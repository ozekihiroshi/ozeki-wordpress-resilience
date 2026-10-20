#!/usr/bin/env python3
"""Periodic fixed-command observer pull; last valid report survives failures."""
import argparse,fcntl,importlib.util,json,os,time
from pathlib import Path
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('observer_status',Path(__file__).with_name('observer-status.py'))
wire=importlib.util.module_from_spec(s);s.loader.exec_module(wire)
def tick(c,transport=None):
    paths=[Path(c[k]).resolve() for k in ('status_file','transfer_health','lock_file','loop_lock')]
    if len(set(paths))!=4:raise ValueError('separate paths required')
    wire.t.ident(c['site_id']);wire.t.ident(c['monitor_id'])
    health=dict(format='owr-observer-transfer-v1',site_id=c['site_id'],monitor_id=c['monitor_id'],
                attempted_at=datetime.now(timezone.utc).isoformat(),state='transfer_failed')
    try:
        def bound(config,packet):
            reply=(transport or wire.t.ssh)(config,packet)
            if reply['report']['monitor_id']!=c['monitor_id']:raise ValueError('monitor binding')
            return reply
        report=wire.pull(c,transport=bound)
        health['state']='source_stale' if time.time()-wire.instant(report['observed_at']).timestamp()>=300 else 'ok'
    except Exception:
        pass
    health['attempted_at']=datetime.now(timezone.utc).isoformat()
    wire.t.atomic(c['transfer_health'],health)
    return health
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',required=True);p.add_argument('--interval',type=int,default=60);a=p.parse_args()
    if not 0<=a.interval<=3600:raise ValueError('interval')
    os.umask(0o027);c=wire.t.read_file(a.config,16384)
    with Path(c['loop_lock']).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        while True:
            result=tick(c);print(json.dumps(result),flush=True)
            if not a.interval:return 0 if result['state']=='ok' else 2
            time.sleep(a.interval)
if __name__=='__main__':raise SystemExit(main())
