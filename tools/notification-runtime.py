"""Independently scheduled relay/worker cycles and persistent stop detection."""
import argparse
from datetime import datetime,timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sqlite3

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

transfer=load('notification-transfer')
live=load('notification-live')
watch=load('monitor-runtime-lab')

def heartbeat(config,problems,now=None):
    path=Path(config['heartbeat_file']);stamp=now or datetime.now(timezone.utc)
    if stamp.tzinfo is None:raise ValueError('timezone required')
    if path.exists():
        old=transfer.read_file(path,4096)
        if old['monitor_id']!=config['monitor_id'] or datetime.fromisoformat(old['completed_at'])>stamp:raise ValueError('heartbeat identity or clock rollback')
    transfer.atomic(path,dict(format='owr-monitor-heartbeat-v1',monitor_id=config['monitor_id'],completed_at=stamp.isoformat(),undelivered=len(problems),open_incidents=len(problems)))

def cycle(role,config,now=None,transport=None,factory=None):
    if role not in ('relay','worker'):raise ValueError('invalid role')
    transfer.ident(config['monitor_id'])
    with Path(config['cycle_lock']).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        problems=[]
        if role=='relay':
            endpoint=transfer.read_file(config['transfer_config'],16384)
            if endpoint.get('relay_monitor_id')!=config['monitor_id'] or endpoint.get('relay_heartbeat_file')!=config['heartbeat_file']:raise ValueError('relay heartbeat binding')
            result=transfer.exchange(endpoint,transport or transfer.ssh)
        else:
            # Test-request intake faults must not stop normal alarm processing.
            try:transfer.stage(transfer.read_file(config['stage_config'],16384))
            except Exception:problems.append('test_intake_failed')
            active=live.current(config['delivery_state'])
            bridge=live.load('notification-admin-bridge')
            counts=bridge.dispatch.run(active,**({'factory':factory} if factory else {}))
            try:live.tests(active,config['requests_dir'],factory=factory)
            except Exception:problems.append('test_processing_failed')
            status=bridge.status(active,dict(active['admin_binding'],config_hash=bridge.digest(active)),simulated=factory is not None)
            if any(c['problems'] for c in status['channels']) or any(r['status'] in ('pending','retry','unknown','rejected') or r['poll_error'] for r in counts):problems.append('notification_delivery_failed')
            publish=transfer.read_file(config['publish_config'],16384)
            if publish['site_id']!=active['admin_binding']['site_id']:raise ValueError('publication site mismatch')
            transfer.atomic(publish['worker_status'],status,0o600)
            transfer.publish(publish)
            result=dict(problems=problems)
        # Never refresh success time if exchange/dispatch/publication did not finish.
        heartbeat(config,problems,now)
        return dict(role=role,healthy=not problems,**result)

def watchdog(config,now=None,sender=None,alert_factory=None):
    targets=config['targets']
    if not isinstance(targets,list) or len(targets)!=2:raise ValueError('relay and worker targets required')
    if {t['role'] for t in targets}!={'relay','worker'} or len({t['monitor_id'] for t in targets})!=2 or len({t['watchdog_state'] for t in targets})!=2:raise ValueError('distinct watchdog targets required')
    results={};alert_config=None
    if sender is None and config.get('alert_dispatch_config'):
        alert_config=transfer.read_file(config['alert_dispatch_config'],32768)
        # This outbox and dispatcher belong to the observer, not the monitored worker.
        def sender(event):
            with sqlite3.connect(alert_config['source_outbox']) as db:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT)')
                raw=json.dumps(event,sort_keys=True)
                old=db.execute('SELECT payload FROM outbox WHERE id=?',(event['event_id'],)).fetchone()
                if old and old[0]!=raw:raise ValueError('observer event conflict')
                db.execute('INSERT OR IGNORE INTO outbox VALUES(?,?)',(event['event_id'],raw))
        # An empty queue is still a valid dispatch source on the first healthy tick.
        with sqlite3.connect(alert_config['source_outbox']) as db:db.execute('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT)')
    for target in targets:
        item={k:v for k,v in target.items() if k!='role'}
        item['delivery']=config.get('delivery',{'transport':'independent_outbox'})
        try:results[target['role']]=watch.run_watchdog(item,now=now,sender=sender)
        except Exception:results[target['role']]=dict(error=True)
    if alert_config is not None:
        try:
            dispatcher=live.load('notification-dispatch-lab')
            counts=dispatcher.run(alert_config,**({'factory':alert_factory} if alert_factory else {}))
            health=transfer.read_file(Path(alert_config['state'])/'delivery-health.json',131072)
            results['alerts']=dict(undelivered=sum(row['count'] for row in counts if row['status'] in ('pending','retry','unknown','rejected'))+len(health['problems']))
        except Exception:results['alerts']=dict(error=True)
    # This optional completion record is for a further independent observer.
    if all('error' not in r for r in results.values()) and config.get('heartbeat_file'):
        problems=[k for k,v in results.items() if v['undelivered']]
        heartbeat(config,problems,now)
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('role',choices=['relay','worker','watchdog']);p.add_argument('--config',type=Path,required=True);a=p.parse_args();os.umask(0o027)
    try:
        config=transfer.read_file(a.config,32768)
        result=watchdog(config) if a.role=='watchdog' else cycle(a.role,config)
        print(json.dumps(result))
        if a.role=='watchdog':return int(any(r.get('error') or r.get('undelivered') for r in result.values()))
        return 0 if result['healthy'] else 1
    except Exception as exc:print(json.dumps(dict(completed=False,error_type=type(exc).__name__)));return 1
if __name__=='__main__':raise SystemExit(main())
