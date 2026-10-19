"""Real S3 lab transport. EC2 roles authorize requests; secret URLs are never persisted."""
import datetime as dt,email.utils,hashlib,json,re,shlex,subprocess,time,urllib.error,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from pathlib import Path
BUCKET='ceri-link-resilience-lock-lab-121426368082';REGION='ap-northeast-1'
def wait_for_observation_time(modified,clock=None,sleep=time.sleep):
    clock=clock or (lambda:dt.datetime.now(dt.timezone.utc))
    gap=(modified-clock()).total_seconds()
    if gap>5:raise ValueError('S3 clock skew exceeds five seconds; synchronize host clock')
    if gap>0:sleep(gap+0.05)
    if modified>clock():raise ValueError('host clock did not advance to S3 modification time')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):raise RuntimeError('Unexpected redirect')
def authorize(actor,**request):
    script=Path(__file__).with_name('lab-s3-request.py').read_text()
    host={'writer':'community','reader':'dm'}[actor]
    p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3 -c '+shlex.quote(script)],input=json.dumps({'actor':actor,**request}).encode(),capture_output=True,timeout=120)
    if p.returncode:raise RuntimeError('EC2 authorization failed for '+actor+'; sensitive details suppressed')
    return json.loads(p.stdout)
def preflight():
    w=authorize('writer',operation='preflight');r=authorize('reader',operation='preflight')
    def response(op):
        item=w[op]
        if not item['success']:raise RuntimeError(op+': '+item['error_code'])
        return item['response']
    if response('get-bucket-location')['LocationConstraint']!=REGION:raise ValueError('region mismatch')
    if response('get-bucket-versioning')['Status']!='Enabled':raise ValueError('versioning disabled')
    if response('get-object-lock-configuration')['ObjectLockConfiguration']['ObjectLockEnabled']!='Enabled':raise ValueError('Object Lock disabled')
    if not all(response('get-public-access-block')['PublicAccessBlockConfiguration'].get(k) is True for k in ['BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets']):raise ValueError('public access block incomplete')
    rules=response('get-bucket-encryption')['ServerSideEncryptionConfiguration']['Rules']
    if not rules or any(x['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']!='AES256' for x in rules):raise ValueError('unexpected encryption; review required')
    for op,absent in [('get-bucket-policy','NoSuchBucketPolicy'),('get-bucket-lifecycle-configuration','NoSuchLifecycleConfiguration')]:
        if w[op].get('error_code')!=absent:raise ValueError('existing/unknown policy or lifecycle requires review: '+op)
    return {'passed':True,'writer':w,'reader':r,'bucket':BUCKET,'region':REGION}
class S3Adapter:
    def __init__(self,work):
        self.work=Path(work);self.work.mkdir(mode=0o700,parents=True,exist_ok=False)
        self.client=urllib.request.build_opener(NoRedirect);self.operations=[];self.request_count=0
    def save(self):
        (self.work/'operations.json').write_text(json.dumps(self.operations,indent=2)+'\n')
    def request(self,actor,method,key,body=None,version=None):
        q={'method':method,'key':key}
        if body is not None:q.update(size=len(body),sha256=hashlib.sha256(body).hexdigest(),md5=hashlib.md5(body).hexdigest())
        if version is not None:q['version']=version
        auth=authorize(actor,**q)
        expected='my-ssm-role' if actor=='writer' else 'OwrM1RecoveryReader'
        if auth['role']!=expected:raise ValueError('actor mismatch')
        url=urllib.parse.urlsplit(auth['url']);host=BUCKET+'.s3.'+REGION+'.amazonaws.com'
        if url.scheme!='https' or url.netloc!=host or url.path!='/'+urllib.parse.quote(key,safe='/-_.~') or url.fragment:raise ValueError('authorization URL outside dedicated bucket/key')
        if auth['headers'].get('host')!=host or auth['headers'].get('x-amz-expected-bucket-owner')!='121426368082':raise ValueError('authorization owner/host mismatch')
        if version is not None and urllib.parse.parse_qs(url.query).get('versionId')!=[version]:raise ValueError('authorization version mismatch')
        try:
            self.request_count+=1
            return self.client.open(urllib.request.Request(auth['url'],headers=auth['headers'],method=method,data=body),timeout=300)
        except urllib.error.HTTPError as exc:
            code=exc.code
            try:error=ET.fromstring(exc.read(8192)).findtext('Code','Unknown')
            except ET.ParseError:error='Unknown'
            finally:exc.close()
            if not re.fullmatch('[A-Za-z0-9]+',error):error='Unknown'
            raise RuntimeError('S3 '+method+' HTTP '+str(code)+' '+error) from None
        except Exception:raise RuntimeError('S3 request failed; sensitive details suppressed') from None
    def put(self,bucket,key,body):
        if bucket!=BUCKET:raise ValueError('wrong bucket')
        event={'method':'PUT','key':key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'state':'started'}
        if any(x['method']=='PUT' and x['key']==key for x in self.operations):raise ValueError('uncertain or repeated PUT; inspect receipt')
        self.operations.append(event);self.save()
        with self.request('writer','PUT',key,body=body) as response:
            version=response.headers.get('x-amz-version-id')
            if not version or version=='null' or response.headers.get('x-amz-server-side-encryption')!='AES256':raise ValueError('PUT version/encryption missing')
        event.update(state='acknowledged',version_id=version);self.save();return version
    def get(self,locator):
        if locator['bucket']!=BUCKET or locator['region']!=REGION or locator['version_id'] in ('','null'):raise ValueError('invalid locator')
        with self.request('reader','GET',locator['key'],version=locator['version_id']) as response:
            h=response.headers;size=int(h['Content-Length'])
            if size!=locator['size_bytes']:raise ValueError('download size mismatch')
            body=response.read(size+1)
            if len(body)!=size:raise ValueError('incomplete download')
            result={'body':body,'version_id':h.get('x-amz-version-id'),'mode':h.get('x-amz-object-lock-mode'),'retain_until':h.get('x-amz-object-lock-retain-until-date'),'last_modified':email.utils.parsedate_to_datetime(h['Last-Modified']).isoformat(),'reader_identity':'OwrM1RecoveryReader'}
            if h.get('x-amz-server-side-encryption')!='AES256':raise ValueError('GET encryption mismatch')
        wait_for_observation_time(dt.datetime.fromisoformat(result['last_modified']))
        self.operations.append({'method':'GET','key':locator['key'],'version_id':result['version_id'],'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'retention':{k:result[k] for k in ['mode','retain_until','last_modified']}});self.save()
        return result
