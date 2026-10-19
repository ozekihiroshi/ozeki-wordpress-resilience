"""Site-bound SSH mailbox: durable requests inward, sanitized status outward."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

MAX_INPUT=32768
MAX_OUTPUT=131072
REQUEST_FIELDS={'request_id','channel_id','site_id','revision','revision_token','created_at'}
UUID=r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}'
STATES={'pending','retry','unknown','rejected','accepted','superseded'}
PROBLEMS={'channel_configuration_failed','delivery_rejected','delivery_unknown','delivery_backlog','receipt_check_failed','ack_expired','ack_overdue'}

def unique(pairs):
    value={}
    for k,v in pairs:
        if k in value:raise ValueError('duplicate field')
        value[k]=v
    return value

def decode(raw,limit):
    if len(raw)>limit:raise ValueError('size limit')
    return json.loads(raw,object_pairs_hook=unique)

def body(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return hashlib.sha256(body(value)).hexdigest()
def ident(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):raise ValueError('invalid identifier')
    return value

def read_file(path,limit):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):raise ValueError('regular file required')
        data=f.read(limit+1)
    return decode(data,limit)

def atomic(path,value,mode=0o640):
    path=Path(path)
    fd,tmp=tempfile.mkstemp(prefix='.transfer-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),mode);f.write(body(value));f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def request(value,site):
    if not isinstance(value,dict) or set(value)!=REQUEST_FIELDS or value['site_id']!=site:raise ValueError('request scope')
    if not isinstance(value['request_id'],str) or not re.fullmatch(UUID,value['request_id']):raise ValueError('request id')
    for key in ('channel_id','site_id','revision_token'):ident(value[key])
    if type(value['revision']) is not int or not 1<=value['revision']<=2147483647:raise ValueError('revision')
    if type(value['created_at']) is not int or not 0<=value['created_at']<=4102444800:raise ValueError('request time')
    # Expiry and active route are checked by the privileged worker, not this mailbox.
    return value

def report(value,site):
    if not isinstance(value,dict) or value.get('format')!='owr-notification-admin-status-v1' or value.get('site_id')!=site:raise ValueError('report scope')
    stamp=datetime.fromisoformat(value['completed_at'])
    if stamp.tzinfo is None or stamp.timestamp()>time.time()+5:raise ValueError('report time')
    ident(value['site_id']);ident(value['revision_token'])
    if type(value['revision']) is not int or value['revision']<1 or type(value.get('simulated')) is not bool:raise ValueError('report metadata')
    channels=value['channels'];tests=value.get('tests',[])
    if not isinstance(channels,list) or len(channels)>20 or not isinstance(tests,list) or len(tests)>20:raise ValueError('report count')
    clean=[];seen=set()
    for c in channels:
        name=ident(c['id'])
        if name in seen:raise ValueError('duplicate channel')
        seen.add(name)
        for field,allowed in [('counts',STATES),('receipts',{'waiting','acknowledged','expired','cancelled'})]:
            if not isinstance(c[field],dict) or set(c[field])-allowed or any(type(n) is not int or not 0<=n<=1000000000 for n in c[field].values()):raise ValueError('report counters')
        if not isinstance(c['problems'],list) or len(c['problems'])>len(PROBLEMS) or any(not isinstance(p,str) or p not in PROBLEMS for p in c['problems']):raise ValueError('report problems')
        clean.append({k:c[k] for k in ('id','counts','receipts','problems')})
    results=[]
    for t in tests:
        if not isinstance(t['request_id'],str) or not re.fullmatch(UUID,t['request_id']):raise ValueError('test id')
        ident(t['channel_id']);ident(t['revision_token'])
        if t['status'] not in {'accepted','unknown','rejected','retry','blocked'}:raise ValueError('test state')
        results.append({k:t[k] for k in ('request_id','channel_id','status','revision_token')})
    result={k:value[k] for k in ('format','site_id','revision','revision_token','completed_at','simulated')}
    result.update(channels=clean,tests=results)
    if len(body(result))>MAX_OUTPUT//2:raise ValueError('report limit')
    return result

def receive(raw,config):
    packet=decode(raw,MAX_INPUT);site=ident(config['site_id'])
    fields={'format','site_id','nonce','requests'}
    if not isinstance(packet,dict) or set(packet) not in (fields,fields|{'relay_heartbeat'}) or packet['format']!='owr-notification-exchange-v1' or packet['site_id']!=site:raise ValueError('exchange scope')
    relay_heartbeat=packet.get('relay_heartbeat')
    if relay_heartbeat is not None:validate_heartbeat(relay_heartbeat,config['relay_monitor_id'])
    if not isinstance(packet['nonce'],str) or not re.fullmatch(r'[a-f0-9]{32}',packet['nonce']):raise ValueError('nonce')
    if not isinstance(packet['requests'],list) or len(packet['requests'])>20:raise ValueError('batch limit')
    requests=[request(r,site) for r in packet['requests']]
    if len({r['request_id'] for r in requests})!=len(requests):raise ValueError('duplicate batch id')
    # Parse status before writing; an invalid report cannot leak any of its fields.
    path=Path(config['report_file'])
    status=report(read_file(path,MAX_OUTPUT),site) if path.exists() else None
    with sqlite3.connect(config['inbox_db'],timeout=2) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL,received REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        count=db.execute('SELECT count(*) FROM inbox').fetchone()[0]
        acknowledgements=[]
        for r in requests:
            serialized=body(r).decode();old=db.execute('SELECT payload FROM inbox WHERE id=?',(r['request_id'],)).fetchone()
            if old and old[0]!=serialized:raise ValueError('request identity conflict')
            if not old:
                if count>=10000:raise ValueError('inbox capacity')
                db.execute('INSERT INTO inbox VALUES(?,?,?)',(r['request_id'],serialized,time.time()));count+=1
            acknowledgements.append(dict(request_id=r['request_id'],sha256=digest(r),state='stored'))
        db.commit() # Acknowledgement means durable storage, never provider acceptance.
    if relay_heartbeat is not None:store_heartbeat(relay_heartbeat,config)
    return dict(format='owr-notification-exchange-result-v1',site_id=site,nonce=packet['nonce'],acknowledgements=acknowledgements,report=status)

def validate_heartbeat(value,monitor_id):
    if not isinstance(value,dict) or set(value)!={'format','monitor_id','completed_at','undelivered','open_incidents'} or value['format']!='owr-monitor-heartbeat-v1' or value['monitor_id']!=ident(monitor_id):raise ValueError('relay heartbeat binding')
    stamp=datetime.fromisoformat(value['completed_at'])
    if stamp.tzinfo is None or stamp.timestamp()>time.time()+5:raise ValueError('relay heartbeat time')
    if any(type(value[k]) is not int or not 0<=value[k]<=1000000 for k in ('undelivered','open_incidents')):raise ValueError('relay heartbeat counters')
    return stamp

def store_heartbeat(value,config):
    target=Path(config['relay_heartbeat_file'])
    with target.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        stamp=validate_heartbeat(value,config['relay_monitor_id'])
        if target.exists():
            previous=read_file(target,4096);before=validate_heartbeat(previous,config['relay_monitor_id'])
            if stamp<before or (stamp==before and previous!=value):raise ValueError('relay heartbeat rollback')
            if stamp==before:return
        atomic(target,value)

def command(config):
    for k in ('host','user'):
        if not isinstance(config[k],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',config[k]):raise ValueError('SSH endpoint')
    if type(config['port']) is not int or not 1<=config['port']<=65535:raise ValueError('port')
    return ['ssh','-F','/dev/null','-T','-p',str(config['port']),'-i',str(Path(config['identity_file']).resolve()),
        '-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes',
        '-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-notification-'+ident(config['site_id']),
        '-o','UserKnownHostsFile='+str(Path(config['known_hosts']).resolve()),'-o','GlobalKnownHostsFile=/dev/null',
        '-o','UpdateHostKeys=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',
        '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2',
        config['user']+'@'+config['host'],'notification-exchange']

def ssh(config,packet):
    # Limit output while reading, not after an unbounded communicate() allocation.
    import selectors
    p=subprocess.Popen(command(config),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        p.stdin.write(body(packet));p.stdin.close()
        selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
        output=bytearray();deadline=time.monotonic()+20
        try:
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise TimeoutError('SSH exchange timeout')
                if not selector.select(remaining):raise TimeoutError('SSH exchange timeout')
                data=os.read(p.stdout.fileno(),4096)
                if not data:break
                output.extend(data)
                if len(output)>MAX_OUTPUT:raise ValueError('SSH response limit')
        finally:selector.close()
        if p.wait(timeout=max(.1,deadline-time.monotonic())):raise RuntimeError('SSH exchange failed')
        return decode(output,MAX_OUTPUT)
    finally:
        if p.poll() is None:p.kill()
        p.wait();p.stdout.close()

def exchange(config,transport=ssh):
    directory=Path(config['requests_dir']);site=ident(config['site_id'])
    # Separate from the PHP request lock: network outages must not block UI writes.
    with Path(config['relay_lock']).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        files=sorted(directory.glob('*.json'))
        if len(files)>100:raise ValueError('local spool full')
        selected=[]
        for path in files[:20]:
            value=request(read_file(path,4096),site)
            if path.name!=value['request_id']+'.json':raise ValueError('request filename')
            selected.append((path,value))
        packet=dict(format='owr-notification-exchange-v1',site_id=site,nonce=secrets.token_hex(16),requests=[v for _,v in selected])
        if config.get('relay_heartbeat_file'):
            path=Path(config['relay_heartbeat_file'])
            previous=read_file(path,4096) if path.exists() else None
            if previous is not None:validate_heartbeat(previous,config['relay_monitor_id'])
            packet['relay_heartbeat']=previous
        reply=transport(config,packet)
        if not isinstance(reply,dict) or set(reply)!={'format','site_id','nonce','acknowledgements','report'} or reply['format']!='owr-notification-exchange-result-v1' or reply['site_id']!=site or reply['nonce']!=packet['nonce']:raise ValueError('response binding')
        expected=[dict(request_id=v['request_id'],sha256=digest(v),state='stored') for _,v in selected]
        if reply['acknowledgements']!=expected:raise ValueError('acknowledgement mismatch')
        output=Path(config['status_file'])
        if reply['report'] is not None:
            incoming=report(reply['report'],site)
            if output.exists():
                old=report(read_file(output,MAX_OUTPUT),site)
                before=datetime.fromisoformat(old['completed_at']);after=datetime.fromisoformat(incoming['completed_at'])
                if after<before or incoming['revision']<old['revision'] or (incoming['revision']==old['revision'] and incoming['revision_token']!=old['revision_token']):raise ValueError('report rollback')
                # Same timestamp can acquire a test result after the dispatch cycle.
            atomic(output,incoming)
        # Acknowledged requests may be removed only if their content is still identical.
        try:
            fd=os.open(directory/'.request.lock',os.O_RDONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o660)
            os.fchmod(fd,0o660)
        except FileExistsError:
            fd=os.open(directory/'.request.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'r') as queue_lock:
            if not stat.S_ISREG(os.fstat(queue_lock.fileno()).st_mode):raise ValueError('queue lock type')
            fcntl.flock(queue_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            for path,value in selected:
                if path.exists() and read_file(path,4096)==value:path.unlink()
            fd=os.open(directory,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        return dict(stored=len(selected),report_received=reply['report'] is not None)

def stage(config):
    """Worker-only import. Transport account cannot invoke the privileged worker."""
    site=ident(config['site_id']);spool=Path(config['worker_requests'])
    with Path(config['stage_lock']).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with sqlite3.connect(config['stage_db']) as ledger:
            ledger.execute('PRAGMA synchronous=FULL')
            ledger.execute('CREATE TABLE IF NOT EXISTS staged(id TEXT PRIMARY KEY,sha256 TEXT NOT NULL)')
            available=max(0,100-len(list(spool.glob('*.json'))));count=0
            with sqlite3.connect(Path(config['inbox_db']).resolve().as_uri()+'?mode=ro',uri=True) as source:
                rows=source.execute('SELECT id,payload FROM inbox ORDER BY rowid').fetchall()
            for rid,raw in rows:
                value=request(decode(raw.encode(),4096),site)
                if rid!=value['request_id']:raise ValueError('inbox identity')
                fingerprint=digest(value);old=ledger.execute('SELECT sha256 FROM staged WHERE id=?',(rid,)).fetchone()
                if old:
                    if old[0]!=fingerprint:raise ValueError('staged identity conflict')
                    continue
                if count>=available:break
                target=spool/(rid+'.json')
                if target.exists() and read_file(target,4096)!=value:raise ValueError('worker spool conflict')
                atomic(target,value,0o600)
                ledger.execute('INSERT INTO staged VALUES(?,?)',(rid,fingerprint));ledger.commit();count+=1
            return dict(staged=count)

def publish(config):
    # Called as the worker; ingress can read only this filtered, fixed output.
    value=report(read_file(config['worker_status'],MAX_OUTPUT),config['site_id'])
    atomic(config['public_status'],value)
    return dict(published=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['receive','exchange','stage','publish']);p.add_argument('--config',type=Path,required=True);a=p.parse_args()
    os.umask(0o027)
    try:
        config=read_file(a.config,16384)
        if a.action=='receive':
            if os.environ.get('SSH_ORIGINAL_COMMAND')!='notification-exchange':raise ValueError('command prohibited')
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024));resource.setrlimit(resource.RLIMIT_CPU,(3,3));signal.alarm(10)
            result=receive(sys.stdin.buffer.read(MAX_INPUT+1),config)
        elif a.action=='exchange':result=exchange(config)
        elif a.action=='stage':result=stage(config)
        else:result=publish(config)
        print(body(result).decode());return 0
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__}));return 1
if __name__=='__main__':raise SystemExit(main())
