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
 prefix='owr-host-inventory-'+secrets.token_hex(5);db=prefix+'-db';host=prefix+'-host';created=[];checks=[]
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
   run('docker','run','-d','--name',host,'--network','container:'+db,'--read-only','--user','33:33','--env-file',str(e),'-v',str(site)+':/var/www/html:ro','-v',str(ROOT/'tools/host-inventory.php')+':/probe.php:ro','--entrypoint','sleep',images['OWR_WP_IMAGE'],'infinity');created.append(host)
   def probe():
    q=run('docker','exec',host,'php','-d','auto_prepend_file=','-d','auto_append_file=','/probe.php',check=False,timeout=35)
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
   run('docker','stop',db);q,bad=probe();assert q.returncode==2 and bad==dict(format='owr-host-inventory-v1',status='probe_failed',stage='database');checks.append('database unavailable yields redacted failure, never healthy inventory')
   (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,host_report=report,preflight=integrated,scope='generated MariaDB/WordPress-shaped tables and real local files; no WP bootstrap, SSH transport or production host',environment_incidents=[],product_defects=[]),indent=2))
 finally:
  for name in reversed(created):run('docker','rm','-f','-v',name)
 print(json.dumps({'passed':True,'checks':len(checks),'containers_removed':True}),flush=True)
if __name__=='__main__':main()
