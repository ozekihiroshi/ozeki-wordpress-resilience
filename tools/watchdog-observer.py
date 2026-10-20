"""Independent host observer; fixed read-only SSH endpoint, durable alarms."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import sys

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

transfer=load('notification-transfer')
watch=load('monitor-runtime-lab')
heartbeat=load('heartbeat-ssh')
original_command=transfer.command
# This loader creates a private module instance: other transfer users are unaffected.
def command(config):
    args=original_command(config)
    args[-1]='watchdog-probe'
    return args
transfer.command=command

def endpoint(config,packet):
    if set(packet)!={'format','nonce'} or packet['format']!='owr-watchdog-probe-v1' or not isinstance(packet['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',packet['nonce']):
        raise ValueError('invalid probe')
    value=None;status='missing'
    try:
        value=transfer.read_file(config['heartbeat_file'],4096)
        heartbeat.parse(transfer.body(value),config['monitor_id'])
        status='present'
    except FileNotFoundError:pass
    except Exception:value=None;status='invalid'
    return dict(format='owr-watchdog-probe-result-v1',nonce=packet['nonce'],monitor_id=config['monitor_id'],status=status,heartbeat=value)

def observe(config,now=None,transport=None,sender=None,factory=None):
    explicit_now=now is not None
    now=now or datetime.now(timezone.utc)
    started_at=now
    root=Path(config['state']);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    with watch.locked(root):
        binding=root/'binding.json'
        if binding.exists() and transfer.read_file(binding,32768)!=config:raise ValueError('configuration changed; use new state')
        if not binding.exists():transfer.atomic(binding,config,0o600)
        last=root/'last-tick.json'
        if last.exists() and datetime.fromisoformat(transfer.read_file(last,4096)['at'])>now:raise ValueError('clock rollback')
        transfer.atomic(last,dict(at=now.isoformat()),0o600)
        packet=dict(format='owr-watchdog-probe-v1',nonce=secrets.token_hex(16))
        reachable=False;invalid=False
        try:
            reply=(transport or transfer.ssh)(config['ssh'],packet)
            if set(reply)!={'format','nonce','monitor_id','status','heartbeat'} or reply['format']!='owr-watchdog-probe-result-v1' or reply['nonce']!=packet['nonce'] or reply['monitor_id']!=config['monitor_id'] or reply['status'] not in ('present','missing','invalid'):raise ValueError('reply binding')
            reachable=True
            # A completion generated during SSH latency is not a future timestamp.
            if not explicit_now:now=datetime.now(timezone.utc)
            if reply['status']=='present':
                value,stamp,_=heartbeat.parse(transfer.body(reply['heartbeat']),config['monitor_id'],now)
                old=root/'completion.json'
                if old.exists():
                    before=transfer.read_file(old,4096)
                    previous=datetime.fromisoformat(before['completed_at'])
                    if stamp<previous or (stamp==previous and value!=before):raise ValueError('completion rollback')
                transfer.atomic(old,value,0o600)
                (root/'invalid.json').unlink(missing_ok=True)
            elif reply['heartbeat'] is not None:raise ValueError('invalid absent heartbeat')
            elif reply['status']=='invalid':invalid=True
        except Exception:
            if reachable:invalid=True
        if not explicit_now:now=datetime.now(timezone.utc)
        if now<started_at:raise ValueError('clock rollback during probe')
        transfer.atomic(last,dict(at=now.isoformat()),0o600)
        if reachable:
            transfer.atomic(root/'reachability.json',dict(format='owr-monitor-heartbeat-v1',monitor_id=config['monitor_id']+'-reachability',completed_at=now.isoformat(),undelivered=0,open_incidents=0),0o600)
        # Never replace the last authenticated completion with the probe time.
        completion=root/'completion.json'
        if invalid:
            transfer.atomic(root/'invalid.json',{},0o600)
        if (root/'invalid.json').exists():
            completion=root/'invalid.json'
        alert=config.get('alerts')
        settings_status=None
        if config.get('configuration'):
            control=load('observer-settings');cc=config['configuration']
            if not alert or cc['delivery_state']!=alert['state'] or cc['site_id']!=config['admin_site_id']:raise ValueError('configuration binding')
            try:settings_status=control.apply_pending(cc)
            except Exception:
                settings_status=control.status(cc);settings_status['processing_error']=True
            alert=control.live.current(cc['delivery_state'])
        if sender is None:
            if not alert:raise ValueError('independent alert dispatcher required')
            def sender(event):
                with sqlite3.connect(alert['source_outbox']) as db:
                    db.execute('PRAGMA synchronous=FULL')
                    db.execute('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT)')
                    db.execute('INSERT OR IGNORE INTO outbox VALUES(?,?)',(event['event_id'],json.dumps(event)))
            with sqlite3.connect(alert['source_outbox']) as db:db.execute('CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT)')
        result=dict(reachable=reachable,completion_observation='invalid' if invalid else ('received' if reachable else 'unavailable'))
        for name,path,identity in [('reachability',root/'reachability.json',config['monitor_id']+'-reachability'),('watchdog',completion,config['monitor_id'])]:
            # Stable config even when invalid: copy a sentinel to a dedicated evaluation file.
            evaluation=root/(name+'-evaluation.json')
            if path.exists():transfer.atomic(evaluation,transfer.read_file(path,4096),0o600)
            result[name]=watch.run_watchdog(dict(monitor_id=identity,heartbeat_file=str(evaluation),watchdog_state=str(root/name),stale_after_seconds=config['stale_after_seconds'],delivery={'transport':'independent_outbox'}),now=now,sender=sender)
        delivery=dict(state='unknown',pending=0)
        if alert:
            try:
                dispatch=load('notification-dispatch-lab')
                counts=dispatch.run(alert,**({'factory':factory} if factory else {}))
                health=transfer.read_file(Path(alert['state'])/'delivery-health.json',131072)
                delivery['pending']=sum(row['count'] for row in counts if row['status'] in ('pending','retry','unknown','rejected'))
                result['delivery_failed']=bool(health['problems']) or delivery['pending']>0
                delivery['state']='failed' if result['delivery_failed'] else 'ok'
            except Exception:
                result['delivery_failed']=True;delivery['state']='failed'
        if settings_status is not None:
            try:settings_status['tests']=control.tests(cc,factory=factory)
            except Exception:settings_status['test_processing_error']=True
        transfer.atomic(root/'status.json',result,0o600)
        if config.get('public_status_file'):
            schema=load('observer-status');targets={};history=[]
            for key,file in [('reachability','reachability.json'),('watchdog','completion.json')]:
                path=root/file
                seen=transfer.read_file(path,4096)['completed_at'] if path.exists() else None
                observation='confirmed' if reachable else 'unavailable'
                if key=='watchdog':
                    if (root/'invalid.json').exists():observation='invalid'
                    elif seen is None or (reachable and reply['status']=='missing'):observation='missing'
                targets[key]=dict(last_seen=seen,active=result[key]['active'],pending=result[key]['undelivered'],observation=observation)
                with sqlite3.connect((root/key/'watchdog.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
                    for (raw,) in db.execute('SELECT payload FROM outbox ORDER BY rowid DESC LIMIT 20'):
                        event=json.loads(raw);history.append(dict(target=key,kind=event['kind'],transition=event['transition'],at=event['observed_at']))
            report=dict(format='owr-observer-status-v1',site_id=config['admin_site_id'],monitor_id=config['monitor_id'],observed_at=now.isoformat(),simulated=factory is not None or not alert,targets=targets,delivery=delivery,history=sorted(history,key=lambda e:e['at'],reverse=True)[:20])
            if settings_status is not None:report['configuration']=settings_status
            transfer.atomic(config['public_status_file'],schema.clean(report,config['admin_site_id']))
        return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['endpoint','observe']);p.add_argument('--config',required=True);a=p.parse_args();os.umask(0o027)
    try:
        config=transfer.read_file(a.config,32768)
        if a.action=='endpoint':
            import resource,signal
            resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024));signal.alarm(10)
            if os.environ.get('SSH_ORIGINAL_COMMAND')!='watchdog-probe':raise ValueError('forced command only')
            result=endpoint(config,transfer.decode(sys.stdin.buffer.read(1025),1024))
        else:result=observe(config)
        print(json.dumps(result))
        return int(a.action=='observe' and (not result['reachable'] or result.get('delivery_failed') or any(result[k]['active'] or result[k]['undelivered'] for k in ('reachability','watchdog'))))
    except Exception as exc:print(json.dumps(dict(error_type=type(exc).__name__)));return 1
if __name__=='__main__':raise SystemExit(main())
