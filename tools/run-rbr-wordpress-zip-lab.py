from pathlib import Path
import subprocess,json,time,secrets,shutil,os,hashlib
import argparse,zipfile,ipaddress
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'lab/rbr-protected-save'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vendor-cache',required=True,type=Path);p.add_argument('--plugin-zip',required=True,type=Path);p.add_argument('--old-zip',required=True,type=Path);p.add_argument('--keep-local-demo',action='store_true');p.add_argument('--demo-port',type=int,default=18714);args=p.parse_args()
if not 1024<=args.demo_port<=65535:raise ValueError('Invalid demo port')
b=args.output.resolve();b.mkdir(mode=0o700,exist_ok=False);lab=b/'lab';lab.mkdir(mode=0o777);os.chmod(lab,0o777)
for n in ['s3','s3/objects','scratch','originals']:(lab/n).mkdir(mode=0o777);os.chmod(lab/n,0o777)
kit=b/'kit';kit.mkdir();(kit/'src').mkdir();(kit/'tools').mkdir();(kit/'tests/support').mkdir(parents=True)
for n in ['VersionedAssetStore','RbrObjectStore','RbrGenerationCoordinator','RbrWordPressSave','RbrWordPressSaveApi','RbrWordPressEditor']:shutil.copy2(ROOT/'src'/(n+'.php'),kit/'src'/(n+'.php'))
for n in ['aws-autoload.php','rbr-create-fixture.php']:shutil.copy2(ROOT/'tools'/n,kit/'tools'/n)
shutil.copytree(args.vendor_cache,kit/'vendor');shutil.copy2(ROOT/'tests/support/RbrS3Double.php',kit/'tests/support/RbrS3Double.php')
for n in ['testboot.php','wp-test.php']:(kit/n).write_text((SRC/n).read_text(encoding='utf-8-sig'))
(kit/'assets').mkdir();shutil.copy2(ROOT/'assets/rbr-editor.js',kit/'assets/rbr-editor.js')
shutil.copy2(SRC/'editor-browser.py',kit/'editor-browser.py')
base=(ROOT/'lab/notification-admin/preflight-browser.py').read_text();(kit/'webdriver-base.py').write_text(base[:base.index('mode=')].replace("return self.call('GET','/attribute/'+name)","return self.call('GET',('/property/' if name=='value' else '/attribute/')+name)").replace("'browserName':'chrome',","'browserName':'chrome','unhandledPromptBehavior':'accept',"))
boot=kit/'testboot.php';t=boot.read_text().replace("'RbrWordPressSaveApi']","'RbrWordPressSaveApi','RbrWordPressEditor']");t+="\nOwr\\RbrWordPressEditor::boot(json_decode(file_get_contents('/lab/config.json'),true)['ids']);\n";boot.write_text(t)
images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
name='owr-save-api-'+secrets.token_hex(4);db=name+'-db';web=name+'-web';created=[];checks=[];demo_ready=False;demo_network=None
def run(*a,check=True,timeout=120):
 p=subprocess.run(a,capture_output=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError(p.stderr.decode()[-1500:]+p.stdout.decode()[-1500:])
 return p

def php(*a,check=True):return run('docker','exec','-u','www-data',web,'php','/kit/wp-test.php',*a,check=check)
def jsonphp(*a):return json.loads(php(*a).stdout)
def write(name,value):
 p=lab/name;p.write_text(json.dumps(value));os.chmod(p,0o666);return '/lab/'+name

def state():return jsonphp('snapshot')
def control(**kw):write('control.json',kw)
def payload(op,seq,label):return {'operation_id':op,'expected_sequence':seq,'pages':{r:{'title':r+' '+label,'slug':r,'paragraphs':[label+' '+r+' line one','line two']} for r in ['company','services','contact']}}
def api(data,cred=None,path='/index.php?rest_route=/owr-rbr/v1/save',method='POST'):
 h=['Content-Type: application/json'];
 if cred:h+=['Cookie: '+cred['cookie'],'X-WP-Nonce: '+cred['nonce']]
 p=write('http-'+secrets.token_hex(4)+'.json',{'path':path,'method':method,'headers':h,'body':json.dumps(data) if data is not None else ''})
 return jsonphp('http',p)
def commits():return [json.loads(p.read_text()) for p in (lab/'s3/objects').glob('*.json') if '/commits/' in json.loads(p.read_text())['key']]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name);print('PASS '+name,flush=True)
try:
 password=secrets.token_hex(20);env=b/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("DISABLE_WP_CRON",true);define("WP_HTTP_BLOCK_EXTERNAL",true);define("FS_METHOD","direct");\n');env.chmod(0o600)
 for image in [images['OWR_DB_IMAGE'],images['OWR_WP_IMAGE']]:run('docker','image','inspect',image)
 dbnet=['--network','none']
 if args.keep_local_demo:
  used=[]
  ids=run('docker','network','ls','-q').stdout.decode().split()
  for net in json.loads(run('docker','network','inspect',*ids).stdout):
   used.extend(ipaddress.ip_network(c['Subnet']) for c in (net['IPAM']['Config'] or []) if c.get('Subnet'))
  used.extend(ipaddress.ip_network(x['dst'],strict=False) for x in json.loads(run('ip','-j','route').stdout) if x.get('dst') not in [None,'default'])
  subnet=next((ipaddress.ip_network('10.254.'+str(i)+'.0/28') for i in range(200,240) if not any(ipaddress.ip_network('10.254.'+str(i)+'.0/28').overlaps(n) for n in used if n.version==4)),None)
  if subnet is None:raise RuntimeError('No unused dedicated demo subnet')
  demo_network=name+'-net';run('docker','network','create','--internal','--subnet',str(subnet),demo_network);dbnet=['--network',demo_network]
 run('docker','run','-d','--name',db,*dbnet,'--memory','512m','--env-file',str(env),images['OWR_DB_IMAGE']);created.append(db)
 end=time.monotonic()+120
 while run('docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized',check=False).returncode:
  if time.monotonic()>end:raise RuntimeError('DB startup timeout')
  time.sleep(1)
 run('docker','run','-d','--name',web,'--network','container:'+db,'--memory','768m','--env-file',str(env),'-v',str(kit)+':/kit:ro','-v',str(lab)+':/lab',images['OWR_WP_IMAGE']);created.append(web)
 end=time.monotonic()+120
 while run('docker','exec',web,'test','-f','/var/www/html/wp-config.php',check=False).returncode:
  if time.monotonic()>end:raise RuntimeError('WP startup timeout')
  time.sleep(1)
 run('docker','exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins')
 run('docker','exec',web,'cp','/kit/testboot.php','/var/www/html/wp-content/mu-plugins/owr-save-lab.php')
 run('docker','exec','-u','www-data',web,'php','/kit/tools/rbr-create-fixture.php','--output=/lab/assets')
 php('setup');php('enroll');admin=jsonphp('credentials','labadmin');sub=jsonphp('credentials','labsubscriber');initial=state();config=json.loads((lab/'config.json').read_text())
 def wp(code):return run('docker','exec','-u','www-data',web,'php','-r','require "/var/www/html/wp-load.php";require_once ABSPATH."wp-admin/includes/plugin.php";'+code).stdout
 def install(path):
  run('docker','cp',str(path.resolve()),web+':/tmp/candidate.zip')
  wp('require_once ABSPATH."wp-admin/includes/file.php";require_once ABSPATH."wp-admin/includes/class-wp-upgrader.php";$u=new Plugin_Upgrader(new Automatic_Upgrader_Skin());$r=$u->install("/tmp/candidate.zip",["overwrite_package"=>true]);if(is_wp_error($r)||!$r)throw new Exception("ZIP install failed");')
 def active():return wp('echo is_plugin_active("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php")?"yes":"no";')==b'yes'
 def activate():wp('$r=activate_plugin("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");if(is_wp_error($r))throw new Exception($r->get_error_message());')
 install(args.plugin_zip);activate();check('fresh final plugin ZIP installs and activates',active())
 with zipfile.ZipFile(args.plugin_zip) as z:
  check('fresh installed files match final ZIP',all(run('docker','exec',web,'cat','/var/www/html/wp-content/plugins/'+n).stdout==z.read(n) for n in z.namelist()))
 check('network isolated; optional demo bound to loopback only',all(v['HostIp']=='127.0.0.1' for x in json.loads(run('docker','inspect',db,web).stdout) for values in (x['HostConfig']['PortBindings'] or {}).values() for v in values))
 control() # Pre-create shared test control as the host owner before the browser writes it.
 browser=name+'-browser'
 run('docker','image','inspect','selenium/standalone-chrome:latest')
 run('docker','run','-d','--name',browser,'--network','container:'+db,'--memory','2g','--shm-size','1g','--env','SE_NODE_HOST=127.0.0.1','--env-file',str(env),'-v',str(kit)+':/kit:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(browser)
 q=run('docker','exec',browser,'python3','/kit/editor-browser.py',check=False,timeout=600)
 (b/'browser.log').write_bytes(q.stdout+q.stderr);print(q.stdout.decode(),flush=True)
 if q.returncode:raise RuntimeError(q.stderr.decode()[-2500:])
 result=json.loads((lab/'browser-result.json').read_text());result['containers_removed']=False;result['scope']='Real Chromium editor + WordPress HTTP + MariaDB; persistent S3 double for controlled faults'
 # Existing administration candidate -> final ZIP, with active saved history and a pending operation.
 install(args.old_zip);activate()
 wp('update_option("owr_zip_test_settings",["enabled"=>false,"site"=>"generated-only"]);')
 pending=payload('zip-pending-save',5,'After ZIP update');control(stop='after_s3')
 q=php('dispatch',write('zip-pending.json',pending),check=False)
 check('pending committed save created before update',q.returncode==93 and len(commits())==6)
 before=state();frozen_q=before['state']['operations']['zip-pending-save']['expected'];settings=wp('global $wpdb;echo json_encode($wpdb->get_results("SELECT option_name,option_value FROM {$wpdb->options} WHERE option_name LIKE CONCAT(CHAR(111,119,114,95),CHAR(37)) OR option_name=CHAR(99,114,111,110) ORDER BY option_name",ARRAY_A));')
 def external():
  return json.loads(wp('$h=["config.json"=>hash_file("sha256","/lab/config.json")];foreach(["s3","originals","scratch"] as $dir){$it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator("/lab/".$dir,FilesystemIterator::SKIP_DOTS));foreach($it as $f){if($f->isFile()){$h[substr($f->getPathname(),5)]=hash_file("sha256",$f->getPathname());}}}ksort($h);echo json_encode($h);'))

 saved=external()
 install(args.plugin_zip)
 for action in ['deactivate','activate']:
  if action=='deactivate':wp('deactivate_plugins("ozeki-wordpress-resilience/ozeki-wordpress-resilience.php");')
  else:activate()
  check(action+' preserves pages, pending journal and completed history',state()==before)
 check('upgrade preserves settings and cron',settings==wp('global $wpdb;echo json_encode($wpdb->get_results("SELECT option_name,option_value FROM {$wpdb->options} WHERE option_name LIKE CONCAT(CHAR(111,119,114,95),CHAR(37)) OR option_name=CHAR(99,114,111,110) ORDER BY option_name",ARRAY_A));'))
 check('upgrade preserves external assets and configuration',saved==external())
 check('upgraded plugin remains active',active())
 with zipfile.ZipFile(args.plugin_zip) as z:
  check('upgraded files match final ZIP',all(run('docker','exec',web,'cat','/var/www/html/wp-content/plugins/'+n).stdout==z.read(n) for n in z.namelist()))
 # Redeploy the exact extracted final runtime while retaining all operator-owned state.
 for n in ['VersionedAssetStore','RbrObjectStore','RbrGenerationCoordinator','RbrWordPressSave','RbrWordPressSaveApi','RbrWordPressEditor']:shutil.copy2(ROOT/'src'/(n+'.php'),kit/'src'/(n+'.php'))
 shutil.copy2(ROOT/'assets/rbr-editor.js',kit/'assets/rbr-editor.js')
 check('kit redeployment preserves pending state',state()==before and external()==saved)
 version=next(x['version'] for x in commits() if x['key'].endswith('000000000006.json'));control();response=api(pending,admin)
 check('pending request resumes after ZIP update without new generation',response['status']==200 and len(commits())==6 and version in [x['version'] for x in commits()] and state()['state']['sequence']==6)
 check('pending Q preserved across update and bound after resume',state()['state']['operations']['zip-pending-save']['expected']==frozen_q and 'expected_ref' in json.loads(response['body']))
 result.update(lifecycle_checks=checks,external_files_preserved=len(saved),schema_migration_tested=False,plugin_sha256=hashlib.sha256(args.plugin_zip.read_bytes()).hexdigest(),old_plugin_sha256=hashlib.sha256(args.old_zip.read_bytes()).hexdigest())
 (b/'result.json').write_text(json.dumps(result,indent=2))

 if args.keep_local_demo:
  # Generated local demonstration only; login token is not shipped or published.
  token=secrets.token_hex(32);url='http://127.0.0.1:'+str(args.demo_port)
  wp('update_option("home",'+json.dumps(url)+');update_option("siteurl",'+json.dumps(url)+');')
  gate=kit/'demo-login.php';gate.write_text('<?php if(!defined("ABSPATH"))exit;add_action("init",function(){if(!isset($_GET["owr_demo"])||!hash_equals('+json.dumps(token)+',(string)$_GET["owr_demo"]))return;$u=get_user_by("login","labadmin");wp_set_current_user($u->ID);wp_set_auth_cookie($u->ID);wp_safe_redirect(admin_url("edit.php?post_type=page"));exit;});')
  run('docker','exec',web,'cp','/kit/demo-login.php','/var/www/html/wp-content/mu-plugins/demo-login.php')
  address=json.loads(run('docker','inspect',db).stdout)[0]['NetworkSettings']['Networks'][demo_network]['IPAddress']
  proxylog=(b/'demo-proxy.log').open('ab');proxy=subprocess.Popen(['python3',str(ROOT/'tools/rbr-local-demo-proxy.py'),'--upstream',address,'--port',str(args.demo_port)],stdout=proxylog,stderr=proxylog,start_new_session=True);time.sleep(1)
  if proxy.poll() is not None:raise RuntimeError('Demo loopback proxy failed')
  info={'proxy_pid':proxy.pid,'url':url+'/?owr_demo='+token,'pages_url':url+'/wp-admin/edit.php?post_type=page','web':web,'db':db,'network':demo_network,'storage':'persistent filesystem S3 protocol double; no AWS calls','generated_only':True}
  (b/'demo.json').write_text(json.dumps(info));(b/'demo.json').chmod(0o600);demo_ready=True
finally:
 for n in reversed(created):
  if demo_ready and n in [web,db]:continue
  run('docker','rm','-f',n,check=False)
 if demo_network and not demo_ready:run('docker','network','rm',demo_network,check=False)
 if (b/'result.json').exists():
  result=json.loads((b/'result.json').read_text());result['containers_removed']=not demo_ready;result['local_demo_retained']=demo_ready;(b/'result.json').write_text(json.dumps(result,indent=2))
print('EDITOR ACCEPTANCE PASS',flush=True)
