"""Generated-only lab kit storage. Reuses scoped role signing and S3Adapter; no IAM mutations."""
import argparse, datetime as dt, gzip, hashlib, importlib.util, json, re, shlex, subprocess, sys
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('Optimized Python unsupported')
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
transport=load('rbr_s3_transport',Path(__file__).with_name('queue-s3-adapter.py'))
COORDINATOR_KEY=r'sites/isolated-queue-lab/sets/AWS-c057202610220001/coordinator/[a-z0-9-]+/(?:operations/[A-Za-z0-9_-]+\.json|commits/[0-9]{12}\.json|originals/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/(?:source|copies/[A-Za-z0-9_-]+))'

def authorize(actor,retention_days=35,**request):
 if retention_days not in (35,36):raise ValueError("Unsupported lab retention")
 script=Path(__file__).with_name('lab-s3-request.py').read_text()
 if retention_days==36:
  if script.count('days=35,minutes=10')!=1:raise ValueError('Unrecognized retention signer template')
  script=script.replace('days=35,minutes=10','days=36,minutes=10')
 old='(database.sql|wordpress-files.tar.gz|queue.sqlite|recovery-set.json|recovery-set.sig|permission-probe.txt)'
 assert old in script
 script=script.replace(old,r'(rbr-[a-f0-9]{64}\.blob|rbr-root\.json)').replace("assert q['method'] in ('PUT','GET','DELETE')", "assert q['method'] in ('PUT','GET')")
 if request.get('method')=='GET' and re.fullmatch(COORDINATOR_KEY,request.get('key','')):
  line=next(x for x in script.splitlines() if x.startswith("assert re.fullmatch(r'sites/"))
  script=script.replace(line,"assert q['method']=='GET' and re.fullmatch("+repr(COORDINATOR_KEY)+",q['key'])")
 host={'writer':'community','reader':'dm'}[actor]
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3 -c '+shlex.quote(script)],input=json.dumps({'actor':actor,**request}).encode(),capture_output=True,timeout=120)
 if p.returncode:raise RuntimeError('Existing lab authorization failed; sensitive details suppressed')
 return json.loads(p.stdout)
transport.authorize=authorize
CHUNK=8*1024*1024

def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
class Store:
 def __init__(self,work):
  self.work=work
  if work.exists():
   ops=json.loads((work/'operations.json').read_text());self.adapter=transport.S3Adapter.__new__(transport.S3Adapter);self.adapter.work=work;self.adapter.client=transport.urllib.request.build_opener(transport.NoRedirect);self.adapter.operations=ops;self.adapter.request_count=0
  else:
   self.adapter=transport.S3Adapter(work)
   self.adapter.save()  # Persist an empty journal before the first request can fail.
 def put(self,raw,key):
  for o in self.adapter.operations:
   if o['method']=='PUT' and o['key']==key:
    if o['state']!='acknowledged':raise RuntimeError('Uncertain PUT: reconcile manually, no resend')
    if o['sha256']!=sha(raw) or o['bytes']!=len(raw):raise ValueError('Conflicting immutable key')
    version=o['version_id'];break
  else:version=self.adapter.put(transport.BUCKET,key,raw)
  return {'locator':{'kind':'s3','bucket':transport.BUCKET,'region':transport.REGION,'key':key,'version_id':version},'size_bytes':len(raw),'sha256':sha(raw)}
 def get(self,ref):
  if not (re.fullmatch(r'sites/isolated-queue-lab/sets/AWS-[a-f0-9]{16}/(rbr-[a-f0-9]{64}\.blob|rbr-root\.json)',ref['locator']['key']) or re.fullmatch(COORDINATOR_KEY,ref['locator']['key'])):raise ValueError('Not a lab RBR key')
  if not 0<ref['size_bytes']<=CHUNK:raise ValueError('Object bound')
  result=self.adapter.get(dict(ref['locator'],size_bytes=ref['size_bytes']))
  if result['version_id']!=ref['locator']['version_id'] or sha(result['body'])!=ref['sha256']:raise ValueError('Fixed object mismatch')
  modified=dt.datetime.fromisoformat(result['last_modified']);until=dt.datetime.fromisoformat(result['retain_until'].replace('Z','+00:00'))
  if result['mode']!='GOVERNANCE' or until<modified+dt.timedelta(days=35) or until<=dt.datetime.now(dt.timezone.utc):raise ValueError('Retention evidence insufficient')
  return result['body']

