from pathlib import Path
import subprocess,json,time,secrets,shutil,os,hashlib
import argparse
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'lab/rbr-protected-save'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vendor-cache',type=Path);args=p.parse_args()
b=args.output.resolve();b.mkdir(mode=0o700,exist_ok=False);lab=b/'lab';lab.mkdir(mode=0o777);os.chmod(lab,0o777)
for n in ['s3','s3/objects','scratch','originals']:(lab/n).mkdir(mode=0o777);os.chmod(lab/n,0o777)
kit=b/'kit';kit.mkdir();(kit/'src').mkdir();(kit/'tools').mkdir();(kit/'tests/support').mkdir(parents=True)
for n in ['VersionedAssetStore','RbrObjectStore','RbrGenerationCoordinator','RbrWordPressSave','RbrWordPressSaveApi']:shutil.copy2(ROOT/'src'/(n+'.php'),kit/'src'/(n+'.php'))
for n in ['aws-autoload.php','rbr-create-fixture.php']:shutil.copy2(ROOT/'tools'/n,kit/'tools'/n)
shutil.copytree(args.vendor_cache or ROOT/'vendor',kit/'vendor');shutil.copy2(ROOT/'tests/support/RbrS3Double.php',kit/'tests/support/RbrS3Double.php')
for n in ['testboot.php','wp-test.php']:(kit/n).write_text((SRC/n).read_text(encoding='utf-8-sig'))
images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
name='owr-save-api-'+secrets.token_hex(4);db=name+'-db';web=name+'-web';created=[];checks=[]
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
 password=secrets.token_hex(20);env=b/'env';env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("DISABLE_WP_CRON",true);define("WP_HTTP_BLOCK_EXTERNAL",true);define("DISALLOW_FILE_MODS",true);\n');env.chmod(0o600)
 for image in [images['OWR_DB_IMAGE'],images['OWR_WP_IMAGE']]:run('docker','image','inspect',image)
 run('docker','run','-d','--name',db,'--network','none','--memory','512m','--env-file',str(env),images['OWR_DB_IMAGE']);created.append(db)
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
 check('network isolated and no published ports',all(not x['HostConfig']['PortBindings'] for x in json.loads(run('docker','inspect',db,web).stdout)))
 a=payload('first-save',0,'First');check('anonymous request denied',api(a)['status'] in [401,403]);check('subscriber denied',api(a,sub)['status']==403)
 check('core REST protected page write denied',api({'content':'bypass'},admin,path='/index.php?rest_route=/wp/v2/pages/'+str(config['ids']['company']))['status']==409)
 check('unrelated page remains editable',api({'content':'Unrelated changed'},admin,path='/index.php?rest_route=/wp/v2/pages/'+str(config['unrelated']))['status']==200)
 control(fail='/commits/');check('S3 failure returns unresolved',api(a,admin)['status']==409);check('S3 failure leaves all public page rows unchanged',state()['pages']==initial['pages']);check('new operation cannot pass pending save',api(payload('wrong-next',0,'Wrong'),admin)['status']==409)
 control();response=api(a,admin);check('real HTTP API resumes failed operation',response['status']==200);s=state();check('generation one applied once',s['state']['sequence']==1 and len(commits())==1)
 check('public HTTP shows S3-confirmed text', 'First company line one' in api(None,path='/?page_id='+str(config['ids']['company']),method='GET')['body'])
 originalcommit=commits()[0]['version'];check('duplicate API request idempotent',api(a,admin)['status']==200 and state()['pages']==s['pages'] and commits()[0]['version']==originalcommit)
 control(stop='after_s3');two=payload('second-save',1,'Second');p=write('second.json',two);q=php('dispatch',p,check=False);check('process interrupted after S3 commit',q.returncode==93 and len(commits())==2);check('after-S3 stop keeps public rows unchanged',state()['pages']==s['pages']);twoVersion=next(x['version'] for x in commits() if x['key'].endswith('000000000002.json'))
 control();check('new process resumes exact committed version',api(two,admin)['status']==200 and next(x['version'] for x in commits() if x['key'].endswith('000000000002.json'))==twoVersion and len(commits())==2)
 s=state();three=payload('third-save',2,'Third');control(stop='after_page_company');q=php('dispatch',write('third.json',three),check=False);check('process stopped inside DB transaction',q.returncode==93);check('DB disconnect rolls back all page writes',state()['pages']==s['pages'] and state()['state']['sequence']==2)
 control();check('transaction stop resumes same generation',api(three,admin)['status']==200 and state()['state']['sequence']==3 and len(commits())==3)
 four=payload('fourth-save',3,'Fourth');control(pause='after_s3');p=write('fourth.json',four)
 proc=subprocess.Popen(['docker','exec','-u','www-data',web,'php','/kit/wp-test.php','dispatch',p],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 end=time.monotonic()+15
 while not (lab/'paused').exists():
  if proc.poll() is not None or time.monotonic()>end:raise RuntimeError('race pause failed')
  time.sleep(.05)
 check('competing operation rejected while committed apply pending',api(payload('competing-save',3,'Wrong'),admin)['status']==409);(lab/'release').touch();out,err=proc.communicate(timeout=30);check('winning operation completes',proc.returncode==0 and json.loads(out)['status']==200);control();s=state()
 check('stale expected generation rejected',api(payload('stale-save',3,'Old'),admin)['status']==409)
 check('old completed replay cannot overwrite newer state',api(a,admin)['status']==200 and state()['pages']==s['pages'] and state()['state']['sequence']==4)
 bad=dict(four);bad['pages']=payload('unused-op',3,'Changed')['pages'];check('same operation changed payload rejected',api(bad,admin)['status']==409)
 check('invalid page scope rejected',api({'operation_id':'invalid-save','expected_sequence':4,'pages':{}},admin)['status']==400)
 # Request-derived expected state is frozen before commit and bound to its exact generation.
 import base64,importlib.util
 spec=importlib.util.spec_from_file_location('qkit',ROOT/'tools/rbr-s3-kit.py');qkit=importlib.util.module_from_spec(spec);spec.loader.exec_module(qkit)
 def readref(ref):
  record=json.loads((lab/'s3/objects'/(hashlib.sha256(ref['locator']['key'].encode()).hexdigest()+'.json')).read_bytes())
  raw=base64.b64decode(record['raw']);assert record['version']==ref['locator']['version_id'] and hashlib.sha256(raw).hexdigest()==ref['sha256'];return raw
 fifth=payload('q-binding-save',4,'Expected from request');prior=state();control(fail='originals/request-expectation/q-binding-save/source')
 check('Q storage failure does not project committed content',api(fifth,admin)['status']==409 and state()['pages']==prior['pages'] and len(commits())==5)
 frozen=state()['state']['operations']['q-binding-save']['expected'];fifth_version=next(x['version'] for x in commits() if x['key'].endswith('000000000005.json'))
 check('Q frozen before generation and no reconstruction used',frozen['pages']['company']['paragraphs']==fifth['pages']['company']['paragraphs'] and frozen['actual_status']=='draft')
 control();reply=api(fifth,admin);receipt=json.loads(reply['body'])
 check('same request resumes Q storage and projection',reply['status']==200 and len(commits())==5 and next(x['version'] for x in commits() if x['key'].endswith('000000000005.json'))==fifth_version)
 bound=json.loads(readref(receipt['expected_ref']));manifest=json.loads(readref(receipt['generation']));expected=qkit.bound_expected(bound,receipt['generation'],manifest,readref)
 check('fixed Q intent and generation binding verified',expected==frozen and bound['intent']['expected_sha256']==hashlib.sha256(qkit.canonical(expected)).hexdigest())
 check('Q covers selected generation retention',receipt['expected_ref']['retain_until']>=manifest['protect_until'])
 check('completed replay preserves Q version',json.loads(api(fifth,admin)['body'])['expected_ref']==receipt['expected_ref'])
 old=json.loads(api(a,admin)['body']);check('older operation returns older Q without overwrite',old['expected_ref']!=receipt['expected_ref'] and state()['state']['sequence']==5)
 (b/'request-q.json').write_text(json.dumps({'request':fifth,'receipt':receipt,'binding':bound,'manifest':manifest,'expected':expected},ensure_ascii=False,indent=2))
 # Deliberate out-of-band drift in this disposable test only.
 run('docker','exec','-u','www-data',web,'php','-r','require "/var/www/html/wp-load.php";global $wpdb;$wpdb->update($wpdb->posts,["post_content"=>"outside change"],["ID"=>'+str(config['ids']['company'])+']);')
 before=state();check('out-of-band change detected before S3 write',api(payload('drift-save',5,'Drift'),admin)['status']==409 and len(commits())==5 and state()['pages']==before['pages'])
 (b/'result.json').write_text(json.dumps({'passed':True,'checks':checks,'scope':'real WordPress HTTP REST + MariaDB; existing filesystem S3 protocol double; no live S3 claim','commits':len(commits()),'containers_removed':False},indent=2))
finally:
 for n in reversed(created):run('docker','rm','-f',n,check=False)
 if (b/'result.json').exists():
  result=json.loads((b/'result.json').read_text());result['containers_removed']=True;(b/'result.json').write_text(json.dumps(result,indent=2))
print('SAVE API ACCEPTANCE PASS',flush=True)
