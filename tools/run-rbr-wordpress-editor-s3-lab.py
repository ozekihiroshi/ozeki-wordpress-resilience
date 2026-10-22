from pathlib import Path
import subprocess,json,time,secrets,shutil,os,hashlib
import argparse,re,importlib.util,threading,socketserver
ROOT=Path(__file__).resolve().parents[1];SRC=ROOT/'lab/rbr-protected-save'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--vendor-cache',required=True,type=Path);p.add_argument('--case',required=True);args=p.parse_args()
if not re.fullmatch(r'api-[a-z0-9-]{1,30}',args.case):raise ValueError('Dedicated api case required')
b=args.output.resolve();b.mkdir(mode=0o700,exist_ok=False);lab=b/'lab';lab.mkdir(mode=0o777);os.chmod(lab,0o777)
for n in ['s3','s3/objects','scratch','originals']:(lab/n).mkdir(mode=0o777);os.chmod(lab/n,0o777)
kit=b/'kit';kit.mkdir();(kit/'src').mkdir();(kit/'tools').mkdir();(kit/'tests/support').mkdir(parents=True)
for n in ['VersionedAssetStore','RbrObjectStore','RbrGenerationCoordinator','RbrWordPressSave','RbrWordPressSaveApi','RbrWordPressEditor']:shutil.copy2(ROOT/'src'/(n+'.php'),kit/'src'/(n+'.php'))
for n in ['aws-autoload.php','rbr-create-fixture.php']:shutil.copy2(ROOT/'tools'/n,kit/'tools'/n)
shutil.copytree(args.vendor_cache,kit/'vendor');shutil.copy2(ROOT/'tests/support/RbrS3Double.php',kit/'tests/support/RbrS3Double.php')
for n in ['testboot.php','wp-test.php']:(kit/n).write_text((SRC/n).read_text(encoding='utf-8-sig').replace('CURLOPT_TIMEOUT=>30','CURLOPT_TIMEOUT=>1100'))
(kit/'assets').mkdir();shutil.copy2(ROOT/'assets/rbr-editor.js',kit/'assets/rbr-editor.js')
shutil.copy2(SRC/'editor-browser.py',kit/'editor-browser.py')
base=(ROOT/'lab/notification-admin/preflight-browser.py').read_text();(kit/'webdriver-base.py').write_text(base[:base.index('mode=')].replace("return self.call('GET','/attribute/'+name)","return self.call('GET',('/property/' if name=='value' else '/attribute/')+name)").replace("'browserName':'chrome',","'browserName':'chrome','unhandledPromptBehavior':'accept',"))
boot=kit/'testboot.php';t=boot.read_text().replace("'RbrWordPressSaveApi']","'RbrWordPressSaveApi','RbrWordPressEditor']");t+="\nOwr\\RbrWordPressEditor::boot(json_decode(file_get_contents('/lab/config.json'),true)['ids']);\n";boot.write_text(t)
images=dict(line.split('=',1) for line in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in line)
name='owr-save-api-'+secrets.token_hex(4);db=name+'-db';web=name+'-web';created=[];checks=[]
def run(*a,check=True,timeout=1200):
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
def records():
 return [json.loads(x) for x in (b/'transport.jsonl').read_text().splitlines()] if (b/'transport.jsonl').exists() else []
def commits():
 return [{'key':x['key'],'version':x['result']['VersionId']} for x in records() if x['phase']=='acked' and x['operation']=='PutObject' and '/commits/' in x['key'] and x['success']]
