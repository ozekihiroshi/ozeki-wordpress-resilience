#!/usr/bin/env python3
"""Real MariaDB SELECT-only account and read-only site mount; generated data."""
import hashlib,importlib.util,json,os,secrets,subprocess,tempfile,time
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
 prefix='owr-preflight-systemd-'+secrets.token_hex(5);db=prefix+'-db';host=prefix+'-host';created=[];checks=[];vm=None;events=[]
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
   import shlex
   from datetime import datetime,timezone
   status=a.output/'web-status';status.mkdir(mode=0o755)
   envvm=os.environ.copy();envvm.update(OWR_VM_LAB_OUTPUT=str(a.output/'vm'),OWR_VM_OBSERVER=host,OWR_VM_REPORTS=str(status))
   hostboot=Path('/proc/sys/kernel/random/boot_id').read_text()
   q=subprocess.run(['python3',str(ROOT/'lab/observer-relay-vm/start.py')],env=envvm,capture_output=True,timeout=400)
   if q.returncode:raise RuntimeError('VM boot failed: '+q.stderr.decode()[-1500:])
   vm=(a.output/'vm/container-name').read_text();vmssh=json.loads((a.output/'vm/ssh-command.json').read_text())
   def remote(command,data=None,check=True,timeout=90):
    q=subprocess.run(['docker','exec',*(['-i'] if data is not None else []),vm,*vmssh,command],input=data,capture_output=True,timeout=timeout)
    if check and q.returncode:raise RuntimeError('guest command failed: '+q.stderr.decode()[-1000:]+q.stdout.decode()[-1000:])
    return q
   def write(path,value,mode=0o600,owner='root:root'):
    code='import pathlib,sys,subprocess;p=pathlib.Path('+repr(path)+');p.write_bytes(sys.stdin.buffer.read());p.chmod('+str(mode)+');subprocess.run(["chown",'+repr(owner)+',str(p)],check=True)'
    remote('sudo python3 -c '+shlex.quote(code),(value if isinstance(value,str) else json.dumps(value)).encode())
   remote("""set -eu
sudo mkdir -p /opt/owr /etc/owr /var/lib/owr-preflight /var/lib/owr-preflight-web
sudo tar -xf /tmp/payload.tar -C /opt/owr --strip-components=1
sudo useradd --system --no-create-home --shell /usr/sbin/nologin owr-preflight
sudo chown owr-preflight:www-data /var/lib/owr-preflight
sudo chmod 700 /var/lib/owr-preflight
echo 'reports /var/lib/owr-preflight-web 9p trans=virtio,version=9p2000.L 0 0' | sudo tee -a /etc/fstab >/dev/null
sudo mount /var/lib/owr-preflight-web
sudo chown owr-preflight:www-data /var/lib/owr-preflight-web
sudo chmod 2750 /var/lib/owr-preflight-web
sudo chown -R root:root /opt/owr
sudo find /opt/owr -type d -exec chmod 755 {} +
sudo find /opt/owr -type f -exec chmod 644 {} +
sudo mkdir /var/lib/owr-preflight/work
sudo chown owr-preflight:www-data /var/lib/owr-preflight/work
sudo chmod 700 /var/lib/owr-preflight/work
""")
   base='/var/lib/owr-preflight';out='/var/lib/owr-preflight-web'
   write(base+'/key',(root/'key').read_text(),owner='owr-preflight:www-data')
   write(base+'/known',pin+(root/'hostkey.pub').read_text(),owner='owr-preflight:www-data')
   connection=dict(conn,host='10.0.2.2',identity_file=base+'/key',known_hosts=base+'/known')
   inventory={k:c[k] for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')};inventory.update(format='owr-deployment-inventory-v1',config_sha256=pre.capture.digest(c),observed_at=datetime.now(timezone.utc).isoformat(),incomplete_runs=0,uncertain_puts=0)
   for name,value in [('profile',c),('inventory',inventory),('connection',connection)]:write(base+'/'+name+'.json',value,owner='owr-preflight:www-data')
   relay=dict(site_id=c['site_id'],config_sha256=pre.capture.digest(c),profile_file=base+'/profile.json',inventory_file=base+'/inventory.json',connection_file=base+'/connection.json',workspace=base+'/work',report_file=out+'/report.json',health_file=out+'/health.json',lock_file=base+'/loop.lock')
   write('/etc/owr/preflight-relay.json',relay,0o640,'root:www-data')
   write('/etc/systemd/system/owr-preflight.service',(ROOT/'examples/preflight-relay/owr-preflight.service').read_text(),0o644)
   remote('sudo systemctl daemon-reload && sudo systemctl enable --now owr-preflight')
   def read(name):return remote('sudo cat '+out+'/'+name).stdout
   def health():return json.loads(read('health.json'))
   def wait(fn,label,seconds=180):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
     try:
      if fn():checks.append(label);print('PASS '+label,flush=True);return
     except (RuntimeError,json.JSONDecodeError,subprocess.TimeoutExpired):pass
     time.sleep(2)
    raise AssertionError(label)
   wait(lambda:health()['state']=='ok','systemd starts real SSH inventory')
   first=health()['attempted_at'];wait(lambda:health()['attempted_at']!=first,'unmodified60second service updates')
   def verify(label):
    raw=remote('systemctl show owr-preflight --property=ActiveState,SubState,UnitFileState,User,Group,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp,MainPID').stdout.decode()
    props=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
    for k,v in dict(ActiveState='active',SubState='running',UnitFileState='enabled',User='owr-preflight',Group='www-data',NoNewPrivileges='yes',ProtectSystem='strict',ProtectHome='yes',PrivateTmp='yes').items():assert props[k]==v,(k,props)
    assert remote('sudo -u www-data test -w '+out+'/report.json',check=False).returncode!=0
    assert remote('sudo -u www-data test -r '+base+'/key',check=False).returncode!=0
    assert remote('sudo runuser -u owr-preflight -g www-data -- python3 -B /opt/owr/tools/preflight-relay.py --config /etc/owr/preflight-relay.json --interval 0',check=False).returncode!=0
    (a.output/(label+'.json')).write_text(json.dumps(props,indent=2));checks.append(label+' identity hardening permissions and duplicate rejection')
   verify('before-stop')
   ui=load('preflight-vm-ui')
   def screen(browser,mode,label):
    q=run('docker','exec',browser,'python3','/lab/preflight-systemd-browser.py',mode,timeout=180)
    (a.output/(label+'-browser.json')).write_bytes(q.stdout)
    run('docker','cp',browser+':/tmp/preflight-'+mode+'.png',str(a.output/(label+'.png')));checks.append(label+' browser accepted');print('PASS '+label,flush=True)
   with ui.ui_session(status,pre.capture.digest(c)) as (web,browser):
    screen(browser,'ok','running')
    remote('sudo systemctl stop owr-preflight');frozen={n:read(n) for n in ['report.json','health.json']}
    stopped=remote('systemctl show owr-preflight --property=ActiveState,SubState,UnitFileState,MainPID').stdout.decode();assert 'ActiveState=inactive' in stopped and 'MainPID=0' in stopped and 'UnitFileState=enabled' in stopped
    (a.output/'stopped-unit.txt').write_text(stopped)
    start=time.monotonic()
    while time.monotonic()-start<310:
     time.sleep(10);assert all(read(n)==v for n,v in frozen.items());print('STOPPED_SECONDS '+str(round(time.monotonic()-start)),flush=True)
    screen(browser,'stopped','stopped')
    old=health()['attempted_at'];remote('sudo systemctl start owr-preflight');wait(lambda:health()['state']=='ok' and health()['attempted_at']!=old,'explicit service restart refreshes report');screen(browser,'restarted','resumed')
    before=remote('cat /proc/sys/kernel/random/boot_id').stdout.decode().strip();old=health()['attempted_at'];remote('sudo systemctl reboot',check=False,timeout=15)
    def boot():return remote('cat /proc/sys/kernel/random/boot_id',timeout=12).stdout.decode().strip()
    wait(lambda:bool(boot()) and boot()!=before,'guest reboot changes BootID',240)
    wait(lambda:health()['state']=='ok' and health()['attempted_at']!=old,'enabled service automatically refreshes after reboot')
    verify('after-reboot');screen(browser,'restarted','reboot-recovered')
    assert Path('/proc/sys/kernel/random/boot_id').read_text()==hostboot;checks.append('WSL observation host BootID unchanged')
    (a.output/'boot.json').write_text(json.dumps(dict(before=before,after=boot(),host_unchanged=True),indent=2))
    (a.output/'service-journal.txt').write_bytes(remote('sudo journalctl -u owr-preflight --no-pager -n 70').stdout)
    remote('sudo systemctl poweroff',check=False,timeout=15)
 finally:
  vmfile=a.output/'vm/container-name'
  if vmfile.exists():
   name=vmfile.read_text();assert name.startswith('owr-production-vm-') and name.replace('-','').isalnum();run('docker','rm','-f','-v',name,check=False)
  for name in reversed(created):run('docker','rm','-f','-v',name,check=False)
 (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,resources_removed=True,real_guest_reboot=True,interval_seconds=60,scope='real dedicated UbuntuVM systemd and pinned SSH/MariaDB; WordPress reads actual VM outputs via9p share; no rebased times; generated data; same physical host'),indent=2))
 print('ALL_PASS',flush=True)
if __name__=='__main__':main()
