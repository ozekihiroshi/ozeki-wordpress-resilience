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
 raw=d('exec',sites[side],'php','/evidence/fixture.php',mode,*args);v=json.loads(raw);(e/(side+'-'+mode+('-'+'-'.join(args)if args else '').replace('/','_')+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2));assert 'operation_failed' not in v,v;return v
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
 db=tag+'-db';dbvol=db+'-volume';d('volume','create',dbvol);made.append(('volume',dbvol));d('run','-d','--name',db,'--network',net,'-v',dbvol+':/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:11.8');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(['docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 plugins=['wp-members']
 for side in ['source','clean','third']:
  web=tag+'-'+side;sites[side]=web;volume=web+'-volume';d('volume','create',volume);made.append(('volume',volume));d('run','-d','--name',web,'--network',net,'-v',volume+':/var/www/html','-v',str(lab)+':/lab','-e','TRIAL_SIDE='+side,'-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+side+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
  for _ in range(60):
   if subprocess.run(['docker','exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
   time.sleep(1)
  d('cp',str(b/'wp.phar'),web+':/tmp/wp.phar');d('exec',web,'mkdir','-p','/evidence','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'transport.php'),web+':/var/www/html/wp-content/mu-plugins/trial.php');d('cp',str(b/'fixture.php'),web+':/evidence/fixture.php')
  wp(side,'core','install','--url=http://'+web,'--title=Coexistence fixture','--admin_user=operator','--admin_password=trial-only-password','--admin_email=operator@example.invalid','--skip-email')
  for slug in plugins+['candidate']:
   d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip','--activate')
  if False:
   for slug in ['download-monitor','ozeki-database-backup-for-s3']:
    d('cp',str(b/(slug+'.zip')),web+':/evidence/'+slug+'.zip');wp(side,'plugin','install','/evidence/'+slug+'.zip',*(['--activate']if side=='mixed'else []))
  d('cp',str(b/'src')+'/.',sites[side]+':/var/www/html/wp-content/plugins/ozeki-resilience/src/');print('Created '+side,flush=True)
 (b/'resources.json').write_text(json.dumps({'sites':sites,'created':made,'lab':str(lab)}))
 report={}
 def observe(side,case):
  state=cli(side,'state',case);v=state['ids'];base='http://localhost';page=base+'/?page_id='+str(v['post']);needle='BOUNDARY-'+case
  anon=d('exec',sites[side],'curl','-fsSL',page)
  auth=json.loads(d('exec',sites[side],'php','/evidence/fixture.php','auth',case))
  member=d('exec',sites[side],'curl','-fsSL','-H','Cookie: '+auth['name']+'='+auth['value'],page)
  status=d('exec',sites[side],'curl','-s','-o','/dev/null','-w','%{http_code}',base+'/wp-content/uploads/'+v['rel'])
  return dict(state,anonymous_body_visible=needle in anon,member_body_visible=needle in member,image_http=status)
 for case in ['A','B','C','D']:
  cli('source','seed',case);initial=cli('source','baseline',case);cli('source','change',case);source=observe('source',case);before=fp();first=cli('clean','restore',case);target=observe('clean',case);assert before==fp()
  comparison=cli('source','comparison',case)
  cli('clean','baseline',case,'second');resave=cli('clean','resave',case);resaved=observe('clean',case);before=fp();second=cli('third','restore',case,'second');third=observe('third',case);assert before==fp()
  report[case]={'initial':initial,'source':source,'first_recovery':target,'fresh_baseline_comparison':comparison,'after_resave':resaved,'second_recovery':third,'recovery_objects_unchanged':True,'first_application_report':first['application_report'],'second_application_report':second['application_report']}
  (e/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('Case '+case+' completed',flush=True)
finally:
 for web in sites.values():(e/(web+'-docker.log')).write_text(run('docker','logs',web,check=False))
