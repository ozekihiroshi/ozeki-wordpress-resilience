"""Dedicated experiment broker. Credentials remain on existing EC2 roles. JSON-lines IPC."""
import base64,datetime as dt,email.utils,hashlib,json,os,re,shlex,subprocess,sys,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREFIX='sites/isolated-queue-lab/sets/AWS-c057202610220001/'
BUCKET='ceri-link-resilience-lock-lab-121426368082'
KEY=PREFIX+r'coordinator/[a-z0-9-]+/(?:operations/[A-Za-z0-9_-]+\.json|commits/[0-9]{12}\.json|originals/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/(?:source|copies/[A-Za-z0-9_-]+))'
class Failure(Exception):
 def __init__(self,status):self.status=status
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):raise Failure(502)
client=urllib.request.build_opener(NoRedirect)
def remote(actor,script,q):
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',{'writer':'community','reader':'dm'}[actor],'python3 -c '+shlex.quote(script)],input=json.dumps(dict(q,actor=actor)),capture_output=True,text=True,timeout=120)
 if p.returncode:raise Failure(502)
 return json.loads(p.stdout)
def metadata(actor,op,key=None):
 s=(ROOT/'tools/lab-s3-request.py').read_text();s=s[:s.index("if q.get('operation')=='preflight':")]
 if op=='list':
  if not key.startswith(PREFIX):raise Failure(400)
  args=['s3api','list-objects-v2','--bucket',BUCKET,'--expected-bucket-owner','121426368082','--prefix',key,'--max-keys','1']
 else:args=['s3api',op,'--bucket',BUCKET,'--expected-bucket-owner','121426368082']
 return remote(actor,s+'\nprint(json.dumps(aws('+repr(args)+')))\n',{})
def authorize(actor,method,key,body=None,version=None,until=None):
 if not re.fullmatch(KEY,key) or method not in ('PUT','GET','HEAD'):raise Failure(400)
 if (method=='PUT')!=(actor=='writer'):raise Failure(400)
 s=(ROOT/'tools/lab-s3-request.py').read_text()
 line=next(x for x in s.splitlines() if x.startswith("assert re.fullmatch(r'sites/"))
 s=s.replace(line,'assert re.fullmatch('+repr(KEY)+",q['key'])")
 s=s.replace("assert q['method'] in ('PUT','GET','DELETE')","assert q['method'] in ('PUT','GET','HEAD')")
 s=s.replace("else:assert isinstance(q.get('version'),str) and q['version'] not in ('','null')","else:assert q['method']=='HEAD' or (isinstance(q.get('version'),str) and q['version'] not in ('','null'))")
 s=s.replace("if q['method'] in ('GET','DELETE'):params['versionId']=q['version']","if q.get('version'):params['versionId']=q['version']")
 s=s.replace("(now+datetime.timedelta(days=35,minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')","q['retain_until']")
 s=s.replace("if q['method']=='PUT':\n", "if q['method']=='PUT':\n assert now+datetime.timedelta(days=35)<datetime.datetime.fromisoformat(q['retain_until'].replace('Z','+00:00'))<=now+datetime.timedelta(days=37)\n")
 q={'method':method,'key':key}
 if version:q['version']=version
 if body is not None:q.update(size=len(body),sha256=hashlib.sha256(body).hexdigest(),md5=hashlib.md5(body).hexdigest(),retain_until=until)
 return remote(actor,s,q)
def request(method,key,body=None,version=None,until=None):
 auth=authorize('writer' if method=='PUT' else 'reader',method,key,body,version,until)
 expected='https://'+BUCKET+'.s3.ap-northeast-1.amazonaws.com/'+key+'?'
 if not auth['url'].startswith(expected) or auth['headers'].get('x-amz-expected-bucket-owner')!='121426368082':raise Failure(502)
 try:
  with client.open(urllib.request.Request(auth['url'],headers=auth['headers'],method=method,data=body),timeout=60) as r:
   h=r.headers;raw=r.read(8*1024*1024+1)
   if len(raw)>8*1024*1024:raise Failure(413)
   result={'VersionId':h.get('x-amz-version-id'),'ContentLength':int(h.get('Content-Length','0')),'LastModified':h.get('Last-Modified'),'@metadata':{'headers':{'date':h.get('Date')}},'mode':h.get('x-amz-object-lock-mode'),'until':h.get('x-amz-object-lock-retain-until-date')}
   if method in ('GET','PUT') and h.get('x-amz-server-side-encryption')!='AES256':raise Failure(502)
   if method=='GET':result['body64']=base64.b64encode(raw).decode()
   return result
 except urllib.error.HTTPError as e:raise Failure(e.code) from None
def serve(q):
 op=q['operation'];a=q['args']
 if a.get('Bucket')!=BUCKET or a.get('ExpectedBucketOwner')!='121426368082':raise Failure(400)
 if op in ('GetBucketVersioning','GetObjectLockConfiguration'):
  v=metadata('writer',{'GetBucketVersioning':'get-bucket-versioning','GetObjectLockConfiguration':'get-object-lock-configuration'}[op])
  if not v['success']:raise Failure(403)
  return v['response']
 key=a.get('Key','')
 if not re.fullmatch(KEY,key):raise Failure(400)
 version=a.get('VersionId')
 if op=='PutObject':
  if a.get('IfNoneMatch')!='*' or a.get('ServerSideEncryption')!='AES256' or a.get('ObjectLockMode')!='GOVERNANCE':raise Failure(400)
  body=base64.b64decode(a['body64'],validate=True)
  if len(body)!=a['ContentLength'] or base64.b64encode(hashlib.sha256(body).digest()).decode()!=a['ChecksumSHA256']:raise Failure(400)
  return request('PUT',key,body=body,until=a['ObjectLockRetainUntilDate'])
 if op not in ('HeadObject','GetObject','GetObjectRetention'):raise Failure(400)
 if op!='HeadObject' and not version:raise Failure(400)
 try:r=request('GET' if op=='GetObject' else 'HEAD',key,version=version)
 except Failure as e:
  if op=='HeadObject' and not version and e.status==403:
   # A successful, exact-prefix list establishes absence; 403 alone never does.
   listing=metadata('reader','list',key)
   if listing['success'] and not any(x['Key']==key for x in listing['response'].get('Contents',[])):raise Failure(404)
  raise
 if op=='GetObjectRetention':return {'Retention':{'Mode':r['mode'],'RetainUntilDate':r['until']}}
 return r
def main():
 journal=Path(sys.argv[1]);journal.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 def record(v):
  with journal.open('a') as f:f.write(json.dumps(v)+'\n');f.flush();os.fsync(f.fileno())
 for line in sys.stdin:
  try:
   q=json.loads(line);event={'operation':q['operation'],'key':q['args'].get('Key'),'version':q['args'].get('VersionId')}
   record(dict(event,state='started'));result=serve(q);record(dict(event,state='acknowledged',result={k:v for k,v in result.items() if k!='body64'}));out={'success':True,'result':result}
  except Failure as e:record(dict(event,state='failed',status=e.status));out={'success':False,'status':e.status}
  except Exception:out={'success':False,'status':502}
  print(json.dumps(out),flush=True)
if __name__=='__main__':main()
