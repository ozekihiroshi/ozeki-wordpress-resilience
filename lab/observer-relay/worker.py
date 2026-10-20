import importlib.util,json,os,sys,time
from pathlib import Path
from datetime import datetime,timezone
def module(name):
 s=importlib.util.spec_from_file_location(name,'/opt/owr/tools/'+name+'.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
mode,role=sys.argv[1:];wire=module('notification-transfer')
Path('/data/'+role+'.pid').write_text(str(os.getpid()))
if mode=='observe':observer=module('watchdog-observer');c=json.loads(Path('/data/'+role+'.json').read_text())
def send(event):
 with Path('/data/notifications.jsonl').open('a') as f:f.write(json.dumps(event)+'\n');f.flush();os.fsync(f.fileno())
while True:
 if mode=='publish':wire.atomic('/public/daily.json',dict(format='owr-daily-admin-v1',site_id='generated-first-site',observed_at=datetime.now(timezone.utc).isoformat(),missing_due_slot=False,runs=[],attempts=[]))
 else:observer.observe(c,sender=send)
 time.sleep(2)
