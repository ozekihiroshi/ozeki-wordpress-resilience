#!/usr/bin/env python3
"""Periodic read-only SSH preflight with atomic local WordPress handoff."""
import argparse,fcntl,json,os,stat,sys,time
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
import importlib.util
s=importlib.util.spec_from_file_location('hostssh',Path(__file__).with_name('host-inventory-ssh.py'));wire=importlib.util.module_from_spec(s);s.loader.exec_module(wire)

def validate(c):
    keys=('report_file','health_file','lock_file','profile_file','inventory_file','connection_file')
    paths=[Path(c[k]) for k in keys]
    if any(not p.is_absolute() or p.is_symlink() for p in paths) or len({p.resolve() for p in paths})!=len(paths):raise ValueError('separate absolute paths required')
    for p in paths[:3]:
        st=p.parent.stat()
        if st.st_uid!=os.geteuid() or st.st_mode&0o022:raise ValueError('private publisher directory required')
    return c

def tick(c,transport=None):
    pre=wire.load('deployment-preflight');profile=pre.read_json(c['profile_file'])
    if profile['site_id']!=c['site_id']:raise ValueError('site binding')
    digest=pre.capture.digest(profile)
    if digest!=c['config_sha256']:raise ValueError('profile binding')
    at=datetime.now(timezone.utc).isoformat()
    health=dict(format='owr-preflight-transfer-v1',site_id=c['site_id'],config_sha256=digest,attempted_at=at,state='acquisition_failed',report_at=None)
    try:
        result=wire.inspect(wire.t.read_file(c['connection_file'],16384),profile,pre.read_json(c['inventory_file']),c['workspace'],transport)
    except Exception:
        result=dict(production_ready=False,state='needs_configuration',host_observation=dict(state='unavailable'),issues=[dict(code='preflight_input_or_acquisition_failed',category='unclassified')])
    envelope=dict(format='owr-preflight-admin-v1',site_id=c['site_id'],config_sha256=digest,attempted_at=at,result=result)
    try:
        wire.t.atomic(c['report_file'],envelope)
        health['report_at']=at
        health['state']='ok' if result.get('host_observation',{}).get('state')=='validated_report' else 'acquisition_failed'
    except Exception:
        health['state']='transfer_failed'
    wire.t.atomic(c['health_file'],health) # Failure must terminate, leaving old health to age out.
    return health

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--interval',type=int,default=60);a=p.parse_args()
    if not 0<=a.interval<=240:raise ValueError('interval must be 0 or 1..240 seconds')
    os.umask(0o027);c=validate(wire.t.read_file(a.config,16384))
    fd=os.open(c['lock_file'],os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'r+') as lock:
        if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):raise ValueError('regular lock required')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            try:r=tick(c)
            except Exception:
                print('{"state":"publisher_failed"}',flush=True);return 2
            print(json.dumps(r),flush=True)
            if not a.interval:return 0 if r['state']=='ok' else 2
            time.sleep(a.interval)
if __name__=='__main__':raise SystemExit(main())
