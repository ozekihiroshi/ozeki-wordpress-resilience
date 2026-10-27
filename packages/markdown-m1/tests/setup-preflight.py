"""Dedicated, generated-data acceptance. Docker is test infrastructure, not product runtime."""
import argparse,base64,ipaddress,json,os,secrets,shutil,subprocess,time,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True):
 p=subprocess.run(args,input=input,capture_output=True,timeout=900)
 if check and p.returncode:raise RuntimeError(str(args[:4])+': '+p.stderr.decode(errors='replace')[-1800:]+p.stdout.decode(errors='replace')[-1500:])
 return p
def main(out):
 out.mkdir(parents=True,exist_ok=False);lab=out/'lab';lab.mkdir();os.chmod(lab,0o777);(lab/'control.json').write_text('{}');os.chmod(lab/'control.json',0o666);(lab/'ipc').mkdir();os.chmod(lab/'ipc',0o777)
 plugin=out/'plugins'/'ozeki-wordpress-resilience'
 shutil.copytree(ROOT,plugin,ignore=shutil.ignore_patterns('tests','vendor'))
 sdk=Path('/home/ozeki/.local/share/owr-editor-reconstruct-source-20261023/kit/vendor');shutil.copytree(sdk,plugin/'vendor')
 with zipfile.ZipFile('/mnt/d/workspace/ozeki-markdown-documents/build/ozeki-markdown-documents-0.1.1.zip') as z:z.extractall(out/'plugins')
 (out/'resources.json').write_text('{}');created=[]
 tag='owr-md-m1-'+uuid.uuid4().hex[:8];net=tag+'-net'
 ids=run('docker','network','ls','-q').stdout.decode().split();used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in n['IPAM']['Config'] or [] if 'Subnet' in c]
 subnet=next(str(n) for n in ipaddress.ip_network('10.251.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
 run('docker','network','create','--subnet',subnet,net);created.append(('network',net))
 def start(suffix):
  web=tag+'-'+suffix;db=web+'-db'
  run('docker','run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only','mariadb:11.8');created.append(('container',db))
  run('docker','run','-d','--name',web,'--network',net,'--memory','768m','--tmpfs','/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('DISALLOW_FILE_MODS',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'-v',str(out/'plugins')+':/plugins:ro','-v',str(lab)+':/lab','-v',str(ROOT/'tests')+':/test:ro','wordpress:php8.3-apache');created.append(('container',web))
  def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
  for _ in range(90):
   if php("try{$m=new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);}catch(Throwable $e){exit(1);}",False).returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
   time.sleep(1)
  else:raise RuntimeError('Database/startup timeout')
  php("define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('M1 generated trial','operator','operator@example.invalid',false,'','lab-only-password');update_option('siteurl','http://"+web+"');update_option('home','http://"+web+"');mkdir(ABSPATH.'wp-content/mu-plugins',0777,true);file_put_contents(ABSPATH.'wp-content/mu-plugins/trial.php',\"<?php require '/test/transport.php';\");")
  php("require '/var/www/html/wp-load.php';require_once ABSPATH.'wp-admin/includes/plugin.php';foreach(['ozeki-markdown-documents/ozeki-markdown-documents.php','ozeki-wordpress-resilience/ozeki-wordpress-resilience.php'] as $p){symlink('/plugins/'.dirname($p),ABSPATH.'wp-content/plugins/'.dirname($p));wp_clean_plugins_cache();$r=activate_plugin($p);if(is_wp_error($r))throw new Exception($p.': '.$r->get_error_message());}")

  return web,db,php
 try:
  web,db,php=start('source')
  (lab/'setup-commands.log').touch();os.chmod(lab/'setup-commands.log',0o666)
  def wp(code):return php("require '/var/www/html/wp-load.php';require_once ABSPATH.'wp-admin/includes/template.php';wp_set_current_user(1);"+code).stdout.decode()
  def action(data):
   payload=base64.b64encode(json.dumps(data).encode()).decode()
   wp("$_POST=json_decode(base64_decode('"+payload+"'),true);$_REQUEST=$_POST;$_REQUEST['_wpnonce']=wp_create_nonce('owr_m1');(new Owr\\M1\\Plugin())->action();")
  def state():return json.loads(wp("echo json_encode(['config'=>get_option('owr_m1_config',[]),'error'=>get_option('owr_m1_error',''),'storage'=>get_option('owr_setup_storage',[]),'baseline'=>get_option('owr_setup_baseline',[])]);"))
  def page():return wp("(new Owr\\M1\\Plugin())->page();")
  def control(v):(lab/'control.json').write_text(json.dumps(v))
  checks=[]
  html=page();assert 'Preparation for protection' in html and 'confirm_terms' in html
  assert not (lab/'setup-commands.log').read_text(),'No S3 calls before configuration consent'
  checks.append('Fresh setup renders without external calls')
  settings=dict(operation='configure',bucket='m1-generated',region='ap-northeast-1',prefix='m1/',owner='',setup_role='source')
  action(settings);assert not state()['config'] and 'terms' in state()['error']
  action(settings|dict(confirm_terms='1',protect='1'));assert not state()['config'] and 'initial snapshot' in state()['error']
  settings['confirm_terms']='1';action(settings);assert not state()['error'] and not state()['config']['protect']
  checks.append('Server rejects missing consent and protection before baseline')
  control({'versioning':'Suspended'});action({'operation':'setup_check'});assert not state()['storage']['ok'] and 'enable S3' in state()['storage']['message']
  control({'fail':'setup'});action({'operation':'setup_check'});assert not state()['storage']['ok'] and 'private request' not in state()['storage']['message']
  control({});action({'operation':'setup_check'});assert state()['storage']['ok']
  commands=(lab/'setup-commands.log').read_text().splitlines();assert set(commands)<= {'GetBucketVersioning','ListObjectsV2'},commands
  checks.append('Read-only storage check, suspended versioning and sanitized failure guidance')
  wp("global $wpdb;$wpdb->query('ALTER TABLE '.$wpdb->posts.' ENGINE=MyISAM');")
  assert 'wp_posts' in page()
  action(dict(operation='whole_initial',trust_initial='1'));assert 'InnoDB' in state()['error']
  wp("global $wpdb;$wpdb->query('ALTER TABLE '.$wpdb->posts.' ENGINE=InnoDB');")
  checks.append('Non-InnoDB database blocks capture with named table and next action')
  action(dict(operation='whole_initial',trust_initial='1'));assert not state()['error'],state()['error'];assert state()['baseline']['manifest']
  action(settings|dict(protect='1'));assert not state()['error'] and state()['config']['protect']
  post=wp("echo wp_insert_post(['post_title'=>'Setup protected post','post_content'=>'Generated setup test','post_status'=>'publish']);")
  assert 'Setup protected post' in wp("echo json_encode((new Owr\\M1\\Plugin())->store()->history());")
  checks.append('Initial capture, fixed-version read-back, protection and confirmed post history')
  action(settings|dict(prefix='different/',protect='1'));assert 'initial snapshot' in state()['error'] and state()['config']['prefix']=='m1/'
  checks.append('Changing destination cannot reuse baseline or enable protection')
  action(settings|dict(setup_role='recovery'));assert not state()['config']['protect']
  html=page();assert 'Recovery destination:' in html and 'name="operation" value="whole_initial"' not in html and 'name="operation" value="initial_snapshot"' not in html
  action(dict(operation='whole_initial',trust_initial='1'));assert 'recovery destination' in state()['error']
  action(dict(operation='initial_snapshot',trust_initial='1'));assert 'recovery destination' in state()['error']
  checks.append('Recovery destination hides and rejects both initial capture paths')
  action(settings|dict(protect='1'));assert not state()['error']
  wp("update_option('WPLANG','ja');update_user_meta(1,'locale','ja');")
  html=wp("add_filter('pre_determine_locale',static fn()=> 'ja');(new Owr\\M1\\Plugin())->page();");(out/'setup-ja.html').write_text(html)
  assert '保護開始までの準備状況' in html and '了承しました' in html
  wp("update_option('WPLANG','en_US');update_user_meta(1,'locale','en_US');")
  (out/'setup-en.html').write_text(page())
  checks.append('Japanese and English preparation and terms text')
  # Existing installations keep service access; confirmation is still required on settings save.
  wp("$c=get_option('owr_m1_config');unset($c['setup_version'],$c['terms_version']);update_option('owr_m1_config',$c);")
  assert 'Existing settings remain in use' in page()
  wp("echo count((new Owr\\M1\\Plugin())->store()->history());")
  checks.append('Legacy configured installation retains authorized service access')
  browser=tag+'-browser';run('docker','run','-d','--name',browser,'--network',net,'--memory','2g','--shm-size','1g','-v',str(ROOT/'tests')+':/test:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(('container',browser))
  result=run('docker','exec','-e','M1_SOURCE=http://'+web,browser,'python3','/test/setup-preflight-browser.py');(out/'browser.log').write_bytes(result.stdout+result.stderr)
  checks.append('Chromium desktop and mobile layout, consent control and role selector')
  (out/'result.json').write_text(json.dumps({'state':'PASS','scope':'Generated isolated WordPress and MariaDB; synthetic S3 SDK transport, no AWS or existing sites','checks':checks},ensure_ascii=False,indent=2))
  print((out/'result.json').read_text(),flush=True)
 finally:
  for kind,name in reversed(created):run('docker','rm','-f','-v',name,check=False) if kind=='container' else run('docker','network','rm',name,check=False)
if __name__=='__main__':
 import sys
 main(Path(sys.argv[1]))
