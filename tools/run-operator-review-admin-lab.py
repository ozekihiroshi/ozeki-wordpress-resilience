import importlib.util,json,os,hashlib,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('ui',R/'tools/preflight-vm-ui.py');ui=importlib.util.module_from_spec(s);s.loader.exec_module(ui)
import argparse
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
root=args.output;root.mkdir(mode=0o755);status=root/'status';status.mkdir(mode=0o755);results=[]
with ui.ui_session(status,'a'*64) as (web,browser):
 deadline=time.monotonic()+60
 while True:
  ready=ui.run('docker','exec',browser,'python3','-c',"import urllib.request,json;assert json.load(urllib.request.urlopen('http://127.0.0.1:4444/status'))['value']['ready']",check=False)
  if ready.returncode==0:break
  if time.monotonic()>deadline:raise RuntimeError('selenium_not_ready')
  time.sleep(1)
 for mode in ('valid','expired','revoked','reconfirmation_required','stale','missing'):
  now=datetime.now(timezone.utc);at=(now-timedelta(seconds=301) if mode=='stale' else now).isoformat()
  review=dict(format='owr-operator-review-status-v1',state='valid' if mode=='stale' else mode,reviewed_at=(now-timedelta(days=2)).isoformat(),expires_at=(now+timedelta(days=5)).isoformat(),reasons=[],automatic_checks_passed=mode in ('valid','stale'),secret='NEVER_RENDER_SECRET')
  if mode=='expired':review.update(expires_at=(now-timedelta(seconds=1)).isoformat(),reasons=['review_expired'])
  if mode=='revoked':review['reasons']=['review_revoked']
  if mode=='reconfirmation_required':review['reasons']=['scope_changed']
  envelope=dict(format='owr-preflight-admin-v1',site_id='generated-first-site',config_sha256='a'*64,attempted_at=at,result=dict(state='needs_configuration',production_ready=False,host_observation={'state':'validated_report','unverified':['writers']},issues=[],operator_review=review))
  if mode=='missing':envelope['result'].pop('operator_review')
  for name,value in [('report.json',envelope),('health.json',dict(format='owr-preflight-transfer-v1',site_id='generated-first-site',config_sha256='a'*64,attempted_at=at,state='ok',report_at=at))]:(status/name).write_text(json.dumps(value))
  before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in status.iterdir()}
  p=ui.run('docker','exec',browser,'python3','/lab/operator-review-browser.py',mode,check=False,timeout=120)
  (root/(mode+'.log')).write_bytes(p.stdout+p.stderr)
  if p.returncode:
   (root/'selenium.log').write_bytes(ui.run('docker','logs',browser,check=False).stdout);raise RuntimeError('browser_scene_failed:'+mode)
  results.append(json.loads(p.stdout));assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in status.iterdir()}
  ui.run('docker','cp',browser+':/tmp/operator-review-'+mode+'.png',str(root/(mode+'.png')))
(root/'result.json').write_text(json.dumps(dict(passed=True,scenes=results,read_only_hashes=True),indent=2));print(json.dumps(results))
