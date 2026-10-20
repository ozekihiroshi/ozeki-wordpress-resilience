#!/usr/bin/env python3
"""Fixed-file read-only SSH pull and periodic generation; no recovery commands."""
import argparse,fcntl,importlib.util,json,os,secrets,sys,time
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
t=load('daily_wire','notification-transfer.py')
export=load('daily_export','daily-admin-status.py')
original_command=t.command
def command(c):
    argv=original_command(c)
    argv=[x.replace('HostKeyAlias=owr-notification-','HostKeyAlias=owr-daily-') for x in argv]
    argv[-1]='daily-status-read'
    return argv
t.command=command
def now():return datetime.now(timezone.utc).isoformat()
def stamp(value):
    d=datetime.fromisoformat(value)
    if d.tzinfo is None or d.timestamp()>time.time()+5:raise ValueError('invalid time')
    return d.timestamp()
VALUES=set('approved awaiting_approval pending expired unverified restore_verified restore_failed recovery_running recovery_interrupted recovery_reviewed_closed registration_pending evidence_error approval_expired running failed unknown missing verified not_verified none not_attempted not_observed stored finished interrupted reviewed_closed succeeded recorded waiting unavailable not_recorded incomplete closed automatic_removed invalid'.split())
def report(v,site):
    if not isinstance(v,dict) or v.get('format')!='owr-daily-admin-v1' or v.get('site_id')!=site or type(v.get('missing_due_slot')) is not bool:raise ValueError('scope')
    stamp(v['observed_at']);out={k:v[k] for k in ('format','site_id','observed_at','missing_due_slot')}
    for key,fields in [('runs',['day','phase','storage_complete','approval_state','restore_state']),
                       ('attempts',['request_id','day','state','outcome','registration','cleanup'])]:
        if not isinstance(v.get(key),list) or len(v[key])>30:raise ValueError('count')
        rows=[]
        for row in v[key]:
            clean={}
            for f in fields:
                x=row[f]
                if f=='storage_complete':
                    if type(x) is not bool:raise ValueError('boolean')
                elif f=='day':
                    import re
                    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x):raise ValueError('day')
                elif f=='request_id':t.ident(x)
                elif not isinstance(x,str) or x not in VALUES:raise ValueError('state')
                clean[f]=x
            rows.append(clean)
        out[key]=rows
    if len(t.body(out))>65536:raise ValueError('size')
    return out
def publish(c):
    source=Path(c['state']).resolve()
    targets=[Path(c[k]).resolve() for k in ('report_file','producer_health')]
    if len(set(targets))!=2 or any(p.is_relative_to(source) for p in targets):raise ValueError('separate output required')
    try:
        v=report(export.snapshot(c['state'],c['site_id']),c['site_id'])
        t.atomic(c['report_file'],v,0o640)
        t.atomic(c['producer_health'],dict(at=now(),state='ok'),0o640)
        return True
    except Exception:
        t.atomic(c['producer_health'],dict(at=now(),state='failed'),0o640)
        return False
def serve(c,raw):
    q=t.decode(raw,4096)
    if set(q)!={'site_id','nonce'} or q['site_id']!=c['site_id'] or len(q['nonce'])!=32 or any(x not in '0123456789abcdef' for x in q['nonce']):raise ValueError('request')
    v=report(t.read_file(c['report_file'],65536),c['site_id']) if Path(c['report_file']).exists() else None
    health=t.read_file(c['producer_health'],4096)
    stamp(health['at'])
    if health['state'] not in ('ok','failed'):raise ValueError('producer state')
    return dict(site_id=c['site_id'],nonce=q['nonce'],report=v,producer_state=health['state'])
def relay(c,transport=t.ssh):
    if Path(c['status_file']).resolve()==Path(c['transfer_health']).resolve():raise ValueError('separate health file required')
    health=dict(format='owr-daily-transfer-v1',site_id=c['site_id'],attempted_at=now(),state='transfer_failed',report_sha256=None)
    output=Path(c['status_file'])
    try:
        old=report(t.read_file(output,65536),c['site_id']) if output.exists() else None
        if old:health['report_sha256']=t.digest(old)
        q=dict(site_id=c['site_id'],nonce=secrets.token_hex(16))
        reply=transport(c,q)
        if not isinstance(reply,dict) or set(reply)!={'site_id','nonce','report','producer_state'} or reply['site_id']!=c['site_id'] or reply['nonce']!=q['nonce']:raise ValueError('response scope')
        if reply['producer_state'] not in ('ok','failed'):raise ValueError('producer')
        if reply['report'] is None:
            health['state']='source_failed'
        else:
            incoming=report(reply['report'],c['site_id'])
            if old and (stamp(incoming['observed_at'])<stamp(old['observed_at']) or incoming['observed_at']==old['observed_at'] and t.digest(incoming)!=t.digest(old)):raise ValueError('rollback or equivocation')
            t.atomic(output,incoming,0o640)
            health['report_sha256']=t.digest(incoming)
            health['state']='source_failed' if reply['producer_state']=='failed' else 'source_stale' if time.time()-stamp(incoming['observed_at'])>=300 else 'ok'
    except Exception:
        # Keep the last known report unchanged, including its original observation time.
        health['state']='transfer_failed'
    t.atomic(c['transfer_health'],health,0o640)
    return health['state']=='ok'
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True)
    p.add_argument('mode',choices=['publish','serve','relay']);p.add_argument('--interval',type=int,default=0)
    a=p.parse_args();os.umask(0o077)
    c=t.read_file(a.config,16384);t.ident(c['site_id'])
    if a.mode=='serve':
        if os.environ.get('SSH_ORIGINAL_COMMAND') not in (None,'daily-status-read'):raise ValueError('fixed command only')
        print(json.dumps(serve(c,sys.stdin.buffer.read(4097))));return 0
    if a.interval<0 or a.interval>3600:raise ValueError('interval')
    with Path(c['lock_file']).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            ok=(publish(c) if a.mode=='publish' else relay(c))
            if not a.interval:return 0 if ok else 2
            time.sleep(a.interval)
if __name__=='__main__':raise SystemExit(main())
