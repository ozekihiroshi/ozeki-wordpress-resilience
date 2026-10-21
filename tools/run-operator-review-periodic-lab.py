"""Periodic production report functions with generated transport data and real WP UI."""
import argparse,copy,hashlib,importlib.util,json,threading,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,R/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ui=load('preflight-vm-ui');relay=load('preflight-relay');transfer=load('preflight-transfer');issuer=load('recurring-capture-review')
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.output;root.mkdir(mode=0o755)
private=root/'private';private.mkdir(mode=0o700);status=root/'status';status.mkdir(mode=0o755);workspace=private/'capture';workspace.mkdir(mode=0o700)
# Match the dedicated WordPress reader group; atomic replacements inherit it.
ui.run('docker','run','--rm','--network','none','-v',str(status)+':/status','owr-external-lab:local','sh','-c','chgrp 33 /status && chmod 2755 /status')
profile=json.loads((R/'examples/first-site/generated-lab.json').read_text());profile['storage']['destination_ref']='generated-storage';profile['trust'].update(operator='lab-operator',public_pin_ref='generated-pin');digest=issuer.gate.pre.capture.digest(profile)
inv={k:copy.deepcopy(profile[k]) for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')};inv.update(format='owr-deployment-inventory-v1',config_sha256=digest,observed_at=datetime.now(timezone.utc).isoformat(),incomplete_runs=0,uncertain_puts=0)
c=dict(site_id=profile['site_id'],config_sha256=digest,workspace=str(workspace))
for key,val in [('profile_file',profile),('inventory_file',inv),('connection_file',dict(site_id=profile['site_id']))]:
 path=private/(key+'.json');path.write_text(json.dumps(val));c[key]=str(path)
for key in ('report_file','health_file','lock_file','review_file'):c[key]=str(private/(key+'.json'))
receiver=dict(site_id=profile['site_id'],config_sha256=digest,report_file=str(status/'report.json'),health_file=str(status/'health.json'))
relay.validate(c)
facts={'database':{'name':'lab','prefix':'wp_','engines':['InnoDB'],'tables':3},'files':{'root':'/var/www/html','entries':3,'bytes':100,'links':0,'special':0},'wordpress':{'standard_upload_path':True,'external_upload_url':False,'multisite_tables':False},'runtime':{'php_version':'8.3.0','os_family':'Linux'}}
def transport(conn,q):return dict(format='owr-host-inventory-v1',status='observed',site_id=q['site_id'],config_sha256=q['config_sha256'],nonce=q['nonce'],observed_at=datetime.now(timezone.utc).isoformat(),facts=copy.deepcopy(facts),unverified=issuer.gate.SCOPES[:-1])
stop=threading.Event();lock=threading.Lock();errors=[];ticks=[]
def cycle():
 inv['observed_at']=datetime.now(timezone.utc).isoformat();relay.wire.t.atomic(c['inventory_file'],inv)
 relay.tick(c,transport)
 result=transfer.pull(receiver,lambda conn,q:transfer.serve(c,q))
 if result['state']!='ok':raise RuntimeError('report_transfer_failed')
 value=json.loads((status/'report.json').read_text());state=value['result']['operator_review']['state']
 ticks.append(dict(at=value['attempted_at'],state=state))
def periodic():
 try:
  while not stop.is_set():
   with lock:cycle()
   stop.wait(2)
 except Exception as exc:errors.append(type(exc).__name__);stop.set()
def renew():
 with lock:
  # Explicit simulated operator action, not part of the periodic loop.
  cycle();report=json.loads(Path(c['report_file']).read_text());health=json.loads(Path(c['health_file']).read_text())
  confirmations={k:dict(confirmed=True,evidence_ref='generated-manual-check/'+k) for k in issuer.gate.SCOPES}
  review=issuer.issue(profile,inv,workspace,report,health,confirmations,profile['operations']['owner'])
  previous=Path(c['review_file'])
  if previous.exists():(private/('review-history-'+str(time.time_ns())+'.json')).write_bytes(previous.read_bytes())
  relay.wire.t.atomic(c['review_file'],review)
def wait_state(expected):
 deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  if errors:raise RuntimeError(str(errors))
  try:
   if json.loads((status/'report.json').read_text())['result']['operator_review']['state']==expected:return
  except (FileNotFoundError,KeyError):pass
  time.sleep(.2)
 raise RuntimeError('state_not_reached:'+expected)
renew();worker=threading.Thread(target=periodic);worker.start();results=[]
try:
 with ui.ui_session(status,digest) as (web,browser):
  deadline=time.monotonic()+60
  while ui.run('docker','exec',browser,'python3','-c',"import urllib.request,json;assert json.load(urllib.request.urlopen('http://127.0.0.1:4444/status'))['value']['ready']",check=False).returncode:
   if time.monotonic()>deadline:raise RuntimeError('selenium_not_ready')
   time.sleep(1)
  for index,mode in enumerate(('valid','expired','valid','revoked','valid')):
   if index==1:
    with lock:
     review=json.loads(Path(c['review_file']).read_text());review['expires_at']=(datetime.now(timezone.utc)+timedelta(seconds=5)).isoformat();relay.wire.t.atomic(c['review_file'],review)
   elif index==3:
    with lock:
     review=json.loads(Path(c['review_file']).read_text());review['status']='revoked';relay.wire.t.atomic(c['review_file'],review)
   elif index in (2,4):renew()
   wait_state(mode)
   before=Path(c['review_file']).read_bytes();count=len(ticks)
   result=ui.run('docker','exec',browser,'python3','/lab/operator-review-browser.py',mode,check=False,timeout=120)
   (root/(str(index)+'-'+mode+'.log')).write_bytes(result.stdout+result.stderr)
   if result.returncode:
    (root/'selenium.log').write_bytes(ui.run('docker','logs',browser,check=False).stdout);raise RuntimeError('browser_scene_failed:'+mode)
   assert before==Path(c['review_file']).read_bytes(),'periodic loop renewed or changed operator confirmation'
   assert len(ticks)>count,'periodic loop did not update during browser scene'
   results.append(dict(index=index,mode=mode,checks=json.loads(result.stdout),periodic_updates=len(ticks)-count))
   ui.run('docker','cp',browser+':/tmp/operator-review-'+mode+'.png',str(root/(str(index)+'-'+mode+'.png')))
finally:
 stop.set();worker.join(timeout=10)
 (root/'ticks.json').write_text(json.dumps(ticks,indent=2))
assert not worker.is_alive() and not errors
value=dict(passed=True,scenes=results,updates=len(ticks),scope='real periodic relay.tick and transfer serve/pull; generated inventory and in-process transport; real WordPress/Chromium; not SSH or systemd',automatic_review_renewal=False)
(root/'result.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
