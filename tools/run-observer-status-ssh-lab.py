"""Pinned read-only status SSH in disposable offline containers."""
import importlib.util,json,secrets,tempfile,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('lab',ROOT/'tools/run-notification-runtime-lab.py');lab=importlib.util.module_from_spec(s);s.loader.exec_module(lab);run=lab.run
prefix='owr-status-'+secrets.token_hex(4);server=prefix+'-source';client=prefix+'-client';created=[];checks=[]
def ex(host,*args,**kw):return run('docker','exec',*(['-i'] if kw.get('input') is not None else []),host,*args,**kw)
def check(value,label):
 if not value:raise AssertionError(label)
 checks.append(label);print('PASS '+label,flush=True)
try:
 with tempfile.TemporaryDirectory() as tmp:
  work=Path(tmp);code=work/'code';code.mkdir()
  for name in ['observer-status','notification-transfer']:shutil.copy2(ROOT/'tools'/(name+'.py'),code/(name+'.py'))
  for name in ['host','key','wrong']:run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/name))
  for host,net in [(server,'none'),(client,'container:'+server)]:
   run('docker','run','-d','--name',host,'--network',net,'--memory','256m','--entrypoint','sleep',lab.IMAGE,'infinity');created.append(host)
   ex(host,'mkdir','-p','/opt/owr','/etc/owr','/public','/state','/run/sshd');run('docker','cp',str(code)+'/.',host+':/opt/owr/');ex(host,'chown','-R','root:root','/opt/owr');ex(host,'chmod','-R','go-w','/opt/owr')
  def put(host,path,value,mode='644'):
   f=work/'upload';f.write_text(value if isinstance(value,str) else json.dumps(value));run('docker','cp',str(f),host+':'+path);ex(host,'chown','root:root',path);ex(host,'chmod',mode,path)
  ex(server,'useradd','-m','-s','/bin/sh','owr-status');ex(server,'usermod','-p','*','owr-status')
  put(server,'/etc/owr/host',(work/'host').read_text(),'600');put(client,'/etc/owr/key',(work/'key').read_text(),'600')
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'host.pub').read_text())
  put(server,'/etc/owr/keys','restrict,command="/usr/bin/python3 /opt/owr/observer-status.py endpoint --config /etc/owr/endpoint.json" '+(work/'key.pub').read_text())
  put(server,'/etc/owr/endpoint.json',dict(site_id='site',public_status_file='/public/status.json'))
  put(server,'/etc/owr/sshd','\n'.join(['Port 2222','HostKey /etc/owr/host','PidFile /run/sshd/status.pid','AuthorizedKeysFile /etc/owr/keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers owr-status','AllowTcpForwarding no','AllowAgentForwarding no','PermitTTY no'])+'\n')
  ex(server,'/usr/sbin/sshd','-f','/etc/owr/sshd')
  from datetime import datetime,timezone,timedelta
  original_time=(datetime.now(timezone.utc)-timedelta(seconds=30)).isoformat()
  report=dict(format='owr-observer-status-v1',site_id='site',monitor_id='watchdog',observed_at=original_time,simulated=True,targets={k:dict(last_seen=None,active=[],pending=0,observation='missing') for k in ('reachability','watchdog')},delivery=dict(state='failed',pending=2),history=[],secret='NEVER-TRANSFER-SECRET')
  put(server,'/public/status.json',report)
  c=dict(site_id='site',host='127.0.0.1',user='owr-status',port=2222,identity_file='/etc/owr/key',known_hosts='/etc/owr/known_hosts',status_file='/state/status.json',lock_file='/state/lock')
  put(client,'/etc/owr/pull.json',c)
  def pull():return ex(client,'python3','/opt/owr/observer-status.py','pull','--config','/etc/owr/pull.json',check=False)
  check(pull().returncode==0,'real SSH snapshot transfer')
  first=ex(client,'cat','/state/status.json').stdout;clean=json.loads(first)
  check(clean['observed_at']==original_time,'transfer preserves observation age')
  check(b'NEVER-TRANSFER-SECRET' not in first,'snapshot strips secret fields')
  check(pull().returncode==0,'identical replay is idempotent')
  put(server,'/public/status.json',dict(report,site_id='other'));check(pull().returncode!=0,'foreign site rejected')
  put(server,'/public/status.json',dict(report,observed_at='2000-01-01T00:00:00+00:00'));check(pull().returncode!=0,'rollback rejected')
  put(server,'/public/status.json',report)
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'wrong.pub').read_text());check(pull().returncode!=0,'host pin mismatch rejected')
  check(ex(client,'cat','/state/status.json').stdout==first,'failed pulls preserve last report')
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'host.pub').read_text())
  denied=ex(client,'ssh','-F','/dev/null','-p','2222','-i','/etc/owr/key','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-notification-site','-o','UserKnownHostsFile=/etc/owr/known_hosts','owr-status@127.0.0.1','id',check=False)
  check(denied.returncode!=0,'forced command denies shell')
  check(ex(server,'runuser','-u','owr-status','--','test','-w','/public/status.json',check=False).returncode!=0,'endpoint cannot write snapshot')
finally:
 for host in reversed(created):run('docker','rm','-f','-v',host,check=False)
Path(sys.argv[1]).write_text(json.dumps(dict(checks=checks,passed=len(checks),external_notifications_sent=0),indent=2)+'\n')
