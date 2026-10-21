import importlib.util,json,os,sys,time,signal
from pathlib import Path
from datetime import datetime,timezone
def module(name):
 s=importlib.util.spec_from_file_location(name,'/opt/owr/tools/'+name+'.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
mode,role=sys.argv[1:];wire=module('notification-transfer')
Path('/data/'+role+'.pid').write_text(str(os.getpid()))
if mode=='observe':observer=module('watchdog-observer');c=json.loads(Path('/data/'+role+'.json').read_text())
def send(event):
 with Path('/data/notifications.jsonl').open('a') as f:f.write(json.dumps(event)+'\n');f.flush();os.fsync(f.fileno())
running=True
def finish(*args):
 global running
 running=False
signal.signal(signal.SIGTERM,finish)
while running:
 if mode=='publish':
  at=datetime.now(timezone.utc).isoformat()
  wire.atomic('/public/report.json',dict(format='owr-preflight-admin-v1',site_id='generated-first-site',config_sha256='a'*64,attempted_at=at,result=dict(production_ready=False,state='needs_configuration',host_observation=dict(state='validated_report',unverified=['writers']),issues=[])))
  wire.atomic('/public/health.json',dict(format='owr-preflight-transfer-v1',site_id='generated-first-site',config_sha256='a'*64,attempted_at=at,report_at=at,state='ok'))
 else:observer.observe(c,sender=send)
 time.sleep(2)
