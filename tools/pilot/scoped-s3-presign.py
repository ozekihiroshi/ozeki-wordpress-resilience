"""Generate one short-lived, scoped S3 request using this EC2 role. Never prints credentials."""
import datetime,hashlib,hmac,json,re,sys,urllib.parse,urllib.request
if sys.flags.optimize:raise RuntimeError('Optimized Python is not supported')
q=json.load(sys.stdin)
bucket='ceri-link-resilience-prod-121426368082';region='ap-northeast-1';owner='121426368082'
assert q['method'] in ('PUT','GET')
assert re.fullmatch(r'sites/wp-ceri-link/sets/RS-WP-CERI-[A-Za-z0-9-]+/[A-Za-z0-9._-]+',q['key'])
expected='my-ssm-role' if q['method']=='PUT' else 'OwrM1RecoveryReader'
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
 headers.update({'content-length':str(q['size']),'x-amz-checksum-sha256':base64.b64encode(bytes.fromhex(q['sha256'])).decode(),'x-amz-server-side-encryption':'AES256','if-none-match':'*'})
else:assert isinstance(q.get('version'),str) and q['version'] not in ('','null')
params={'X-Amz-Algorithm':'AWS4-HMAC-SHA256','X-Amz-Credential':creds['AccessKeyId']+'/'+scope,'X-Amz-Date':stamp,'X-Amz-Expires':'900','X-Amz-SignedHeaders':';'.join(sorted(headers)),'X-Amz-Security-Token':creds['Token']}
if q['method']=='GET':params['versionId']=q['version']
def enc(v):return urllib.parse.quote(v,safe='-_.~')
query='&'.join(enc(k)+'='+enc(v) for k,v in sorted(params.items()))
path='/'+urllib.parse.quote(q['key'],safe='/-_.~')
canonical='\n'.join([q['method'],path,query,''.join(k+':'+headers[k]+'\n' for k in sorted(headers)),params['X-Amz-SignedHeaders'],'UNSIGNED-PAYLOAD'])
message='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
def mac(k,s):return hmac.new(k,s.encode(),hashlib.sha256).digest()
key=mac(mac(mac(mac(('AWS4'+creds['SecretAccessKey']).encode(),day),region),'s3'),'aws4_request')
signature=hmac.new(key,message.encode(),hashlib.sha256).hexdigest()
print(json.dumps({'url':'https://'+host+path+'?'+query+'&X-Amz-Signature='+signature,'headers':headers,'role':role,'expires_at':(now+datetime.timedelta(minutes=15)).isoformat()}))
