"""Operator-approved atomic revisions and bounded admin test requests (Linux)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
from datetime import datetime, timezone
import importlib.util

def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def freeze(provider, directory):
    """Pin credentials as well as recipient; rotating a profile cannot reroute old work."""
    result=provider.copy()
    if 'credentials_file' in result:
        fd=os.open(result['credentials_file'],os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as f:
            info=os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077:
                raise ValueError('owner-only credentials required')
            raw=f.read(65537)
        if len(raw)>65536:raise ValueError('credentials too large')
        directory.mkdir(mode=0o700,exist_ok=True)
        path=directory/hashlib.sha256(raw).hexdigest()
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        except FileExistsError:
            if path.read_bytes()!=raw:raise ValueError('credential snapshot conflict')
        result['credentials_file']=str(path)
    return result

def import_events(db,config,validate):
    db.execute('CREATE TABLE IF NOT EXISTS imported_events(event TEXT PRIMARY KEY,payload TEXT)')
    with sqlite3.connect(Path(config['source_outbox']).as_uri()+'?mode=ro',uri=True) as source:
        rows=source.execute('SELECT payload FROM outbox ORDER BY rowid').fetchall()
    for (raw,) in rows:
        event=validate(json.loads(raw));body=json.dumps(event,sort_keys=True)
        previous=db.execute('SELECT payload FROM imported_events WHERE event=?',(event['event_id'],)).fetchone()
        if previous:
            if previous[0]!=body:raise ValueError('source identity conflict')
            continue
        incident=json.dumps([event[k] for k in ('site','domain','kind','subject')])
        for channel in config['channels']:
            last=db.execute('SELECT payload FROM deliveries WHERE channel=? AND incident=? ORDER BY rowid DESC LIMIT 1',(channel['id'],incident)).fetchone()
            # A resolution belongs to the route that saw its opening, even after disabling.
            selected=(event['transition']=='opened' and channel.get('active',False) and event['kind'] in channel.get('kinds',[])) or (event['transition']=='resolved' and last and json.loads(last[0])['transition']=='opened')
            if selected:
                db.execute('INSERT OR IGNORE INTO deliveries(channel,event,incident,payload) VALUES(?,?,?,?)',(channel['id'],event['event_id'],incident,body))
        db.execute('INSERT INTO imported_events VALUES(?,?)',(event['event_id'],body))

def current(state):
    with sqlite3.connect(Path(state).resolve().as_uri()+'/dispatch.sqlite?mode=ro',uri=True) as db:
        return json.loads(db.execute('SELECT binding FROM settings').fetchone()[0])

def apply(config,binding,expected_hash):
    """No external sending; one SQLite transaction is the cutover authority."""
    import fcntl
    dispatch=load('notification-dispatch-lab');bridge=load('notification-admin-bridge')
    directory=Path(config['state'])
    if not (directory/'dispatch.sqlite').is_file():raise ValueError('initialize dispatcher first')
    if binding['config_hash']!=bridge.digest(config):raise ValueError('candidate binding mismatch')
    with (directory/'dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with sqlite3.connect(directory/'dispatch.sqlite') as db:
            db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE')
            old=json.loads(db.execute('SELECT binding FROM settings').fetchone()[0])
            prior=old.get('admin_binding')
            if prior and prior==binding:return old
            if bridge.digest(old)!=expected_hash:raise ValueError('stale active configuration')
            if old['source_outbox']!=config['source_outbox']:raise ValueError('source replacement prohibited')
            if prior and (prior['site_id']!=binding['site_id'] or binding['revision']<=prior['revision']):raise ValueError('stale or foreign revision')
            # Import the cutover snapshot through the OLD routing before adding routes.
            imported=dispatch.import_events(db,old)
            if not old.get('managed'):
                db.execute('CREATE TABLE imported_events(event TEXT PRIMARY KEY,payload TEXT)')
                for (raw,) in imported:
                    event=dispatch.validate(json.loads(raw))
                    db.execute('INSERT OR IGNORE INTO imported_events VALUES(?,?)',(event['event_id'],json.dumps(event,sort_keys=True)))
            channels=[]
            for channel in old['channels']:
                channels.append(dict(channel,logical_id=channel.get('logical_id',channel['id']),active=False,
                    provider=freeze(channel['provider'],directory/'credentials')))
            for channel in config['channels']:
                route='r'+hashlib.sha256((binding['revision_token']+channel['id']).encode()).hexdigest()[:40]
                channels.append(dict(channel,id=route,logical_id=channel['id'],active=True,provider=freeze(channel['provider'],directory/'credentials')))
            new=dict(config,channels=channels,managed=True,admin_binding=binding,health=old.get('health',{}))
            dispatch.validate_config(new)
            db.execute('UPDATE settings SET binding=?',(json.dumps(new,sort_keys=True),))
            # A previous report must not claim the new revision has been processed yet.
            db.commit()
            return new

def tests(config,spool,now=None,factory=None):
    """Requests contain identifiers only. Caller supplies the trusted spool path."""
    import fcntl,re
    dispatch=load('notification-dispatch-lab');now=time.time() if now is None else now
    factory=factory or dispatch.adapter
    directory=Path(config['state']);binding=config['admin_binding']
    with (directory/'dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with sqlite3.connect(directory/'dispatch.sqlite') as db:
            if json.loads(db.execute('SELECT binding FROM settings').fetchone()[0])!=config:raise ValueError('stale configuration')
            db.execute('CREATE TABLE IF NOT EXISTS test_requests(id TEXT PRIMARY KEY,channel TEXT,status TEXT,created REAL,revision_token TEXT)')
            db.execute("UPDATE test_requests SET status='unknown' WHERE status='sending'");db.commit()
            paths=list(Path(spool).glob('*.json'))
            if len(paths)>100:raise ValueError('request spool full')
            for path in sorted(paths):
                if not re.fullmatch(r'[a-f0-9-]{36}\.json',path.name):continue
                try:
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                    with os.fdopen(fd) as f:
                        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):continue
                        req=json.loads(f.read(4097))
                    rid=req['request_id'];channel=req['channel_id']
                    if path.stem!=rid or not isinstance(channel,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',channel):continue
                    if db.execute('SELECT 1 FROM test_requests WHERE id=?',(rid,)).fetchone():continue
                    route=next((c for c in config['channels'] if c.get('active') and c['logical_id']==channel),None)
                    valid=all(req.get(k)==binding[k] for k in ('site_id','revision','revision_token'))
                    stamp=req.get('created_at');valid=valid and type(stamp) is int and 0<=now-stamp<=300 and route is not None
                    recent=db.execute("SELECT 1 FROM test_requests WHERE channel=? AND created>? AND status IN ('sending','accepted','unknown','retry','rejected')",(channel,now-60)).fetchone()
                    state='sending' if valid and not recent else 'blocked'
                    db.execute('INSERT INTO test_requests VALUES(?,?,?,?,?)',(rid,channel,state,now,binding['revision_token']));db.commit()
                    if state!='sending':continue
                    event=dict(event_id=rid.replace('-',''),site=binding['site_id'],domain='notification-test',subject=channel,kind='notification_test',transition='resolved',observed_at=datetime.fromtimestamp(now,timezone.utc).isoformat())
                    try:factory(route['provider']).send(event);state='accepted'
                    except Exception as exc:state=exc.outcome if isinstance(exc,dispatch.push.DeliveryError) else 'unknown'
                    db.execute('UPDATE test_requests SET status=? WHERE id=?',(state,rid));db.commit()
                except (ValueError,KeyError,OSError,TypeError):continue
            # Retain outcomes in SQLite; consuming the transport files prevents a full spool.
            for path in paths:
                if db.execute('SELECT 1 FROM test_requests WHERE id=?',(path.stem,)).fetchone():
                    path.unlink(missing_ok=True)
            return [dict(request_id=r[0],channel_id=r[1],status=r[2],revision_token=r[4]) for r in db.execute('SELECT * FROM test_requests ORDER BY created DESC LIMIT 20')]

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    a=sub.add_parser('apply');a.add_argument('--compiled',type=Path,required=True);a.add_argument('--expected-hash',required=True)
    r=sub.add_parser('run');r.add_argument('--state',required=True);r.add_argument('--requests',type=Path);r.add_argument('--status',type=Path,required=True)
    args=p.parse_args()
    try:
        bridge=load('notification-admin-bridge')
        if args.action=='apply':
            result=apply(json.loads((args.compiled/'config.json').read_text()),json.loads((args.compiled/'binding.json').read_text()),args.expected_hash)
            print(json.dumps({'active_hash':bridge.digest(result),'revision':result['admin_binding']['revision']}))
        else:
            config=current(args.state);bridge.dispatch.run(config)
            if args.requests:tests(config,args.requests)
            report=bridge.status(config,dict(config['admin_binding'],config_hash=bridge.digest(config)))
            bridge.dispatch.health.atomic_json(args.status,report)
    except Exception as exc:print(json.dumps({'error_type':type(exc).__name__}));return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
