import subprocess,time,json,hashlib,zipfile,sys
from pathlib import Path
case=sys.argv[1]; stage=sys.argv[2]; b=Path('/tmp/owr-navigation-fix-20261124')/stage/case; b.mkdir(parents=True,exist_ok=True); lab=Path('/tmp/owr-navigation-fix-20261124'); import shutil; shutil.copy(lab/(case+'.php'),b/'probe.php'); shutil.copy(lab/'transport.php',b/'transport.php');old=Path('/tmp/owr-rc21-roundtrip-20261124');made=[];sites={};result={}
docker=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];name='owr-hypothesis-'+str(int(time.time()))
def d(*a):
 p=subprocess.run(docker+list(a),text=True,capture_output=True,timeout=180)
 if p.returncode:raise RuntimeError(p.stderr[-2000:]+p.stdout[-1500:])
 return p.stdout
def wp(s,*a):return d('exec',sites[s],'php','/tmp/wp.phar','--allow-root',*a)
def cli(s,m,*a):
 raw=d('exec',sites[s],'php','/lab/probe.php',m,*a)
 try:v=json.loads(raw)
 except ValueError:
  (b/(s+'-'+m+'-raw.txt')).write_text(raw);v={'ok':False,'non_json':True,'raw_file':s+'-'+m+'-raw.txt'}
 print(s,m,json.dumps(v),flush=True);return v
def comparable(v):
 r={k:x for k,x in v.items() if k not in ['actual_author_id','history_count','pending','queue']}
 if case=='lifecycle':
  r['pages']=[p for p in r['pages'] if int(p['ID'])>=4];r['comments']=[c for c in r['comments'] if int(c['comment_post_ID'])>=4];r['anonymous_conditions']={k:x for k,x in r['anonymous_conditions'].items() if int(k)>=4}
 return r
def control(f=''):(b/'control.json').write_text(json.dumps({'fail':f}))
try:
 assert hashlib.sha256((old/'candidate.zip').read_bytes()).hexdigest()=='ec0b5cbedd7855054d87ef5656ffcfbde25335c25d4e939b0291d73acf0874de'
 (b/'objects').mkdir(exist_ok=False);control()
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net))
 db=name+'-db';d('run','-d','--name',db,'--memory','512m','--cpus','0.5','--network',net,'--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(docker+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 for s in ['source','destination']:
  web=name+'-'+s;sites[s]=web;vol=web+'-volume';d('volume','create',vol);made.append(('volume',vol))
  d('run','-d','--name',web,'--memory','512m','--cpus','0.5','--network',net,'-v',vol+':/var/www/html','-v',str(b)+':/lab','-e','AWS_EC2_METADATA_DISABLED=true','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+s+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
  for _ in range(60):
   if subprocess.run(docker+['exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
   time.sleep(1)
  d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins','/tmp/recovery-work');d('cp',str(b/'transport.php'),web+':/var/www/html/wp-content/mu-plugins/isolation.php');wp(s,'core','install','--url=http://'+web,'--title=Synthetic isolation','--admin_user=operator','--admin_password=isolated-test-only-password','--admin_email=operator@example.invalid','--skip-email');d('cp',str(old/'candidate.zip'),web+':/tmp/candidate.zip');wp(s,'plugin','install','/tmp/candidate.zip','--activate');
  if stage!='before':
   d('cp',str(lab/'overlay/src')+'/.',web+':/var/www/html/wp-content/plugins/ozeki-resilience/src/');d('cp',str(lab/'overlay/ozeki-wordpress-resilience.php'),web+':/var/www/html/wp-content/plugins/ozeki-resilience/ozeki-wordpress-resilience.php')
  print('Prepared '+s,flush=True)
 cli('source','prepare');result['initial']=cli('source','state');result['initial_restore']=cli('destination','restore');result['initial_destination']=cli('destination','state')
 originals={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (b/'objects').rglob('*') if p.is_file()}
 for mode in ['unstick','stick','save','refresh-baseline']:
  operation=cli('source',mode);assert operation['ok'],operation
  source=cli('source','state');restore=cli('destination','restore');dest=cli('destination','state')
  result[mode]={'operation':operation,'source':source,'restore':restore,'destination':dest,'equal':source['display']==dest['display']}
  (b/'result.json').write_text(json.dumps(result,indent=2))
  assert restore.get('success') and result[mode]['equal'], 'Recovered state mismatch: '+mode
 result['cycle_save']=cli('destination','cycle-save');assert result['cycle_save']['ok']
 result['cycle_source']=cli('destination','state')
 result['cycle_restore']=cli('source','cycle-restore');assert result['cycle_restore']['success']
 result['cycle_destination']=cli('source','state')
 result['cycle_equal']=result['cycle_source']['display']==result['cycle_destination']['display']
 assert result['cycle_equal'], 'Second recovery mismatch'
 if 'deleted_equal' in result: assert result['deleted_equal'], 'Menu deletion mismatch'
 result['originals_unchanged']=all(Path(p).exists() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in originals.items())
 result['storage']='Isolated file-backed SDK; no AWS access';(b/'result.json').write_text(json.dumps(result,indent=2));print('Results saved',flush=True)
finally:
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f']if kind=='container'else []),n)
  except Exception as e:print('Cleanup failed '+n+str(e),flush=True)
