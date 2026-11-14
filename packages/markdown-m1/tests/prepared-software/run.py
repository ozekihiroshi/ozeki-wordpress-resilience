import subprocess,time,json,zipfile,hashlib,os,shutil
from pathlib import Path
b=Path(__file__).resolve().parent
tag='owr-noinit-'+str(int(time.time())); made=[];sites={};e=b/'results';e.mkdir(exist_ok=True)
lab=b/tag;lab.mkdir();(lab/'objects').mkdir();(lab/'control.json').write_text('{}');os.chmod(lab,0o777);os.chmod(lab/'objects',0o777)
live=None
def run(*a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError(str(a[:5])+p.stderr[-1800:]+p.stdout[-1800:])
 return p.stdout
def d(*a):return run('docker',*a)
def wp(s,*a):return d('exec',sites[s],'php','/tmp/wp.phar','--allow-root',*a)
def cli(s,mode,*a):
 raw=d('exec',sites[s],'php','/evidence/fixture.php',mode,*a);v=json.loads(raw);(e/(s+'-'+mode+'-'+str(time.time_ns())+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2));return v
def fingerprint():return live.fingerprint() if live else {str(p.relative_to(lab/'objects')):hashlib.sha256(p.read_bytes()).hexdigest()for p in (lab/'objects').rglob('*')if p.is_file()}
allowed={'version','db_version','block','show_excerpt','show_reg','show_login','autoex','mod_reg','notify','warnings','attrib','user_pages','shortcodes'}-{'version','db_version'}
def preserved(s,state):
 old=json.loads((lab/(s+'-prepared.json')).read_text())['settings']['wpmembers_settings'];new=state['settings']['wpmembers_settings']
 assert {k:v for k,v in old.items()if k not in allowed}=={k:v for k,v in new.items()if k not in allowed},'Prepared runtime changed'
def equivalent(a,z):
 assert not a['queue'],a
 assert a['member']==z['member'],('member',a['member'],z['member'])
 for key in ['wpmembers_fields','wpmembers_dialogs','wpmembers_tos']:assert a['settings'][key]==z['settings'][key],key
 for k in allowed:assert a['settings']['wpmembers_settings'].get(k)==z['settings']['wpmembers_settings'].get(k),k
 expected=json.loads(json.dumps(a['pages'])); expected['sample-page']['body']=expected['sample-page']['body'].replace(a['home']+'/',z['home']+'/'); assert expected==z['pages'],'pages/restriction'
 assert not z['pending'] and not z['queue'] and not z['error'],z
def http(s,edit=''):
 st=cli(s,'state');p=st['pages'];raw=d('exec',sites[s],'php','/evidence/http.php','http://'+sites[s],edit,str(p['trial-private']['id']),str(p['trial-login']['id']),str(p['trial-profile']['id']));v=json.loads(raw);(e/(s+'-http-'+str(time.time_ns())+'.json')).write_text(json.dumps(v));return v
def integration(s,mode,*args):
 raw=d('exec',sites[s],'php','/evidence/integrations.php',mode,*args);v=json.loads(raw);(e/(s+'-integration-'+mode+'-'+str(time.time_ns())+'.json')).write_text(json.dumps(v));return v
report={'scope':'Isolated WP-Members no-initialization feasibility experiment, not product release','storage':'file-backed SDK transport; no AWS access'}
try:
 if os.environ.get('OWR_LIVE_S3')=='1':
  from live import Live
  live=Live(lab);report['storage']='Real S3 via host-only scoped SDK transport';report['s3']=live.scope
 net=tag+'-net';d('network','create','--internal',net);made.append(('network',net))
 db=tag+'-db';vol=db+'-volume';d('volume','create',vol);made.append(('volume',vol));d('run','-d','--name',db,'--memory','512m','--cpus','0.5','--network',net,'-v',vol+':/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:11.8');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(['docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 for s in ['source','target','third']:
  web=tag+'-'+s;sites[s]=web;vol=web+'-volume';d('volume','create',vol);made.append(('volume',vol))
  d('run','-d','--name',web,'--memory','512m','--cpus','0.5','--network',net,'-v',vol+':/var/www/html','-v',str(lab)+':/lab','-e','TRIAL_SIDE='+s,'-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+s+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);define('WP_DEBUG',true);define('WP_DEBUG_LOG',true);define('WP_DEBUG_DISPLAY',false);",'wordpress:php8.3-apache');made.append(('container',web))
  for _ in range(60):
   if subprocess.run(['docker','exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
   time.sleep(1)
  d('cp',str(b/'wordpress-7.1.4.tar.gz'),web+':/tmp/core.tar.gz');d('exec',web,'tar','xzf','/tmp/core.tar.gz','--strip-components=1','-C','/var/www/html')
  d('cp',str(b/'wp.phar'),web+':/tmp/wp.phar');d('exec',web,'mkdir','-p','/evidence','/tmp/recovery-work','/var/www/html/wp-content/mu-plugins')
  for f in ['fixture.php','http.php','candidate.zip','wp-members.zip','product-src.tar','contact-form-7.zip','flamingo.zip','tablepress.zip','advanced-custom-fields.zip','ozeki-markdown-documents.zip']:d('cp',str(b/f),web+':/evidence/'+f)
  d('cp',str(b/'transport.php'),web+':/var/www/html/wp-content/mu-plugins/trial.php')
  wp(s,'core','install','--url=http://'+web,'--title=No initialization trial','--admin_user=operator','--admin_password=Trial-operator-ONLY-581!','--admin_email=operator@example.invalid','--skip-email')
  wp(s,'plugin','install','/evidence/wp-members.zip','--activate');wp(s,'plugin','install','/evidence/candidate.zip','--activate')
  for plugin in ['contact-form-7','flamingo','tablepress','advanced-custom-fields','ozeki-markdown-documents']:wp(s,'plugin','install','/evidence/'+plugin+'.zip','--activate')
  d('exec',web,'tar','xf','/evidence/product-src.tar','-C','/var/www/html/wp-content/plugins/ozeki-resilience')
  d('cp',str(b/'integrations.php'),web+':/evidence/integrations.php')
  # Normal activation/setup first; the test guard is installed afterwards.
  cli(s,'prepare')
  vendor=d('exec',web,'cat','/var/www/html/wp-content/plugins/wp-members/includes/install.php')
  assert 'function wpmem_install_settings() {'in vendor
  vendor=vendor.replace('function wpmem_install_settings() {',"function wpmem_install_settings() { throw new \\RuntimeException('Forbidden initialization after preparation');",1)
  (b/('install-'+s+'.php')).write_text(vendor);d('cp',str(b/('install-'+s+'.php')),web+':/var/www/html/wp-content/plugins/wp-members/includes/install.php')

  d('exec',web,'chown','-R','www-data:www-data','/var/www/html');print('Prepared '+s,flush=True)
 report['versions']={'wordpress':wp('source','core','version').strip(),'php':d('exec',sites['source'],'php','-r','echo PHP_VERSION;'),'wp_members':wp('source','plugin','get','wp-members','--field=version').strip()}
 integration('source','seed');cli('source','seed');cli('source','baseline','generation1');http('source','Kyoto');integration('source','edit','two');ia=integration('source','state');cli('source','edit-definition');a=cli('source','state');assert a['member']['city']=='Kyoto';assert not a['queue']
 before=fingerprint();n=cli('target','negative','generation1');assert n['rejected']and n['state_unchanged'];assert before==fingerprint();report['missing_preparation']=n
 cli('target','restore','generation1');assert before==fingerprint();z=cli('target','state');equivalent(a,z);preserved('target',z);assert ia==integration('target','state'),'First integration mismatch';report['first_recovery']=http('target');print('First recovery and HTTP use passed',flush=True)
 cli('target','baseline','generation2');http('target','Osaka');integration('target','edit','three');ia=integration('target','state');a=cli('target','state');assert a['member']['city']=='Osaka';preserved('target',a)
 before=fingerprint();cli('third','restore','generation2');assert before==fingerprint();z=cli('third','state');equivalent(a,z);preserved('third',z);assert ia==integration('third','state'),'Second integration mismatch';report['integrations_roundtrip']=True;report['second_recovery']=http('third');print('Second recovery and HTTP use passed',flush=True)
 cli('target','delete-definition');a=cli('target','state');before=fingerprint();cli('third','restore','generation2');assert before==fingerprint();z=cli('third','state');assert a['settings']['wpmembers_fields']==z['settings']['wpmembers_fields'];preserved('third',z);assert not any(f['2']=='trial_select' if isinstance(f,dict)else f[2]=='trial_select' for f in z['settings']['wpmembers_fields']);report['definition_deletion']=True
 report['prepared_settings_preserved']=True;report['initialization_guard_never_triggered']=True;report['object_count']=len(fingerprint());report['pass']=True
except Exception as ex:
 report['pass']=False;report['failure']=str(ex);raise
finally:
 if live:
  try:(e/'s3-final-versions.json').write_text(json.dumps(live.fingerprint(),indent=2))
  except Exception as ex:report['pass']=False;report['final_inventory_error']=type(ex).__name__
  finally:live.stop()
 for s,web in sites.items():
  for name in ['debug.log']:
   p=subprocess.run(['docker','exec',web,'cat','/var/www/html/wp-content/'+name],capture_output=True,text=True)
   if p.returncode==0:(e/(s+'-'+name)).write_text(p.stdout)
 (e/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(e/'resources.json').write_text(json.dumps({'sites':sites,'made':made,'lab':str(lab)}))
 for kind,name in reversed(made):subprocess.run(['docker',kind,'rm','-f',name]if kind=='container'else ['docker',kind,'rm',name],capture_output=True)
 print(json.dumps(report,ensure_ascii=False),flush=True)
