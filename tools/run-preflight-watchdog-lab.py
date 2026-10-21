#!/usr/bin/env python3
"""Real MariaDB SELECT-only account and read-only site mount; generated data."""
import hashlib,importlib.util,json,os,secrets,subprocess,tempfile,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True,timeout=45):
 p=subprocess.run(args,input=input,capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('lab operation failed (private diagnostics retained by caller)')
 return p
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
 images=dict(x.split('=',1) for x in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in x)
 prefix='owr-preflight-watch-' +secrets.token_hex(5);db=prefix+'-db';host=prefix+'-host';created=[];checks=[];vm=None;events=[]
 print('LAB '+prefix,flush=True)
 try:
  with tempfile.TemporaryDirectory(prefix='owr-host-probe-') as temp:
   root=Path(temp);root.chmod(0o755);site=root/'site';site.mkdir(mode=0o755);(site/'wp-content/uploads').mkdir(parents=True);(site/'wp-content/uploads/generated.txt').write_text('generated media');(site/'wp-config.php').write_text('<?php throw new Exception("SHOULD_NOT_RUN");')
   secret=secrets.token_hex(20);env=root/'db-env';env.write_text(f'MARIADB_ROOT_PASSWORD={secret}\nMARIADB_DATABASE=lab\n');env.chmod(0o600)
   run('docker','run','-d','--name',db,'--network','none','--env-file',str(env),'--memory','512m',images['OWR_DB_IMAGE']);created.append(db)
   deadline=time.monotonic()+100
   while run('docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized',check=False).returncode:
    if time.monotonic()>deadline:raise RuntimeError('DB readiness deadline')
    time.sleep(1)
   def sql(text):return run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',input=text.encode()).stdout
   sql("CREATE TABLE wp_options(option_name varchar(64),option_value text) ENGINE=InnoDB; CREATE TABLE wp_posts(ID bigint) ENGINE=InnoDB; CREATE TABLE wp_postmeta(post_id bigint) ENGINE=InnoDB; INSERT INTO wp_options VALUES ('upload_path',''),('upload_url_path',''); CREATE USER 'inspector'@'%' IDENTIFIED BY '"+secret+"'; GRANT SELECT ON lab.* TO 'inspector'@'%';")
   c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());c['storage']['destination_ref']='generated';c['trust'].update(operator='lab',public_pin_ref='generated')
   pre=load('deployment-preflight');check=load('host-inventory-check');nonce=secrets.token_hex(16)
   cfg={'SITE':c['site_id'],'CONFIG_SHA256':pre.capture.digest(c),'NONCE':nonce,'DB_NAME':'lab','DB_PREFIX':'wp_','ROOT':'/var/www/html','DB_HOST':'127.0.0.1','DB_USER':'inspector','DB_PASSWORD':secret}
   e=root/'host-env';e.write_text(''.join('OWR_INV_'+k+'='+v+'\n' for k,v in cfg.items()));e.chmod(0o600)
   run('docker','run','-d','--name',host,'--network','container:'+db,'--env-file',str(e),'-v',str(site)+':/var/www/html:ro','-v',str(ROOT/'tools/host-inventory.php')+':/probe.php:ro','--entrypoint','sleep','owr-external-lab:local','infinity');created.append(host)
   ssh=load('host-inventory-ssh')
   client=prefix+'-client'
   run('docker','run','-d','--name',client,'--network','container:'+db,'-v',str(ROOT)+':/repo:ro','--entrypoint','sleep','owr-external-lab:local','infinity');created.append(client)
   for key in ('key','hostkey','wrong'):
    run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(root/key))
   def ex(name,*args,**kw):return run('docker','exec',*(['-i'] if kw.get('input') is not None else []),name,*args,**kw)
   def put(name,path,value,mode='644'):
    f=root/'upload';f.write_text(value if isinstance(value,str) else json.dumps(value));run('docker','cp',str(f),name+':'+path);ex(name,'chown','root:root',path);ex(name,'chmod',mode,path)
   ex(host,'mkdir','-p','/opt/owr','/etc/owr','/run/sshd')
   for file in ('host-inventory-ssh.py','notification-transfer.py','host-inventory.php'):
    run('docker','cp',str(ROOT/'tools'/file),host+':/opt/owr/'+file)
   ex(host,'chown','-R','root:root','/opt/owr');ex(host,'chmod','-R','go-w','/opt/owr')
   ex(host,'useradd','-m','-s','/bin/sh','inspector');ex(host,'usermod','-p','*','inspector')
   put(host,'/etc/owr/hostkey',(root/'hostkey').read_text(),'600')
   put(host,'/etc/owr/keys','restrict,command="/usr/bin/python3 -B /opt/owr/host-inventory-ssh.py endpoint --config /etc/owr/endpoint.json" '+(root/'key.pub').read_text())
   endpoint=dict(site_id=c['site_id'],config_sha256=pre.capture.digest(c),php='/usr/local/bin/php',probe={k:cfg[k] for k in ('DB_HOST','DB_NAME','DB_PREFIX','DB_USER','DB_PASSWORD','ROOT')})
   put(host,'/etc/owr/endpoint.json',endpoint,'640');ex(host,'chgrp','inspector','/etc/owr/endpoint.json')
   put(host,'/etc/owr/sshd','\n'.join(['Port 2222','HostKey /etc/owr/hostkey','PidFile /run/sshd/inventory.pid','AuthorizedKeysFile /etc/owr/keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','PermitRootLogin no','AllowUsers inspector','AllowTcpForwarding no','AllowAgentForwarding no','PermitTTY no','PermitUserEnvironment no','DisableForwarding yes'])+'\n')
   ex(host,'/usr/sbin/sshd','-f','/etc/owr/sshd')
   put(client,'/key',(root/'key').read_text(),'600')
   pin='owr-inventory-'+c['site_id']+' '
   put(client,'/known',pin+(root/'hostkey.pub').read_text())
   conn=dict(site_id=c['site_id'],host='127.0.0.1',user='inspector',port=2222,identity_file='/key',known_hosts='/known')
   put(client,'/connection.json',conn)
   base=ssh.command(conn)
   def probe(packet=None):
    packet=packet or dict(site_id=c['site_id'],config_sha256=pre.capture.digest(c),nonce=nonce)
    q=ex(client,*base,input=json.dumps(packet).encode(),check=False,timeout=25)
    assert secret.encode() not in q.stdout+q.stderr
    return q,json.loads(q.stdout)
   def dump():return run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --skip-comments --skip-dump-date lab').stdout
   import shlex,sys
   from datetime import datetime,timezone
   vmout=a.output/'vm';os.environ['OWR_TWO_VM_OUTPUT']=str(vmout);os.environ['OWR_TWO_VM_NETWORK_HOST']=host
   q=subprocess.run(['python3',str(ROOT/'lab/preflight-two-vm/start.py')],capture_output=True,timeout=600)
   if q.returncode:raise RuntimeError('twoVM startup '+q.stderr.decode()[-1500:])
   sys.path.insert(0,str(ROOT/'lab/preflight-two-vm'));import common as vmc
   vm=vmc.name()
   def remote(role,command,data=None,check=True,timeout=120):return vmc.remote(role,command,data=data,check=check,timeout=timeout)
   def write(role,path,value,mode=0o600,owner='root:root'):
    code='import pathlib,sys,subprocess;p=pathlib.Path('+repr(path)+');p.write_bytes(sys.stdin.buffer.read());p.chmod('+str(mode)+');subprocess.run(["chown",'+repr(owner)+',str(p)],check=True)'
    remote(role,'sudo python3 -c '+shlex.quote(code),(value if isinstance(value,str) else json.dumps(value)).encode())
   for role in ['source','receiver']:
    remote(role,"""set -eu
sudo mkdir -p /opt/owr /etc/owr /var/lib/owr-preflight /var/lib/owr-preflight-web
sudo tar -xf /tmp/payload.tar -C /opt/owr --strip-components=1
sudo useradd --system --no-create-home --shell /usr/sbin/nologin owr-preflight
sudo chown owr-preflight:www-data /var/lib/owr-preflight /var/lib/owr-preflight-web
sudo chmod 700 /var/lib/owr-preflight
sudo chmod 2750 /var/lib/owr-preflight-web
sudo chown -R root:root /opt/owr
sudo find /opt/owr -type d -exec chmod 755 {} +
sudo find /opt/owr -type f -exec chmod 644 {} +
sudo mkdir /var/lib/owr-preflight/work
sudo chown owr-preflight:www-data /var/lib/owr-preflight/work
sudo chmod 700 /var/lib/owr-preflight/work
""")
   base='/var/lib/owr-preflight';out='/var/lib/owr-preflight-web';digest=pre.capture.digest(c)
   inventory={k:c[k] for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')};inventory.update(format='owr-deployment-inventory-v1',config_sha256=digest,observed_at=datetime.now(timezone.utc).isoformat(),incomplete_runs=0,uncertain_puts=0)
   for name,value in [('profile',c),('inventory',inventory),('connection',dict(conn,host='10.0.2.2',identity_file=base+'/probe-key',known_hosts=base+'/probe-known'))]:write('source',base+'/'+name+'.json',value,owner='owr-preflight:www-data')
   write('source',base+'/probe-key',(root/'key').read_text(),owner='owr-preflight:www-data');write('source',base+'/probe-known',pin+(root/'hostkey.pub').read_text(),owner='owr-preflight:www-data')
   publisher=dict(site_id=c['site_id'],config_sha256=digest,profile_file=base+'/profile.json',inventory_file=base+'/inventory.json',connection_file=base+'/connection.json',workspace=base+'/work',report_file=out+'/report.json',health_file=out+'/health.json',lock_file=base+'/loop.lock')
   write('source','/etc/owr/preflight-relay.json',publisher,0o640,'root:www-data')
   write('source','/etc/systemd/system/owr-preflight.service',(ROOT/'examples/preflight-relay/owr-preflight.service').read_text(),0o644)
   # Only bounded public reports are readable through this key.
   run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(root/'transferkey'))
   remote('source','sudo useradd --system --no-create-home --shell /bin/sh --gid www-data owr-reader && sudo usermod -p "*" owr-reader')
   write('source','/etc/owr/read.json',dict(site_id=c['site_id'],config_sha256=digest,report_file=out+'/report.json',health_file=out+'/health.json'),0o640,'root:www-data')
   write('source','/etc/owr/authorized','restrict,command="/usr/bin/python3 -B /opt/owr/tools/preflight-transfer.py serve --config /etc/owr/read.json" '+(root/'transferkey.pub').read_text(),0o644)
   write('source','/etc/ssh/sshd_config.d/80-owr.conf','Match User owr-reader\n AuthorizedKeysFile /etc/owr/authorized\n AuthenticationMethods publickey\n DisableForwarding yes\n PermitTTY no\nMatch all\n',0o644)
   remote('source','sudo sshd -t && sudo systemctl reload ssh')
   receiver=dict(site_id=c['site_id'],config_sha256=digest,host='192.0.2.10',port=22,user='owr-reader',identity_file=base+'/transfer-key',known_hosts=base+'/known',report_file=out+'/report.json',health_file=out+'/health.json',lock_file=base+'/loop.lock')
   write('receiver',base+'/transfer-key',(root/'transferkey').read_text(),owner='owr-preflight:www-data');write('receiver',base+'/known','owr-preflight-'+c['site_id']+' '+(vmout/'source/host.pub').read_text(),owner='owr-preflight:www-data')
   write('receiver','/etc/owr/preflight-transfer.json',receiver,0o640,'root:www-data');write('receiver','/etc/systemd/system/owr-preflight-transfer.service',(ROOT/'examples/preflight-relay/owr-preflight-transfer.service').read_text(),0o644)
   for role,unit in [('source','owr-preflight'),('receiver','owr-preflight-transfer')]:remote(role,'sudo systemctl daemon-reload && sudo systemctl enable --now '+unit)
   def health():return json.loads(vmc.cat('receiver',out+'/health.json'))
   def wait(fn,label,seconds=200):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
     try:
      if fn():checks.append(label);print('PASS '+label,flush=True);return
     except (RuntimeError,ValueError,subprocess.TimeoutExpired):pass
     time.sleep(3)
    raise AssertionError(label)
   wait(lambda:health()['state']=='ok','real interVM SSH transfer')
   import importlib.util
   spec=importlib.util.spec_from_file_location('exercise',ROOT/'lab/preflight-watchdog/exercise.py');exercise=importlib.util.module_from_spec(spec);spec.loader.exec_module(exercise)
   exercise.run(ROOT,a.output,vmc,write,c,digest,checks)

 finally:
  vf=a.output/'vm/container-name'
  if vf.exists():
   name=vf.read_text();assert name.startswith('owr-two-vm-') and name.replace('-','').isalnum();run('docker','rm','-f','-v',name,check=False)
  for name in reversed(created):run('docker','rm','-f','-v',name,check=False)
 (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,resources_removed=True,scope='new preflight watchdog integration only; independent observer process outside two guest VMs; local HTTP notification receiver; same physical host; no WordPress UI repeat or external notification'),indent=2))
 print('ALL_PASS',flush=True)
if __name__=='__main__':main()
