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
 prefix='owr-preflight-relay-'+secrets.token_hex(5);db=prefix+'-db';host=prefix+'-host';created=[];checks=[]
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
   before=dump();files={str(f.relative_to(site)):hashlib.sha256(f.read_bytes()).hexdigest() for f in site.rglob('*') if f.is_file()}
   q,report=probe();assert q.returncode==0 and report['facts']['database']['engines']==['InnoDB'];assert report['facts']['files']['bytes']>0
   assert before==dump();assert files=={str(f.relative_to(site)):hashlib.sha256(f.read_bytes()).hexdigest() for f in site.rglob('*') if f.is_file()}
   assert run('docker','exec',host,'test','-e','/tmp/SHOULD_NOT_RUN',check=False).returncode!=0
   checks.append('real SELECT-only MariaDB and read-only site scan; DB/file hashes unchanged; wp-config not executed')
   v={k:c[k] for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')};v.update(format='owr-deployment-inventory-v1',config_sha256=pre.capture.digest(c),observed_at=report['observed_at'],incomplete_runs=0,uncertain_puts=0)
   work=root/'work';work.mkdir(mode=0o700)
   def assess(rpt):return check.integrate(pre.assess(c,v,work),c,rpt,nonce)
   integrated=assess(report);assert integrated['state']=='needs_configuration' and any(x['code']=='host_unverified_scope_remaining' for x in integrated['issues'])
   checks.append('measured facts connected to preflight; unobserved writer/queue/control scope remains blocked')
   # Verify actual CLI composition, not only function calls.
   for name,value in [('profile',c),('inventory',v),('host',report)]: (root/(name+'.json')).write_text(json.dumps(value))
   command=['python3','-B',str(ROOT/'tools/deployment-preflight.py'),'--profile',str(root/'profile.json'),'--inventory',str(root/'inventory.json'),'--workspace',str(work),'--host-report',str(root/'host.json'),'--host-nonce',nonce]
   q=run(*command,check=False);assert q.returncode==2 and json.loads(q.stdout)['host_observation']['state']=='validated_report';checks.append('CLI report binding and conservative verdict')
   denied=run('docker','exec',host,'php','-r',"mysqli_report(MYSQLI_REPORT_OFF);$d=new mysqli('127.0.0.1','inspector',getenv('OWR_INV_DB_PASSWORD'),'lab');exit($d->query('INSERT INTO wp_posts VALUES(999)')===false?0:1);",check=False);assert denied.returncode==0;assert before==dump();checks.append('SELECT-only credentials reject writes in separate negative test')
   sql('CREATE TABLE foreign_engine(ID int) ENGINE=MyISAM;');_,bad=probe();assert assess(bad)['state']=='unsupported';sql('DROP TABLE foreign_engine;');checks.append('actual unsupported engine detected')
   (site/'outside-link').symlink_to('/etc/passwd');_,bad=probe();assert assess(bad)['state']=='unsupported';(site/'outside-link').unlink();checks.append('symlink detected without following target')
   wrong=dict(report,nonce='0'*32);assert assess(wrong)['host_observation']['state']=='invalid';checks.append('wrong nonce rejected')
   for name,value in [('profile',c),('inventory',v)]:put(client,'/'+name+'.json',value)
   ex(client,'mkdir','-m','700','/work')
   cli=['python3','-B','/repo/tools/host-inventory-ssh.py','inspect','--config','/connection.json','--profile','/profile.json','--inventory','/inventory.json','--workspace','/work']
   def inspect():return ex(client,*cli,check=False)
   q=inspect();assert q.returncode==2 and json.loads(q.stdout)['host_observation']['state']=='validated_report';checks.append('actual SSH inspect CLI reaches preflight')
   assert ex(host,'runuser','-u','inspector','--','test','-w','/opt/owr/host-inventory.php',check=False).returncode!=0
   assert ex(host,'runuser','-u','inspector','--','test','-w','/var/www/html',check=False).returncode!=0
   checks.append('probe account cannot modify code or site')
   q=ex(client,*(base[:-1]+['id']),input=b'{}',check=False);assert q.returncode!=0;checks.append('arbitrary command rejected by forced endpoint')
   q=ex(client,*base,input=json.dumps(dict(site_id='wrong',config_sha256=pre.capture.digest(c),nonce=nonce)).encode(),check=False);assert q.returncode!=0;checks.append('foreign site request rejected')
   put(client,'/known',pin+(root/'wrong.pub').read_text());q=inspect();assert json.loads(q.stdout)['host_observation']['state']=='unavailable';checks.append('wrong host key fails closed')
   put(client,'/known',pin+(root/'hostkey.pub').read_text());assert json.loads(inspect().stdout)['host_observation']['state']=='validated_report';checks.append('pin restored recovers')
   ex(host,'pkill','-x','sshd');q=inspect();assert json.loads(q.stdout)['host_observation']['state']=='unavailable';checks.append('SSH service stopped is unavailable, no cached success')
   ex(host,'/usr/sbin/sshd','-f','/etc/owr/sshd');assert json.loads(inspect().stdout)['host_observation']['state']=='validated_report';checks.append('SSH service restart recovers')
   relay=load('preflight-relay')
   ex(client,'mkdir','-m','750','/publish','/health','/private')
   rc=dict(site_id=c['site_id'],config_sha256=pre.capture.digest(c),report_file='/publish/report.json',health_file='/health/health.json',lock_file='/private/lock',profile_file='/profile.json',inventory_file='/inventory.json',connection_file='/connection.json',workspace='/work')
   put(client,'/relay.json',rc,'600')
   relaycmd=['python3','-B','/repo/tools/preflight-relay.py','--config','/relay.json']
   def once():return ex(client,*relaycmd,'--interval','0',check=False)
   snapshots={}
   def snap(label):
    snapshots[label]=dict(report=json.loads(ex(client,'cat','/publish/report.json').stdout),health=json.loads(ex(client,'cat','/health/health.json').stdout))
   assert once().returncode==0;snap('ok');checks.append('actual SSH relay publishes bound report and health')
   ex(host,'pkill','-x','sshd');assert once().returncode==2;snap('acquisition_failed');assert snapshots['acquisition_failed']['health']['state']=='acquisition_failed';checks.append('SSH outage replaces old success with current acquisition failure')
   ex(host,'/usr/sbin/sshd','-f','/etc/owr/sshd');assert once().returncode==0
   old=ex(client,'cat','/publish/report.json').stdout
   ex(client,'mv','/publish/report.json','/publish/previous.json');ex(client,'mkdir','/publish/report.json')
   assert once().returncode==2
   health=json.loads(ex(client,'cat','/health/health.json').stdout);assert health['state']=='transfer_failed'
   assert ex(client,'cat','/publish/previous.json').stdout==old
   snapshots['transfer_failed']=dict(report=json.loads(old),health=health)
   ex(client,'rmdir','/publish/report.json');ex(client,'mv','/publish/previous.json','/publish/report.json');checks.append('publication failure preserves previous bytes and updates separate health')
   # Actual periodic process, no fake scheduler or timestamp changes.
   ex(client,'sh','-c','python3 -B /repo/tools/preflight-relay.py --config /relay.json --interval 2 > /private/loop.log 2>&1 & echo $! > /private/pid')
   first=json.loads(ex(client,'cat','/health/health.json').stdout)['attempted_at']
   limit=time.monotonic()+30
   while json.loads(ex(client,'cat','/health/health.json').stdout)['attempted_at']==first:
    if time.monotonic()>limit:raise AssertionError('periodic update deadline')
    time.sleep(1)
   snap('recovered');assert snapshots['recovered']['health']['state']=='ok'
   assert once().returncode!=0;checks.append('periodic updates and duplicate loop refusal')
   pid=ex(client,'cat','/private/pid').stdout.decode().strip();assert pid.isdigit();ex(client,'kill',pid)
   time.sleep(3);snap('stopped');beforehealth=ex(client,'cat','/health/health.json').stdout
   print('waiting 305 seconds for actual stopped publisher aging',flush=True)
   time.sleep(305)
   assert ex(client,'cat','/health/health.json').stdout==beforehealth
   from datetime import datetime,timezone
   assert (datetime.now(timezone.utc)-datetime.fromisoformat(snapshots['stopped']['health']['attempted_at'])).total_seconds()>=300
   checks.append('actual process stop leaves report and health stale after five minutes')
   assert once().returncode==0;snap('restarted');checks.append('restart publishes fresh matching pair')
   (a.output/'relay-snapshots.json').write_text(json.dumps(snapshots,indent=2))
   run('docker','stop',db);q,bad=probe();assert q.returncode==0 and bad==dict(format='owr-host-inventory-v1',status='probe_failed',stage='database');checks.append('database unavailable yields redacted failure, never healthy inventory')
   (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,host_report=report,preflight=integrated,scope='generated MariaDB/WordPress-shaped tables and real local files; real pinned SSH between dedicated containers; no WP bootstrap or production host',environment_incidents=[],product_defects=[]),indent=2))
 finally:
  for name in reversed(created):run('docker','rm','-f','-v',name)
 print(json.dumps({'passed':True,'checks':len(checks),'containers_removed':True}),flush=True)
if __name__=='__main__':main()