spec=importlib.util.spec_from_file_location('broker',ROOT/'tools/rbr-coordinator-transport.py');broker=importlib.util.module_from_spec(spec);spec.loader.exec_module(broker)
prefix=broker.PREFIX+'coordinator/'+args.case+'/'
pre=broker.metadata('reader','list',prefix)
(b/'preflight.json').write_text(json.dumps(pre,indent=2))
if not pre['success'] or pre['response'].get('Contents'):raise RuntimeError('New exact prefix must be confirmed empty')
class Handler(socketserver.StreamRequestHandler):
 def handle(self):
  q=json.loads(self.rfile.readline(12*1024*1024));op=q['operation'];a=q['args'];key=a.get('Key','')
  entry={'operation':op,'key':key,'version':a.get('VersionId'),'time':time.time()}
  def log(value):
   with (b/'transport.jsonl').open('a') as f:f.write(json.dumps(dict(entry,**value))+'\n');f.flush();os.fsync(f.fileno())
  log({'phase':'started'})
  try:
   if key and not key.startswith(prefix):raise broker.Failure(403)
   ctl=json.loads((lab/'control.json').read_text()) if (lab/'control.json').exists() else {}
   if op=='PutObject' and ctl.get('fail') and ctl['fail'] in key:
    log({'phase':'injected_before_request','status':503});raise broker.Failure(503)
   result=broker.serve(q);reply={'success':True,'result':result}
  except broker.Failure as e:reply={'success':False,'status':e.status}
  except Exception:reply={'success':False,'status':502}
  log(dict(phase='acked',**{k:v for k,v in reply.items() if k!='result'},result={k:v for k,v in reply.get('result',{}).items() if k!='body64'}))
  (lab/'live-commits.json').write_text(json.dumps(commits()))
  self.wfile.write((json.dumps(reply)+'\n').encode())
server=socketserver.UnixStreamServer(str(lab/'broker.sock'),Handler);os.chmod(lab/'broker.sock',0o666)
threading.Thread(target=server.serve_forever,daemon=True).start()
(lab/'live-commits.json').write_text('[]')
(lab/'live.json').write_text(json.dumps({'prefix':prefix}))
shutil.copy2(SRC/'live-request.php',kit/'live-request.php')
boot=(kit/'testboot.php').read_text()
lo=boot.index(" $server=new RbrS3Double");hi=boot.index(' $fault=',lo)
boot=boot[:lo]+" require_once '/kit/live-request.php';\n $control=is_file('/lab/control.json')?json_decode(file_get_contents('/lab/control.json'),true):[];\n $request=owr_live_request(...);\n $store=new Owr\\RbrObjectStore($request,'ceri-link-resilience-lock-lab-121426368082','ap-northeast-1','121426368082',json_decode(file_get_contents('/lab/live.json'),true)['prefix'],'/lab/scratch',fn()=>time(),'corporate-test',true);\n"+boot[hi:]
boot=boot.replace('microtime(true)+15','microtime(true)+120')
(kit/'testboot.php').write_text(boot)

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
 browser=name+'-browser'
 run('docker','image','inspect','selenium/standalone-chrome:latest')
 run('docker','run','-d','--name',browser,'--network','container:'+db,'--memory','2g','--shm-size','1g','--env','SE_NODE_HOST=127.0.0.1','--env-file',str(env),'-v',str(kit)+':/kit:ro','-v',str(lab)+':/lab','--entrypoint','sleep','selenium/standalone-chrome:latest','infinity');created.append(browser)
 q=run('docker','exec',browser,'python3','/kit/editor-browser.py',check=False,timeout=3600)
 (b/'browser.log').write_bytes(q.stdout+q.stderr);print(q.stdout.decode(),flush=True)
 if q.returncode:raise RuntimeError(q.stderr.decode()[-2500:])
 result=json.loads((lab/'browser-result.json').read_text());result['containers_removed']=False;result['scope']='Real Chromium editor + WordPress HTTP + MariaDB + scoped real S3; injected pre-commit failure';result['prefix']=prefix;result['versions']=commits()
 (b/'result.json').write_text(json.dumps(result,indent=2))

finally:
 server.shutdown();server.server_close()
 for n in reversed(created):run('docker','rm','-f',n,check=False)
 if (b/'result.json').exists():
  result=json.loads((b/'result.json').read_text());result['containers_removed']=True;(b/'result.json').write_text(json.dumps(result,indent=2))
print('LIVE EDITOR ACCEPTANCE PASS',flush=True)
