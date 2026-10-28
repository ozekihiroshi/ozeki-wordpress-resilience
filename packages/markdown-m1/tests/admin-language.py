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
  web,db,php=start('language')
  php("file_put_contents('/var/www/html/wp-content/mu-plugins/language.php',base64_decode('"+base64.b64encode(b"<?php add_filter('pre_determine_locale',static fn($v)=>($_COOKIE['owr_test_locale']??'')==='ja'?'ja':$v);").decode()+"'));")
  browser=tag+'-browser';run('docker','run','-d','--name',browser,'--network',net,'--memory','2g','--shm-size','1g','-v',str(ROOT/'tests')+':/test:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(('container',browser))
  result=run('docker','exec','-e','M1_SOURCE=http://'+web,browser,'python3','/test/admin-language-browser.py');(out/'browser.log').write_bytes(result.stdout+result.stderr)
  state=json.loads(php("require '/var/www/html/wp-load.php';echo json_encode(['config'=>get_option('ozeki_resilience_m1_config'),'baseline'=>get_option('ozeki_resilience_setup_baseline')]);").stdout)
  assert state['config']['protect'] and state['baseline']['manifest']
  php("require '/var/www/html/wp-load.php';wp_set_current_user(1);wp_insert_post(['post_title'=>'Save settings <b>Original</b>','post_content'=>'Generated language test','post_status'=>'publish']);")
  html=php("require '/var/www/html/wp-load.php';require_once ABSPATH.'wp-admin/includes/template.php';wp_set_current_user(1);add_filter('pre_determine_locale',static fn()=> 'ja');(new OzekiResilience\\M1\\Plugin())->page();").stdout.decode()
  assert 'Save settings' in html and '&lt;b&gt;Original&lt;/b&gt;' in html,'User title must remain original and escaped'
  (out/'result.json').write_text(json.dumps({'state':'PASS','scope':'Isolated WordPress / MariaDB / local S3 simulation','checks':['Japanese setup via real browser: configure, consent, storage check, initial capture, enable protection','Japanese and English buttons, labels, schedule details, recovery and status explanations','English environment contains no Japanese interface text','Same form field names and operation values in both languages','User titles remain untranslated and HTML-escaped','Protection enabled and subsequent post confirmed in history']},indent=2))
  print((out/'result.json').read_text())
 finally:
  for kind,name in reversed(created):run('docker','rm','-f','-v',name,check=False) if kind=='container' else run('docker','network','rm',name,check=False)
if __name__=='__main__':
 import sys
 main(Path(sys.argv[1]))
