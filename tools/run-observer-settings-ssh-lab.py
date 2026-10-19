"""Pinned settings inbox SSH in disposable offline containers; no notification sends."""
import importlib.util,json,secrets,tempfile,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('lab',ROOT/'tools/run-notification-runtime-lab.py');lab=importlib.util.module_from_spec(s);s.loader.exec_module(lab);run=lab.run
prefix='owr-settings-'+secrets.token_hex(4);server=prefix+'-source';client=prefix+'-client';created=[];checks=[]
def ex(host,*args,**kw):return run('docker','exec',*(['-i'] if kw.get('input') is not None else []),host,*args,**kw)
def check(value,label):
 if not value:raise AssertionError(label)
 checks.append(label);print('PASS '+label,flush=True)
try:
 with tempfile.TemporaryDirectory() as tmp:
  work=Path(tmp);code=work/'code';code.mkdir()
  for name in ['observer-settings','notification-transfer','notification-live','notification-admin-bridge','notification-dispatch-lab','notification-health','pushover-adapter','monitor-delivery']:shutil.copy2(ROOT/'tools'/(name+'.py'),code/(name+'.py'))
  for name in ['host','key','wrong']:run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(work/name))
  for host,net in [(server,'none'),(client,'container:'+server)]:
   run('docker','run','-d','--name',host,'--network',net,'--memory','256m','--entrypoint','sleep',lab.IMAGE,'infinity');created.append(host)
   ex(host,'mkdir','-p','/opt/owr','/etc/owr','/public','/state','/run/sshd');run('docker','cp',str(code)+'/.',host+':/opt/owr/');ex(host,'chown','-R','root:root','/opt/owr');ex(host,'chmod','-R','go-w','/opt/owr')
  def put(host,path,value,mode='644'):
   f=work/'upload';f.write_text(value if isinstance(value,str) else json.dumps(value));run('docker','cp',str(f),host+':'+path);ex(host,'chown','root:root',path);ex(host,'chmod',mode,path)
  ex(server,'useradd','-m','-s','/bin/sh','owr-status');ex(server,'usermod','-p','*','owr-status')
  put(server,'/etc/owr/host',(work/'host').read_text(),'600');put(client,'/etc/owr/key',(work/'key').read_text(),'600')
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'host.pub').read_text())
  put(server,'/etc/owr/keys','restrict,command="/usr/bin/python3 /opt/owr/observer-settings.py receive --config /etc/owr/endpoint.json" '+(work/'key.pub').read_text())
  ex(server,'chown','owr-status:owr-status','/public');ex(server,'chmod','750','/public')
  put(server,'/etc/owr/endpoint.json',dict(site_id='site',inbox_db='/public/inbox.sqlite'))
  put(server,'/state/secret','DO-NOT-READ','600');ex(server,'chmod','700','/state')
  put(server,'/etc/owr/sshd','\n'.join(['Port 2222','HostKey /etc/owr/host','PidFile /run/sshd/status.pid','AuthorizedKeysFile /etc/owr/keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers owr-status','AllowTcpForwarding no','AllowAgentForwarding no','PermitTTY no'])+'\n')
  ex(server,'/usr/sbin/sshd','-f','/etc/owr/sshd')
  import time,uuid
  v=dict(format='owr-observer-settings-request-v1',request_id=str(uuid.uuid4()),created_at=int(time.time()),expected_hash='a'*64,settings=dict(format='owr-notification-settings-v1',site_id='site',revision=1,revision_token='rev1',channels=[dict(id='phone',label='Phone',profile='push',provider='pushover',recipient='Phone',enabled=True,kinds=['monitor_stopped','heartbeat_invalid','notification_delivery_failed'],retry=60,expire=300)]))
  c=dict(site_id='site',host='127.0.0.1',user='owr-status',port=2222,identity_file='/etc/owr/key',known_hosts='/etc/owr/known_hosts',requests_dir='/state',lock_file='/state/lock')
  put(client,'/etc/owr/pull.json',c)
  path='/state/'+v['request_id']+'.json'
  def pull():return ex(client,'python3','/opt/owr/observer-settings.py','exchange','--config','/etc/owr/pull.json',check=False)
  put(client,path,v);check(pull().returncode==0,'real SSH settings stored acknowledgement')
  check(ex(client,'test','-e',path,check=False).returncode!=0,'spool consumed only after durable acknowledgement')
  put(client,path,v);check(pull().returncode==0,'lost acknowledgement replay accepted')
  count=int(ex(server,'python3','-c',"import sqlite3;print(sqlite3.connect('/public/inbox.sqlite').execute('select count(*) from inbox').fetchone()[0])").stdout)
  check(count==1,'duplicate request stored once')
  changed=dict(v,created_at=v['created_at']-1);put(client,path,changed);check(pull().returncode!=0,'same request id with different content rejected')
  put(client,path,v)
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'wrong.pub').read_text());check(pull().returncode!=0,'host pin mismatch rejected')
  check(ex(client,'test','-f',path,check=False).returncode==0,'failed transfer preserves queued candidate')
  put(client,'/etc/owr/known_hosts','owr-notification-site '+(work/'host.pub').read_text())
  denied=ex(client,'ssh','-F','/dev/null','-p','2222','-i','/etc/owr/key','-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-notification-site','-o','UserKnownHostsFile=/etc/owr/known_hosts','owr-status@127.0.0.1','id',check=False)
  check(denied.returncode!=0,'forced command denies shell')
  check(ex(server,'runuser','-u','owr-status','--','cat','/state/secret',check=False).returncode!=0,'inbox user cannot read private notification credentials')
  check(ex(server,'runuser','-u','owr-status','--','test','-w','/opt/owr/observer-settings.py',check=False).returncode!=0,'inbox user cannot modify worker code')
  check(pull().returncode==0,'settings replay cleared before test request')
  v=dict(format='owr-observer-test-request-v1',site_id='site',request_id=str(uuid.uuid4()),created_at=int(time.time()),expected_hash='a'*64,revision=1,revision_token='rev1',channel_id='phone')
  path='/state/'+v['request_id']+'.json'
  put(client,path,v);check(pull().returncode==0,'real SSH independent test request durably acknowledged')
  put(client,path,v);check(pull().returncode==0,'independent test lost acknowledgement replay accepted')
  count=int(ex(server,'python3','-c',"import sqlite3;print(sqlite3.connect('/public/inbox.sqlite').execute('select count(*) from inbox').fetchone()[0])").stdout)
  check(count==2,'settings and test requests coexist without duplicates')
  put(client,path,dict(v,body='injected notification'));check(pull().returncode!=0,'test request arbitrary message rejected')
  check(ex(client,'test','-f',path,check=False).returncode==0,'invalid test request retained for diagnosis')
finally:
 for host in reversed(created):run('docker','rm','-f','-v',host,check=False)
Path(sys.argv[1]).write_text(json.dumps(dict(checks=checks,passed=len(checks),external_notifications_sent=0),indent=2)+'\n')
