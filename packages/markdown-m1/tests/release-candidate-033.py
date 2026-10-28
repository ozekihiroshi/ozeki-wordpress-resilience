"""Candidate ZIP acceptance. Args: output-dir candidate.zip previous.zip wp-cli.phar plugin-check.zip. Docker only; generated data and synthetic S3."""
import argparse,base64,ipaddress,json,os,secrets,shutil,subprocess,time,uuid,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(*args,input=None,check=True):
 p=subprocess.run(args,input=input,capture_output=True,timeout=900)
 if check and p.returncode:raise RuntimeError(str(args[:4])+': '+p.stderr.decode(errors='replace')[-1800:]+p.stdout.decode(errors='replace')[-1500:])
 return p
def main(out, candidate, previous, wpcli, checker, acf=None):
 out.mkdir(parents=True,exist_ok=False);lab=out/'lab';lab.mkdir();os.chmod(lab,0o777);(lab/'control.json').write_text('{}');os.chmod(lab/'control.json',0o666);(lab/'ipc').mkdir();os.chmod(lab/'ipc',0o777)
 plugin=out/'plugins'/'ozeki-resilience'
 (out/'plugins').mkdir()
 for src,name in [(candidate,'candidate.zip'),(previous,'previous.zip'),(wpcli,'wp'),(checker,'plugin-check.zip')]:shutil.copyfile(src,lab/name)
 (out/'resources.json').write_text('{}');created=[]
 tag='owr-md-m1-'+uuid.uuid4().hex[:8];net=tag+'-net'
 ids=run('docker','network','ls','-q').stdout.decode().split();used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in n['IPAM']['Config'] or [] if 'Subnet' in c]
 subnet=next(str(n) for n in ipaddress.ip_network('10.251.0.0/16').subnets(new_prefix=28) if not any(n.overlaps(u) for u in used if n.version==u.version))
 run('docker','network','create','--subnet',subnet,net);created.append(('network',net))
 def start(suffix):
  web=tag+'-'+suffix;db=web+'-db'
  run('docker','run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=lab-only','-e','MARIADB_DATABASE=wordpress','-e','MARIADB_USER=wordpress','-e','MARIADB_PASSWORD=lab-only','mariadb:11.8');created.append(('container',db))
  run('docker','run','-d','--name',web,'--network',net,'--memory','768m','--tmpfs','/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_USER=wordpress','-e','WORDPRESS_DB_PASSWORD=lab-only','-e','WORDPRESS_DB_NAME=wordpress','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'-v',str(out/'plugins')+':/plugins:ro','-v',str(lab)+':/lab','-v',str(ROOT/'tests')+':/test:ro','wordpress:php8.3-apache');created.append(('container',web))
  def php(code,check=True):return run('docker','exec','-i',web,'php',input=('<?php '+code).encode(),check=check)
  for _ in range(90):
   if php("try{$m=new mysqli(getenv('WORDPRESS_DB_HOST'),'wordpress','lab-only','wordpress');exit($m->connect_errno?1:0);}catch(Throwable $e){exit(1);}",False).returncode==0 and run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode==0:break
   time.sleep(1)
  else:raise RuntimeError('Database/startup timeout')
  php("define('WP_INSTALLING',true);require '/var/www/html/wp-load.php';require ABSPATH.'wp-admin/includes/upgrade.php';wp_install('M1 generated trial','operator','operator@example.invalid',false,'','lab-only-password');update_option('siteurl','http://"+web+"');update_option('home','http://"+web+"');mkdir(ABSPATH.'wp-content/mu-plugins',0777,true);file_put_contents(ABSPATH.'wp-content/mu-plugins/trial.php',\"<?php require '/test/transport.php';\");")


  return web,db,php
 try:
  web,db,php=start('language')
  def wp(web,*args,check=True):return run('docker','exec',web,'php','/lab/wp',*args,'--allow-root',check=check).stdout.decode()
  print(wp(web,'plugin','install','/lab/candidate.zip','--activate'),flush=True)
  assert wp(web,'plugin','get','ozeki-resilience','--field=version').strip()=='0.3.3'
  with zipfile.ZipFile(candidate) as z:expected={n.split('/',1)[1]:__import__('hashlib').sha256(z.read(n)).hexdigest() for n in z.namelist() if not n.endswith('/')}
  hashcode="$r=ABSPATH.'wp-content/plugins/ozeki-resilience/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($r,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($r))]=hash_file('sha256',$f->getPathname());echo json_encode($a);"
  assert json.loads(wp(web,'eval',hashcode))==expected

  php("file_put_contents('/var/www/html/wp-content/mu-plugins/language.php',base64_decode('"+base64.b64encode(b"<?php add_filter('pre_determine_locale',static fn($v)=>($_COOKIE['owr_test_locale']??'')==='ja'?'ja':$v);").decode()+"'));")
  wp(web,'eval',"wp_set_current_user(1);wp_mkdir_p(wp_upload_dir()['basedir']);update_option('owr_m1_config',['bucket'=>'m1-generated','region'=>'ap-northeast-1','prefix'=>'fresh/','retention_days'=>0,'protect'=>false]);$p=new Owr\\M1\\Plugin();$point=(new Owr\\M1\\SiteSnapshot($p->store()))->capture(true,[]);update_option('owr_site_initial',$point);$c=$p->config();update_option('owr_setup_baseline',['identity'=>Owr\\M1\\SetupReadiness::identity($c),'manifest'=>$point['manifest']]);Owr\\M1\\SetupReadiness::requireStart($c);$c['protect']=true;update_option('owr_m1_config',$c);")
  state=json.loads(php("require '/var/www/html/wp-load.php';echo json_encode(['config'=>get_option('owr_m1_config'),'baseline'=>get_option('owr_setup_baseline')]);").stdout)
  assert state['config']['protect'] and state['baseline']['manifest']
  php("require '/var/www/html/wp-load.php';wp_set_current_user(1);wp_insert_post(['post_title'=>'Save settings <b>Original</b>','post_content'=>'Generated language test','post_status'=>'publish']);")
  html=php("require '/var/www/html/wp-load.php';require_once ABSPATH.'wp-admin/includes/template.php';wp_set_current_user(1);add_filter('pre_determine_locale',static fn()=> 'ja');(new Owr\\M1\\Plugin())->page();").stdout.decode()
  assert 'Save settings' in html and '&lt;b&gt;Original&lt;/b&gt;' in html,'User title must remain original and escaped'
  print('PASS fresh ZIP installation, initial capture and protected saving via CLI',flush=True)
  if acf:
   shutil.copyfile(acf,lab/'acf.zip')
   print(wp(web,'plugin','install','/lab/acf.zip','--activate'),flush=True)
   assert 'false'==wp(web,'eval',"echo json_encode(Owr\\M1\\SetupReadiness::acfReady((new Owr\\M1\\Plugin())->config()));").strip()
   wp(web,'eval',"wp_set_current_user(1);acf_import_field_group(['key'=>'group_readiness','title'=>'Readiness fixture','location'=>[[['param'=>'post_type','operator'=>'==','value'=>'post']]],'fields'=>[['key'=>'field_readiness','name'=>'sub-title','label'=>'Fixture','type'=>'text']]]);$id=wp_insert_post(['post_title'=>'ACF readiness fixture','post_status'=>'publish']);update_field('field_readiness','a:0:{}',$id);$p=new Owr\\M1\\Plugin();$point=(new Owr\\M1\\SiteSnapshot($p->store()))->capture(true,[]);$c=$p->config();update_option('owr_setup_baseline',Owr\\M1\\SetupReadiness::baselineRecord($c,$point['manifest']));Owr\\M1\\SetupReadiness::requireStart($c);echo 'READY';")
   assert 'true'==wp(web,'eval',"echo json_encode(Owr\\M1\\SetupReadiness::acfReady((new Owr\\M1\\Plugin())->config()));").strip()
   for locale,message in [('ja','現在のACF無料版を含む初期保存を確認済み'),('en_US','Initial save includes this ACF free version')]:
    rendered=wp(web,'eval',"add_filter('pre_determine_locale',static fn()=> '"+locale+"');Owr\\M1\\SetupReadiness::render((new Owr\\M1\\Plugin())->config());")
    assert message in rendered
   print('PASS real ACF free: old capture unconfirmed, new captured version ready, Japanese/English display',flush=True)
  update,udb,uphp=start('upgrade')
  print(wp(update,'plugin','install','/lab/previous.zip','--activate'),flush=True)
  assert wp(update,'plugin','get','ozeki-resilience','--field=version').strip()=='0.3.2'
  wp(update,'eval',"wp_set_current_user(1);wp_mkdir_p(wp_upload_dir()['basedir']);update_option('owr_m1_config',['bucket'=>'m1-generated','region'=>'ap-northeast-1','prefix'=>'upgrade/','retention_days'=>0,'protect'=>false]);wp_insert_post(['post_title'=>'Before upgrade','post_content'=>'Preserved original content','post_status'=>'publish']);$p=new Owr\\M1\\Plugin();$point=(new Owr\\M1\\SiteSnapshot($p->store()))->capture(true,[]);update_option('owr_site_initial',$point);$c=$p->config();$c['protect']=true;update_option('owr_m1_config',$c);wp_insert_post(['post_title'=>'Tracked before upgrade','post_content'=>'Tracked original','post_status'=>'publish']);update_option('owr_site_restore_result',['through'=>7,'fixture'=>'preserve']);update_option('owr_m1_pending',['id'=>'generated-pending','payload'=>'preserve']);update_option('owr_m1_comment_pending',[['id'=>'generated-related']]);")
  snapshot="global $wpdb;$keys=['owr_m1_config','owr_m1_pending','owr_m1_comment_pending','owr_site_restore_result','owr_site_initial'];$a=[];foreach($keys as $k)$a[$k]=get_option($k);$a['posts']=$wpdb->get_results(\"SELECT ID,post_title,post_content,post_status,post_type FROM {$wpdb->posts} ORDER BY ID\",ARRAY_A);$a['history']=(new Owr\\M1\\Plugin())->store()->history();echo json_encode($a);"
  before=json.loads(wp(update,'eval',snapshot));assert before['history']
  print(wp(update,'plugin','install','/lab/candidate.zip','--force','--activate'),flush=True)
  assert before==json.loads(wp(update,'eval',snapshot)), 'Update changed settings/history/pending/posts/results'
  assert json.loads(wp(update,'eval',hashcode))==expected
  # Pending records above are deliberately synthetic sentinels, not replayable operations.
  # Remove only these test fixtures after proving preservation, then check ordinary protected editing.
  wp(update,'eval',"delete_option('owr_m1_pending');delete_option('owr_m1_comment_pending');wp_set_current_user(1);wp_insert_post(['post_title'=>'Tracked after upgrade','post_content'=>'New protected content','post_status'=>'publish']);")
  after=json.loads(wp(update,'eval',snapshot));assert len(after['history'])>len(before['history'])
  assert after['owr_m1_config']==before['owr_m1_config'] and after['owr_m1_config']['protect']
  print('PASS active 0.3.2 rc.1 → 0.3.3 ZIP update preserves state and continues protected saving',flush=True)
  print(wp(web,'plugin','install','/lab/plugin-check.zip','--activate'),flush=True)
  check_version=wp(web,'plugin','get','plugin-check','--field=version').strip()
  check=run('docker','exec',web,'php','/lab/wp','plugin','check','ozeki-resilience','--require=/var/www/html/wp-content/plugins/plugin-check/cli.php','--format=json','--allow-root',check=False)
  raw=check.stdout.decode();(out/'plugin-check.txt').write_text(raw+check.stderr.decode())
  import re,collections
  rows=[]
  for file,data in re.findall(r'FILE: ([^\n]+)\n(\[[^\n]*\])',raw):
   for row in json.loads(data):row['file']=file;rows.append(row)
  if not rows:raise RuntimeError('Plugin Check output was not recognized: '+raw[:2000]+check.stderr.decode()[:500])
  (out/'plugin-check.json').write_text(json.dumps(rows,indent=2))
  counts=collections.Counter(x['type'] for x in rows);print('Plugin Check '+check_version+': '+str(counts),flush=True)
  result={'state':'PASS' if not counts['ERROR'] else 'CHECK_FAILED','scope':'Isolated WordPress / MariaDB / local S3 simulation; no live AWS','wordpress':wp(web,'core','version').strip(),'php':run('docker','exec',web,'php','-r','echo PHP_VERSION;').stdout.decode(),'plugin_check_version':check_version,'plugin_check_errors':counts['ERROR'],'plugin_check_warnings':counts['WARNING'],'installed_files':len(expected),'zip_sha256':__import__('hashlib').sha256(candidate.read_bytes()).hexdigest(),'checks':['Fresh install from candidate ZIP with all installed file hashes matching','CLI initial capture, readiness gate and enabled protection; not a browser test','Japanese rendering with untranslated escaped user content','Active replacement from submitted 0.3.2 rc.1 ZIP preserves config, posts, confirmed history, synthetic body/related pending records and recovery result','Legacy enabled protection continues saving after update without a new setup','Updated installed file hashes match candidate ZIP'],'acf_free_readiness_checked':bool(acf),'submitted':False}
  (out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
  assert not counts['ERROR'],'Plugin Check errors require review'

 finally:
  for kind,name in reversed(created):run('docker','rm','-f','-v',name,check=False) if kind=='container' else run('docker','network','rm',name,check=False)
if __name__=='__main__':
 import sys
 main(*(Path(x).resolve() for x in sys.argv[1:]))
