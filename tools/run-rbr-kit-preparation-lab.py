from pathlib import Path
import subprocess,json,time,secrets,shutil,os,hashlib
import argparse,zipfile,ipaddress
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'lab/rbr-protected-save'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vendor-cache',required=True,type=Path);p.add_argument('--plugin-zip',required=True,type=Path);p.add_argument('--saved-receipt',required=True,type=Path);p.add_argument('--profile',required=True,type=Path);p.add_argument('--q-sha256',required=True);p.add_argument('--keep-local-demo',action='store_true');p.add_argument('--demo-port',type=int,default=18714);args=p.parse_args()
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

 if len(args.q_sha256)!=64 or any(c not in '0123456789abcdef' for c in args.q_sha256):raise ValueError('Q digest required')
 # Generated UI fixture imports the actual previous experimental editor receipt; source site is not changed.
 receipt=json.loads(args.saved_receipt.read_text())
 if 'body' in receipt:receipt=json.loads(receipt['body'])
 if 'data' in receipt:receipt=receipt['data']
 (kit/'saved-history.json').write_text(json.dumps({'sequence':receipt['sequence'],'generations':[{'operation':'fixture-saved-editor','sequence':receipt['sequence'],'state':'applied','generation':receipt['generation'],'expected_ref':receipt['expected_ref'],'q_sha256':args.q_sha256}]}))
 for n in ['RbrReconstructionConsole','RbrKitPreparation']:shutil.copy2(ROOT/'src'/(n+'.php'),kit/'src'/(n+'.php'))
 shutil.copy2(ROOT/'assets/rbr-kit-preparation.js',kit/'assets/rbr-kit-preparation.js')
 inbox=lab/'preparation-inbox';inbox.mkdir();inbox.chmod(0o777)
 operator=b/'operator';operator.mkdir();(operator/'state').mkdir();shutil.copy2(args.profile,operator/'profile.json')
 conf={'schema':'owr-kit-preparation-config-v1','profile':str(operator/'profile.json'),'state':str(operator/'state'),'report':str(kit/'preparation-report.json'),'inbox':str(inbox)}
 (operator/'config.json').write_text(json.dumps(conf))
 import importlib.util
 spec=importlib.util.spec_from_file_location('preparation',ROOT/'tools/rbr-kit-preparation-worker.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
 prep.report(conf,(operator/'profile.json').read_bytes())
 (kit/'preparation-boot.php').write_text("<?php require_once '/kit/src/RbrReconstructionConsole.php';require_once '/kit/src/RbrKitPreparation.php';Owr\\RbrKitPreparation::boot(fn()=>new class{function generationHistory(){return json_decode(file_get_contents('/kit/saved-history.json'),true);}},json_decode(file_get_contents('/lab/config.json'),true)['ids'],'/kit/preparation-report.json','/lab/preparation-inbox');")
 run('docker','exec',web,'cp','/kit/preparation-boot.php','/var/www/html/wp-content/mu-plugins/zz-preparation.php')
 browser=name+'-browser';run('docker','run','-d','--name',browser,'--network','container:'+db,'--memory','2g','--shm-size','1g','--env','SE_NODE_HOST=127.0.0.1','--env-file',str(env),'-v',str(kit)+':/kit:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(browser)
 browsercode=(SRC/'editor-browser.py').read_text();browsercode=browsercode[:browsercode.index('try:\n a=fresh()')]
 browsercode+="""
phase=os.environ['PREPARATION_PHASE']
try:
 d=fresh();login(d);d.get(root+'/wp-admin/tools.php?page=owr-kit-preparation')
 end=time.monotonic()+40
 wanted={'request':'承認待ちキットを準備','resume':'失敗・明示的に再開できます','done':'保存完了・独立署名承認待ち'}[phase]
 while wanted not in d.find_element(By.ID,'owr-kit-status').text:
  if time.monotonic()>end:raise RuntimeError('Missing state '+wanted)
  time.sleep(.25)
 if phase!='done':
  d.find_element(By.CSS_SELECTOR,'#owr-kit-status button').click()
  end=time.monotonic()+15
  while '要求受付済み' not in d.find_element(By.ID,'owr-kit-status').text:
   if time.monotonic()>end:raise RuntimeError('Request not accepted')
   time.sleep(.2)
 else:
  if d.find_element(By.CSS_SELECTOR,'#owr-kit-status button').get_attribute('disabled') is None:raise RuntimeError('Completed job still enabled')
 d.save_screenshot('/lab/preparation-'+phase+'.png');print('PASS browser '+phase)
finally:
 for d in drivers:d.quit()
"""
 (kit/'preparation-browser.py').write_text(browsercode)
 def browse(phase):
  q=run('docker','exec','--env','PREPARATION_PHASE='+phase,browser,'python3','/kit/preparation-browser.py',timeout=180);print(q.stdout.decode(),flush=True)
 browse('request');check('one browser request recorded',len(list(inbox.glob('*.json')))==1)
 def fail(*a):raise RuntimeError('Generated pre-network failure')
 prep.cycle(conf,fail);check('controlled failure displayed',json.loads((kit/'preparation-report.json').read_text())['items'][0]['state']=='failed')
 browse('resume');check('explicit resume recorded',len(list(inbox.glob('*.json')))==2)
 # Real unchanged CLI, same frozen receipt/profile, dedicated new work and S3 prefix.
 q=run('python3',str(ROOT/'tools/rbr-kit-preparation-worker.py'),'--config',str(operator/'config.json'),'--allow-disposable-lab','--once',timeout=1500)
 (operator/'worker.log').write_bytes(q.stdout+q.stderr)
 report=json.loads((kit/'preparation-report.json').read_text());check('real CLI prepared exact generation awaiting approval',report['items'][0]['state']=='stored_awaiting_independent_approval' and report['items'][0]['generation_sha256']==receipt['generation']['sha256'])
 browse('done')
 endpoint='/index.php?rest_route=/owr-rbr/v1/kit-preparation'
 check('subscriber denied',api(None,sub,path=endpoint,method='GET')['status']==403)
 check('anonymous denied',api(None,path=endpoint,method='GET')['status'] in [401,403])
 check('generation page contents unchanged',state()==initial)
 result={'passed':True,'checks':checks,'report':report,'scope':'Generated saved-history fixture imported from prior real experimental S3 editor receipt; browser to unchanged real generation-kit CLI; no signing/reconstruction/publication'}
 (b/'result.json').write_text(json.dumps(result,indent=2))
finally:
 for n in reversed(created):run('docker','rm','-f',n,check=False)
 if (b/'result.json').exists():
  result=json.loads((b/'result.json').read_text());result['containers_removed']=True;(b/'result.json').write_text(json.dumps(result,indent=2))
