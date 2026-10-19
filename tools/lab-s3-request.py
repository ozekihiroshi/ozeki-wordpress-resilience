"""Generate one short-lived, scoped S3 request using this EC2 role. Never prints credentials."""
import datetime,hashlib,hmac,json,re,sys,urllib.parse,urllib.request
if sys.flags.optimize:raise RuntimeError('Optimized Python is not supported')
q=json.load(sys.stdin)
bucket='ceri-link-resilience-lock-lab-121426368082';region='ap-northeast-1';owner='121426368082'
assert q.get('actor') in ('writer','reader')
import os,subprocess
cli='/usr/local/bin/aws' if q['actor']=='writer' else '/home/ubuntu/.local/owr-m1-runtime/bin/aws'
env={k:v for k,v in os.environ.items() if not k.startswith('AWS_')}
env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_DEFAULT_REGION=region,AWS_PAGER='')
def aws(args):
 p=subprocess.run([cli,*args,'--output','json'],env=env,capture_output=True,text=True,timeout=60)
 if p.returncode:
  match=re.search(r'\(([^)]+)\) when calling',p.stderr)
  return {'success':False,'error_code':match.group(1) if match else 'request_failed'}
 return {'success':True,'response':json.loads(p.stdout or '{}')}
identity=aws(['sts','get-caller-identity'])
expected='my-ssm-role' if q['actor']=='writer' else 'OwrM1RecoveryReader'
assert identity['success'] and identity['response']['Account']==owner and ':assumed-role/'+expected+'/' in identity['response']['Arn']
if q.get('operation')=='preflight':
 result={'role':expected,'account':owner,'identity_verified_by_sts':True}
 if q['actor']=='writer':
  for op in ['get-bucket-location','get-bucket-versioning','get-object-lock-configuration','get-bucket-encryption','get-public-access-block','get-bucket-policy','get-bucket-lifecycle-configuration']:
   result[op]=aws(['s3api',op,'--bucket',bucket,'--expected-bucket-owner',owner])
 print(json.dumps(result));sys.exit(0)
assert q['method'] in ('PUT','GET','DELETE')
assert re.fullmatch(r'sites/isolated-queue-lab/sets/AWS-[a-f0-9]{16}/(database.sql|wordpress-files.tar.gz|queue.sqlite|recovery-set.json|recovery-set.sig|permission-probe.txt)',q['key'])
expected='my-ssm-role' if q['actor']=='writer' else 'OwrM1RecoveryReader'
if q['method']=='DELETE':assert q['key'].endswith('/permission-probe.txt')
def imds(path,token=None,method='GET'):
 h={'X-aws-ec2-metadata-token':token} if token else {'X-aws-ec2-metadata-token-ttl-seconds':'60'}
 with urllib.request.urlopen(urllib.request.Request('http://169.254.169.254/latest/'+path,headers=h,method=method),timeout=5) as r:return r.read().decode()
token=imds('api/token',method='PUT')
assert json.loads(imds('dynamic/instance-identity/document',token))['accountId']==owner
role=imds('meta-data/iam/security-credentials/',token).strip();assert role==expected
creds=json.loads(imds('meta-data/iam/security-credentials/'+role,token));now=datetime.datetime.now(datetime.timezone.utc)
assert datetime.datetime.fromisoformat(creds['Expiration'].replace('Z','+00:00'))>now+datetime.timedelta(minutes=17)
stamp=now.strftime('%Y%m%dT%H%M%SZ');day=now.strftime('%Y%m%d');scope=day+'/'+region+'/s3/aws4_request'
host=bucket+'.s3.'+region+'.amazonaws.com';headers={'host':host,'x-amz-expected-bucket-owner':owner}
if q['method']=='PUT':
 assert type(q['size']) is int and 0<q['size']<1024**3 and re.fullmatch('[a-f0-9]{64}',q['sha256'])
 import base64
 assert re.fullmatch('[a-f0-9]{32}',q['md5'])
 headers.update({'content-md5':base64.b64encode(bytes.fromhex(q['md5'])).decode(),'x-amz-object-lock-mode':'GOVERNANCE','x-amz-object-lock-retain-until-date':(now+datetime.timedelta(days=35,minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')})
 headers.update({'content-length':str(q['size']),'x-amz-checksum-sha256':base64.b64encode(bytes.fromhex(q['sha256'])).decode(),'x-amz-server-side-encryption':'AES256','if-none-match':'*'})
else:assert isinstance(q.get('version'),str) and q['version'] not in ('','null')
params={'X-Amz-Algorithm':'AWS4-HMAC-SHA256','X-Amz-Credential':creds['AccessKeyId']+'/'+scope,'X-Amz-Date':stamp,'X-Amz-Expires':'900','X-Amz-SignedHeaders':';'.join(sorted(headers)),'X-Amz-Security-Token':creds['Token']}
if q['method'] in ('GET','DELETE'):params['versionId']=q['version']
def enc(v):return urllib.parse.quote(v,safe='-_.~')
query='&'.join(enc(k)+'='+enc(v) for k,v in sorted(params.items()))
path='/'+urllib.parse.quote(q['key'],safe='/-_.~')
canonical='\n'.join([q['method'],path,query,''.join(k+':'+headers[k]+'\n' for k in sorted(headers)),params['X-Amz-SignedHeaders'],'UNSIGNED-PAYLOAD'])
message='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
def mac(k,s):return hmac.new(k,s.encode(),hashlib.sha256).digest()
key=mac(mac(mac(mac(('AWS4'+creds['SecretAccessKey']).encode(),day),region),'s3'),'aws4_request')
signature=hmac.new(key,message.encode(),hashlib.sha256).hexdigest()
print(json.dumps({'url':'https://'+host+path+'?'+query+'&X-Amz-Signature='+signature,'headers':headers,'role':role,'expires_at':(now+datetime.timedelta(minutes=15)).isoformat()}))
