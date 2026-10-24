"""Test-only authentication transport: existing experimental EC2 roles, no credential export.
The shipped plugin uses the AWS SDK default credential provider directly, not this helper.
"""
import base64,hashlib,json,re,shlex,subprocess,threading,time,urllib.request,urllib.error
from pathlib import Path
BUCKET='ceri-link-resilience-lock-lab-121426368082'
ROOT=Path('/mnt/d/workspace/ozeki-wordpress-resilience')
class Live:
 def __init__(self,lab,prefix):
  assert re.fullmatch(r'sites/isolated-queue-lab/sets/AWS-c057202610220001/coordinator/m1-[a-f0-9]{12}/',prefix)
  self.lab=lab;self.prefix=prefix;self.stopped=False
  self.base=(ROOT/'tools/lab-s3-request.py').read_text()
  self.allowed=re.escape(prefix)+r'(originals/[a-f0-9-]+/[a-f0-9-]+/(source\.md|metadata\.json)|history/[0-9]{20}\.json)'
 def remote(self,actor,script,q):
  p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',{'writer':'community','reader':'dm'}[actor],'python3 -c '+shlex.quote(script)],input=json.dumps(dict(q,actor=actor)),capture_output=True,text=True,timeout=90)
  if p.returncode:raise RuntimeError('SSH authentication transport failed (no credential output)')
  return json.loads(p.stdout)
 def listing(self,prefix,token=None):
  assert prefix.startswith(self.prefix)
  args=['s3api','list-objects-v2','--bucket',BUCKET,'--expected-bucket-owner','121426368082','--prefix',prefix]
  if token:args+=['--continuation-token',token]
  script=self.base[:self.base.index("if q.get('operation')=='preflight':")]+"\nprint(json.dumps(aws("+repr(args)+")))\n"
  r=self.remote('reader',script,{})
  if not r['success']:raise RuntimeError('S3 list denied: '+r.get('error_code','unknown'))
  return r['response']
 def request(self,op,a):
  assert a['Bucket']==BUCKET and a['ExpectedBucketOwner']=='121426368082'
  if op=='ListObjectsV2':return self.listing(a['Prefix'],a.get('ContinuationToken'))
  key=a['Key'];assert re.fullmatch(self.allowed,key)
  method={'PutObject':'PUT','GetObject':'GET'}[op];actor='writer' if method=='PUT' else 'reader'
  s=self.base;line=next(x for x in s.splitlines() if x.startswith("assert re.fullmatch(r'sites/"));s=s.replace(line,'assert re.fullmatch('+repr(self.allowed)+",q['key'])")
  s=s.replace("else:assert isinstance(q.get('version'),str) and q['version'] not in ('','null')","else:assert 'version' not in q or q['version'] not in ('','null')")
  s=s.replace("if q['method'] in ('GET','DELETE'):params['versionId']=q['version']","if q.get('version'):params['versionId']=q['version']")
  s=s.replace("0<q['size']<1024**3","0<=q['size']<=5*1024**2+65536")
  s=s.replace("(now+datetime.timedelta(days=35,minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')","q['retain_until']")
  s=s.replace("if q['method']=='PUT':\n","if q['method']=='PUT':\n headers['content-type']=q['content_type']\n")
  q={'method':method,'key':key};body=None
  if method=='PUT':
   assert a['IfNoneMatch']=='*' and a['ObjectLockMode']=='GOVERNANCE' and a['ServerSideEncryption']=='AES256'
   body=base64.b64decode(a['body64']);q.update(size=len(body),sha256=hashlib.sha256(body).hexdigest(),md5=hashlib.md5(body).hexdigest(),retain_until=a['ObjectLockRetainUntilDate'],content_type=a['ContentType'])
  elif 'VersionId'in a:q['version']=a['VersionId']
  auth=self.remote(actor,s,q)
  try:
   with urllib.request.urlopen(urllib.request.Request(auth['url'],headers=auth['headers'],data=body,method=method),timeout=60) as r:
    result={'VersionId':r.headers.get('x-amz-version-id'),'ObjectLockMode':r.headers.get('x-amz-object-lock-mode'),'ObjectLockRetainUntilDate':r.headers.get('x-amz-object-lock-retain-until-date'),'ContentType':r.headers.get('Content-Type')}
    if method=='GET':result['body64']=base64.b64encode(r.read()).decode()
    return result
  except urllib.error.HTTPError as e:raise RuntimeError('S3 HTTP '+str(e.code)) from None
 def start(self):
  assert not self.listing(self.prefix).get('Contents'), 'Fresh experimental prefix must be unused'
  (self.lab/'live').write_text(self.prefix)
  self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
 def loop(self):
  done=set()
  while not self.stopped:
   for p in (self.lab/'ipc').glob('*.request'):
    if p.name in done:continue
    done.add(p.name);q=json.loads(p.read_text());event={'operation':q['operation'],'key':q['args'].get('Key'),'prefix':q['args'].get('Prefix')}
    try:r={'success':True,'result':self.request(q['operation'],q['args'])}
    except Exception as e:r={'success':False,'error':str(e)}
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(r));temp.rename(p.with_suffix('.response'))
    with (self.lab/'live-events.jsonl').open('a')as f:f.write(json.dumps(dict(event,success=r['success']))+'\n')
   time.sleep(.1)
