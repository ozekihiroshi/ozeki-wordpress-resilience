import subprocess,os,time,json,zipfile,hashlib,tarfile,urllib.request
from pathlib import Path
b=Path(__file__).resolve().parent;tag='owr-coexist-'+str(int(time.time()));made=[];sites={};e=b/'results';e.mkdir(exist_ok=True)
def run(*args,check=True):
 p=subprocess.run(args,capture_output=True,text=True,timeout=240)
 if check and p.returncode:raise RuntimeError(str(args[:5])+p.stderr[-1600:]+p.stdout[-2400:])
 return p.stdout
def d(*args):return run('docker',*args)
def wp(side,*args):return d('exec',sites[side],'php','/tmp/wp.phar','--allow-root',*args)
def cli(side,mode,*args):
 raw=d('exec',sites[side],'php','/evidence/fixture.php',mode,*args);v=json.loads(raw);(e/(side+'-'+mode+('-'+'-'.join(args)if args else '').replace('/','_')+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2));return v
def fp():return {str(p.relative_to(lab/'objects')):hashlib.sha256(p.read_bytes()).hexdigest()for p in (lab/'objects').rglob('*')if p.is_file()}
def match(a,z):
 keys=['post','page','markdown','acf','receipt','form_title','table','member_first','member_auth','restriction','image']
 differences={k:[a.get(k),z.get(k)]for k in keys if a.get(k)!=z.get(k)}
 assert not differences,differences
 assert not z['pending']and not z['related_pending']
 return True
try:
 lab=b/('lab-'+tag);lab.mkdir(exist_ok=False);os.chmod(lab,0o777);(lab/'control.json').write_text('{}');(lab/'objects').mkdir(exist_ok=True);os.chmod(lab/'objects',0o777)
 net=tag+'-net';d('network','create','--internal',net);made.append(('network',net))
 db=tag+'-db';d('run','-d','--name',db,'--network',net,'--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:11.8');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(['docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 plugins=['advanced-custom-fields','contact-form-7','flamingo','ozeki-markdown-documents','tablepress','wp-members']
 for side in ['source','clean','mixed','third']:
  web=tag+'-'+side;sites[side]=web;volume=web+'-volume';d('volume','create',volume);made.append(('volume',volume));d('run','-d','--name',web,'--network',net,'-v',volume+':/var/www/html','-v',str(lab)+':/lab','-e','TRIAL_SIDE='+side,'-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+side+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
  for _ in range(60):
   if subprocess.run(['docker','exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
   time.sleep(1)
  d('cp',str(b/'wp.phar'),web+':/tmp/wp.phar');d('exec',web,'mkdir','-p','/evidence','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'transport.php'),web+':/var/www/html/wp-content/mu-plugins/trial.php');d('cp',str(b/'fixture.php'),web+':/evidence/fixture.php')
  wp(side,'core','install','--url=http://'+web,'--title=Coexistence fixture','--admin_user=operator','--admin_password=trial-only-password','--admin_email=operator@example.invalid','--skip-email')
  for slug in plugins+['candidate']:
   d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip','--activate')
  if side in ['source','mixed']:
   for slug in ['download-monitor','ozeki-database-backup-for-s3']:
    d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip',*(['--activate']if side=='mixed'else []))
  print('Created '+side,flush=True)
 (b/'resources.json').write_text(json.dumps({'sites':sites,'created':made,'lab':str(lab)}))
 cli('source','seed');wp('source','plugin','activate','download-monitor','ozeki-database-backup-for-s3');cli('source','unsupported');legacy=cli('source','baseline');(lab/'legacy-baseline.json').write_bytes((lab/'source-baseline.json').read_bytes());legacy_objects=fp();print('Legacy original preserved',flush=True)
 for side in sites:
  d('cp',str(b/'src')+'/.',sites[side]+':/var/www/html/wp-content/plugins/ozeki-resilience/src/')
 d('exec',sites['source'],'mkdir','-p','/var/www/html/wp-content/plugins/ozeki-resilience/tests')
 for test in ['file-scope.php','recovery-preparation.php']:
  d('cp',str(b/test),sites['source']+':/var/www/html/wp-content/plugins/ozeki-resilience/tests/'+test)
  print(d('exec',sites['source'],'php','/var/www/html/wp-content/plugins/ozeki-resilience/tests/'+test),flush=True)
 report={'legacy':legacy,'checks':{}}
 cli('source','edit','1');source=cli('source','state')
 for side in ['clean','mixed']:
  before=fp();restored=cli(side,'restore','source');after=cli(side,'state');assert before==fp();match(source,after)
  assert not after['private_file_exists'];assert any(x['item']=='uploads/dlm_uploads/coexist-private.pdf' for x in restored['application_report']['not_applied'])
  ids=json.loads((lab/'ids.json').read_text())
  for name,needle in [('formpage','name="your-message"'),('tablepage','Reading'),('private','MEMBER-ONLY-CONTENT')]:
   page=d('exec',sites[side],'curl','-fsSL','http://localhost/?page_id='+str(ids[name]));assert (needle in page)==(name!='private')
  code=d('exec',sites[side],'curl','-s','-o','/dev/null','-w','%{http_code}','http://localhost/wp-content/uploads/dlm_uploads/coexist-private.pdf');assert code in ['403','404']
  report['checks'][side]={'supported_match':True,'originals_unchanged':True,'private_http':code,'state':after};print(side+' legacy recovery PASS',flush=True)
 large=cli('source','large');assert large['captured'];report['large']=large;print('Unsupported large PDF no longer blocks PASS',flush=True)
 new=cli('source','baseline');assert 'uploads/dlm_uploads/coexist-private.pdf'not in new['files'];report['new_capture']=new
 cli('mixed','baseline','mixed/');cli('mixed','edit','2','mixed/');second=cli('mixed','state');before=fp();cli('third','restore','mixed');third=cli('third','state');assert before==fp();match(second,third);assert not third['private_file_exists'];report['second_recovery']=third
 final_objects=fp();assert all(final_objects.get(k)==v for k,v in legacy_objects.items());report['legacy_objects_unchanged']=True
 print('Use, resave, formal history and second recovery PASS',flush=True)
 d('cp',str(b/'extra.php'),sites['source']+':/evidence/extra.php');print(d('exec',sites['source'],'php','/evidence/extra.php'),flush=True)
 (e/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
finally:
 for web in sites.values():(e/(web+'-docker.log')).write_text(run('docker','logs',web,check=False))

