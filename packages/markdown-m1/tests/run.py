"""Dedicated, generated-data acceptance. Docker is test infrastructure, not product runtime."""
import argparse,base64,ipaddress,json,os,secrets,shutil,subprocess,time,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True):
 p=subprocess.run(args,input=input,capture_output=True,timeout=900)
 if check and p.returncode:raise RuntimeError(str(args[:4])+': '+p.stderr.decode(errors='replace')[-1800:]+p.stdout.decode(errors='replace')[-1500:])
 return p
def main(out,live=False,plugin_zip=None):
 out.mkdir(parents=True,exist_ok=False);lab=out/'lab';lab.mkdir();os.chmod(lab,0o777);(lab/'control.json').write_text('{}');os.chmod(lab/'control.json',0o666);(lab/'ipc').mkdir();os.chmod(lab/'ipc',0o777)
 plugin=out/'plugins'/'ozeki-wordpress-resilience'
 if plugin_zip:
  with zipfile.ZipFile(plugin_zip) as z:z.extractall(out/'plugins')
 else:
  shutil.copytree(ROOT,plugin,ignore=shutil.ignore_patterns('tests','vendor'))
  sdk=Path('/home/ozeki/.local/share/owr-editor-reconstruct-source-20261023/kit/vendor');shutil.copytree(sdk,plugin/'vendor')
 with zipfile.ZipFile('/mnt/d/workspace/ozeki-markdown-documents/build/ozeki-markdown-documents-0.1.1.zip') as z:z.extractall(out/'plugins')
 live_store=None
 config={'bucket':'m1-generated','region':'ap-northeast-1','prefix':'m1/','protect':True,'retention_days':0}
 if live:
  from live_s3 import Live,BUCKET
  prefix='sites/isolated-queue-lab/sets/AWS-c057202610220001/coordinator/m1-'+secrets.token_hex(6)+'/'
  live_store=Live(lab,prefix);live_store.start();config.update(bucket=BUCKET,prefix=prefix,owner='121426368082',retention_days=36)
  (out/'scope.json').write_text(json.dumps(config))
 (out/'resources.json').write_text('{}');created=[]
 tag='owr-md-m1-'+uuid.uuid4().hex[:8];net=tag+'-net'
 ids=run('docker','network','ls','-q').stdout.decode().split();used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in n['IPAM']['Config'] or [] if 'Subnet' in c]
 subnet=next(str(n) for n in ipaddress.ip_network('10.251.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
 run('docker','network','create','--subnet',subnet,net);created.append(('network',net))
 def start(suffix):
  web=tag+'-'+suffix;db=web+'-db'
  run('docker','run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only','mariadb:11.8');created.append(('container',db))
  run('docker','run','-d','--name',web,'--network',net,'--memory','768m','--tmpfs','/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('DISALLOW_FILE_MODS',true);",'-v',str(out/'plugins')+':/plugins:ro','-v',str(lab)+':/lab','-v',str(ROOT/'tests')+':/test:ro','wordpress:php8.3-apache');created.append(('container',web))
  def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
  for _ in range(90):
   if php("try{$m=new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);}catch(Throwable $e){exit(1);}",False).returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
   time.sleep(1)
  else:raise RuntimeError('Database/startup timeout')
  php("define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('M1 generated trial','operator','operator@example.invalid',false,'','lab-only-password');update_option('siteurl','http://"+web+"');update_option('home','http://"+web+"');mkdir(ABSPATH.'wp-content/mu-plugins',0777,true);file_put_contents(ABSPATH.'wp-content/mu-plugins/trial.php',\"<?php require '/test/transport.php';\");")
  php("require '/var/www/html/wp-load.php';require_once ABSPATH.'wp-admin/includes/plugin.php';foreach(['ozeki-markdown-documents/ozeki-markdown-documents.php','ozeki-wordpress-resilience/ozeki-wordpress-resilience.php'] as $p){symlink('/plugins/'.dirname($p),ABSPATH.'wp-content/plugins/'.dirname($p));wp_clean_plugins_cache();$r=activate_plugin($p);if(is_wp_error($r))throw new Exception($p.': '.$r->get_error_message());}")
  php("require '/var/www/html/wp-load.php';update_option('owr_m1_config',json_decode(base64_decode('"+base64.b64encode(json.dumps(config).encode()).decode()+"'),true));")
  return web,db,php
 try:
  web,db,php=start('source')
  browser=tag+'-browser';run('docker','run','-d','--name',browser,'--network',net,'--memory','2g','--shm-size','1g','-v',str(ROOT/'tests')+':/test:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(('container',browser))
  with (out/'browser-source.log').open('wb') as log:
   p=subprocess.run(['docker','exec','-e','M1_SOURCE=http://'+web,browser,'python3','/test/browser.py'],stdout=log,stderr=log,timeout=1800)
  if p.returncode:raise RuntimeError('Source browser failed; see '+str(out/'browser-source.log'))
  expected=json.loads((lab/'expected.json').read_text())
  snapshot=json.loads(php("require '/var/www/html/wp-load.php';$p=new OzekiResilience\\M1\\Plugin();echo json_encode($p->store()->history());").stdout)
  assert len(snapshot)==7, len(snapshot)
  a_ids={r['original']['asset'] for r in snapshot if r['attributes']['title']=='M1 A'}
  b_ids={r['original']['asset'] for r in snapshot if r['attributes']['title']=='M1 B'}
  assert len(a_ids)==1 and len(b_ids)==1 and a_ids.isdisjoint(b_ids),'Stable distinct document identities across versions'
  for row in snapshot:
   ref=row['original']['source']
   raw=base64.b64decode(live_store.request('GetObject',{'Bucket':config['bucket'],'ExpectedBucketOwner':config['owner'],'Key':config['prefix']+ref['key'],'VersionId':ref['version']})['body64']).decode() if live else (lab/'objects'/'m1'/ref['key']).read_bytes().decode()
   assert '```mermaid' in raw or 'Document B' in raw
   assert __import__('hashlib').sha256(raw.encode()).hexdigest()==ref['sha256']
   (out/('direct-original-'+str(row['sequence'])+'.md')).write_text(raw)
  # The source container/DB are removed before a fresh WordPress exists.
  run('docker','rm','-f','-v',web,db);created.remove(('container',web));created.remove(('container',db))
  target,tdb,tphp=start('target')
  tphp("require '/var/www/html/wp-load.php';$c=get_option('owr_m1_config');$c['protect']=false;update_option('owr_m1_config',$c);wp_insert_post(['post_title'=>'Different IDs','post_status'=>'publish']);")
  result=run('docker','exec','-e','M1_TARGET=http://'+target,browser,'python3','/test/browser.py','restore');(out/'browser-target.log').write_bytes(result.stdout+result.stderr)
  restored=json.loads(tphp("require '/var/www/html/wp-load.php';$r=[];foreach(get_posts(['post_type'=>'ozmd_document','numberposts'=>-1]) as $p)$r[$p->post_title]=['source'=>get_post_meta($p->ID,'_ozmd_source',true),'status'=>$p->post_status,'slug'=>$p->post_name];echo json_encode($r);").stdout)
  assert restored==expected,(restored,expected)
  (out/'result.json').write_text(json.dumps({'state':'PASS','mode':'real experimental S3 (test-only role signing transport)' if live else 'local S3 API test double','formal_versions':len(snapshot),'source_destroyed_before_restore':True,'raw_attributes_status_equal':True},indent=2))
  print((out/'result.json').read_text(),flush=True)
 finally:
  (out/'resources.json').write_text(json.dumps(created))
  for kind,name in reversed(created):run('docker','rm','-f','-v',name,check=False) if kind=='container' else run('docker','network','rm',name,check=False)
  if live_store:live_store.stopped=True
if __name__=='__main__':
 import sys
 main(Path(sys.argv[1]),'--live' in sys.argv,Path(sys.argv[sys.argv.index('--zip')+1]) if '--zip' in sys.argv else None)