def publish(source,work):
 work.mkdir(mode=0o700,exist_ok=True)
 plan=json.loads((source/'inputs/plan.json').read_text())
 if plan['site_id']!='corporate-test':raise ValueError('Generated corporate fixture only')
 pre=transport.preflight();(work/'preflight.json').write_bytes(canonical(pre))
 state=work/'publication.json'
 if not state.exists():
  import secrets
  state.write_bytes(canonical({'prefix':'sites/isolated-queue-lab/sets/AWS-'+secrets.token_hex(8)+'/','source_definition_sha256':sha((source/'inputs/definition.json').read_bytes())}))
 record=json.loads(state.read_text());prefix=record['prefix']
 if record['source_definition_sha256']!=sha((source/'inputs/definition.json').read_bytes()):raise ValueError('Different source on resume')
 store=Store(work/'writer');cache=source/'inputs/cache';memo={};overrides={}
 def upload(raw):return store.put(raw,prefix+'rbr-'+sha(raw)+'.blob')
 def read(ref):
  raw=(cache/(ref['sha256']+'.blob')).read_bytes()
  if len(raw)!=ref['size_bytes'] or sha(raw)!=ref['sha256']:raise ValueError('Source cache mismatch')
  return raw
 d=json.loads((source/'inputs/definition.json').read_bytes());env=json.loads(read(d['environment_ref']))
 for kind in ['wordpress','database']:
  ref=env['packages'][kind]['artifact_ref'];descriptor=json.loads(read(ref));image=descriptor['image_id']
  if not re.fullmatch('sha256:[a-f0-9]{64}',image):raise ValueError('Unfixed image')
  archive=work/(kind+'.tar.gz')
  if not archive.exists():
   temp=work/(kind+'.partial')
   if temp.exists():raise RuntimeError('Incomplete local image archive; inspect before retry')
   with temp.open('xb') as target:
    with gzip.GzipFile(filename='',mode='wb',fileobj=target,mtime=0,compresslevel=1) as zipped:
     proc=subprocess.Popen(['docker','image','save',image],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
     while True:
      block=proc.stdout.read(CHUNK)
      if not block:break
      zipped.write(block)
     if proc.wait()!=0:raise RuntimeError('Image archive failed')
   temp.rename(archive)
  chunks=[];h=hashlib.sha256();total=0
  with archive.open('rb') as f:
   while True:
    block=f.read(CHUNK)
    if not block:break
    h.update(block);total+=len(block);chunks.append(upload(block))
  overrides[ref['sha256']]=canonical({'kind':'docker-save-gzip-chunks-v1','image_id':image,'archive_sha256':h.hexdigest(),'archive_size_bytes':total,'chunks':chunks})
 def rewrite(value):
  if isinstance(value,dict):
   if set(['locator','sha256','size_bytes'])<=set(value):return visit(value)
   return {k:rewrite(v) for k,v in value.items()}
  if isinstance(value,list):return [rewrite(v) for v in value]
  return value
 def visit(ref):
  digest=ref['sha256']
  if digest in memo:return memo[digest]
  if digest in overrides:raw=overrides[digest]
  else:
   raw=read(ref)
   try:value=json.loads(raw)
   except (ValueError,UnicodeError):value=None
   if value is not None:
    new=rewrite(value)
    if new!=value:raw=canonical(new)
  result=upload(raw);memo[digest]=result;return result
 fixed_d=upload(canonical(rewrite(d)))
 names=['src/RbrGenerationCoordinator.php','src/RbrReconstructionPlanner.php','tools/rbr-wordpress-apply.php','tools/rbr-wordpress-observe.php','tools/rbr-compare.py','tools/rbr-reconstruct-lab.py','tools/rbr-plan.php','tools/rbr-planner-build.php']
 code=[{'path':n,'ref':upload((ROOT/n).read_bytes())} for n in names]
 root={'schema':'owr-rbr-s3-kit-v1','definition_ref':fixed_d,'code':code,'public_activation':False,'scope':'generated-corporate-site'}
 receipt=store.put(canonical(root),prefix+'rbr-root.json');(work/'root-receipt.json').write_bytes(canonical(receipt))
 print(json.dumps({'state':'stored','root_receipt':str(work/'root-receipt.json'),'objects':len([x for x in store.adapter.operations if x['method']=='PUT']),'bytes':sum(x['bytes'] for x in store.adapter.operations if x['method']=='PUT')}),flush=True)

def bound_expected(binding,generation_ref,manifest,read):
 if set(binding)!={'schema','generation','intent','expected'} or binding['schema']!='owr-rbr-bound-expected-v1':raise ValueError('Bound Q schema')
 if binding['generation']!=generation_ref:raise ValueError('Q belongs to another generation')
 intent=binding['intent'];q=binding['expected']
 if sha(canonical(intent))!=manifest['intent_sha256'] or intent.get('expected_sha256')!=sha(canonical(q)):raise ValueError('Q intent digest mismatch')
 for field in ['site_id','operation_id','sequence','parent','deadline']:
  if intent.get(field)!=manifest.get(field):raise ValueError('Q intent generation mismatch')
 # Compare request material hashes, never derive Q from reconstructed output.
 for asset in intent['assets']:
  if asset['kind']=='page':
   page=q['pages'][asset['id']]
   if page['role']!=asset['role'] or sha(canonical({k:page[k] for k in ['title','slug','paragraphs']}))!=asset['sha256']:raise ValueError('Q differs from save request')
  elif asset['kind']=='image':
   if q['images'][asset['id']]['sha256']!=asset['sha256']:raise ValueError('Q image differs from intent')
  elif asset['kind']=='relations':
   selected=next(x for x in manifest['assets'] if x['id']==asset['id'])
   if json.loads(read(selected['storage']))['edges']!=q['relations']:raise ValueError('Q relations differ from intent')
 return q

def verify_bound_root(root,read):
 if root.get('schema')=='owr-rbr-s3-kit-v2':
  if 'expected_binding_ref' not in root:raise ValueError('Bound Q required by kit v2')
 elif 'expected_binding_ref' in root:raise ValueError('Bound Q requires kit v2')
 else:return
 d=json.loads(read(root['definition_ref']));generation=d['assets_ref'];manifest=json.loads(read(generation))
 q=bound_expected(json.loads(read(root['expected_binding_ref'])),generation,manifest,read)
 if canonical(q)!=canonical(json.loads(read(d['expected_ref']))) or q['scope']!=d['required_scope']:raise ValueError('Definition Q binding differs')

def dependency_items(value):
 # Full snapshot parents are provenance only. Do not exempt fields in other schemas.
 fields={'schema','site_id','sequence','operation_id','intent_sha256','parent','protect_until','deadline','assets'}
 if value.get('schema')=='owr-rbr-generation-v1':
  if set(value)!=fields:raise ValueError('Invalid generation fields')
  return [(key,item) for key,item in value.items() if key!='parent']
 if value.get('schema')=='owr-rbr-bound-expected-v1':
  if set(value)!={'schema','generation','intent','expected'}:raise ValueError('Invalid bound Q fields')
  return [(key,value[key]) for key in ['generation','expected']]
 return list(value.items())

def fetch(receipt,out,before_execute=None):
 out.mkdir(mode=0o700);store=Store(out/'reader');root_raw=store.get(json.loads(receipt.read_bytes()));root=json.loads(root_raw);(out/'root-manifest.json').write_bytes(root_raw)
 if root['schema'] not in ['owr-rbr-s3-kit-v1','owr-rbr-s3-kit-v2'] or root['public_activation'] is not False:raise ValueError('Unsupported kit')
 bundle=out/'bundle';bundle.mkdir();cache=bundle/'cache';cache.mkdir();code=out/'kit';code.mkdir();seen={};archives=[]
 def visit(ref):
  k=ref['sha256']
  if k in seen:
   if seen[k]!=ref:raise ValueError('Ambiguous reference')
   return (cache/(k+'.blob')).read_bytes()
  if len(seen)>500:raise ValueError('Closure bound')
  seen[k]=ref;raw=store.get(ref);(cache/(k+'.blob')).write_bytes(raw)
  try:value=json.loads(raw)
  except (ValueError,UnicodeError):return raw
  def walk(v):
   if isinstance(v,dict):
    if set(['locator','sha256','size_bytes'])<=set(v):visit(v)
    else:
     for _,x in dependency_items(v):walk(x)
   elif isinstance(v,list):
    for x in v:walk(x)
  walk(value)
  if isinstance(value,dict) and value.get('kind')=='docker-save-gzip-chunks-v1':archives.append(value)
  return raw
 (bundle/'definition.json').write_bytes(visit(root['definition_ref']))
 verify_bound_root(root,visit)
 allowed={'src/RbrGenerationCoordinator.php','src/RbrReconstructionPlanner.php','tools/rbr-wordpress-apply.php','tools/rbr-wordpress-observe.php','tools/rbr-compare.py','tools/rbr-reconstruct-lab.py','tools/rbr-plan.php','tools/rbr-planner-build.php'}
 if {x['path'] for x in root['code']}!=allowed or len(root['code'])!=len(allowed):raise ValueError('Unexpected execution code')
 for item in root['code']:
  path=code/item['path'];path.parent.mkdir(exist_ok=True);path.write_bytes(visit(item['ref']))
 # Recheck independent authority immediately before downloaded code execution.
 if before_execute is not None:before_execute()
 # P is regenerated from the fetched D, not the sender's local P.
 subprocess.run(['php',str(code/'tools/rbr-plan.php'),'--definition='+str(bundle/'definition.json'),'--objects='+str(cache),'--output='+str(bundle/'plan.json')],check=True)
 imagefiles=[]
 for index,descriptor in enumerate(archives):
  target=out/('image-'+str(index)+'.tar.gz');h=hashlib.sha256();total=0
  with target.open('xb') as f:
   for ref in descriptor['chunks']:
    block=(cache/(ref['sha256']+'.blob')).read_bytes();h.update(block);total+=len(block);f.write(block)
  if h.hexdigest()!=descriptor['archive_sha256'] or total!=descriptor['archive_size_bytes']:raise ValueError('Archive mismatch')
  imagefiles.append({'path':str(target),'image_id':descriptor['image_id'],'sha256':h.hexdigest(),'size_bytes':total})
 (out/'images.json').write_bytes(canonical(imagefiles))
 print(json.dumps({'state':'fetched-and-verified','objects':len(seen),'archives':len(imagefiles),'root_sha256':sha(canonical(root))}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['publish','fetch']);p.add_argument('--source',type=Path);p.add_argument('--work',type=Path,required=True);p.add_argument('--receipt',type=Path);p.add_argument('--execute-generated-lab',action='store_true');a=p.parse_args()
 if not a.execute_generated_lab:p.error('Explicit lab opt-in required')
 if a.mode=='publish':publish(a.source.resolve(),a.work.resolve())
 else:p.error('Unsigned fetch entry disabled; use rbr-approved-kit.py with independent approval')
