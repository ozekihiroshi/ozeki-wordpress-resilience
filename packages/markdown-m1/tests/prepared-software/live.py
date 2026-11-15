"""Isolated test transport. EC2 credentials stay on the host, never in WordPress."""
import base64,json,os,re,threading,time
import boto3
from botocore.config import Config

class Live:
 def __init__(self,lab):
  self.lab=lab;self.stopped=False
  self.scope={'bucket':'ceri-link-resilience-lock-lab-121426368082','owner':'121426368082','region':'ap-northeast-1','prefix':'sites/isolated-queue-lab/delete-validation-20261026/onboarding-20261026/input-audit-20261111/acf-fix-only/prepared-software-'+os.urandom(12).hex()+'/'}
  self.s3=boto3.client('s3',region_name=self.scope['region'],config=Config(connect_timeout=5,read_timeout=40,retries={'max_attempts':2}))
  assert not self.fingerprint(),'Fresh isolated prefix is not empty'
  (lab/'aws.json').write_text(json.dumps(self.scope));(lab/'ipc').mkdir(mode=0o777);os.chmod(lab/'ipc',0o777)
  (lab/'live').write_text(self.scope['prefix'])
  self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
 def fingerprint(self):
  out={}
  for page in self.s3.get_paginator('list_object_versions').paginate(Bucket=self.scope['bucket'],Prefix=self.scope['prefix'],ExpectedBucketOwner=self.scope['owner']):
   assert not page.get('DeleteMarkers'),'Unexpected deletion'
   for x in page.get('Versions',[]):out[x['Key']+'#'+x['VersionId']]=[x['ETag'],x['Size'],x['IsLatest']]
  return out
 def request(self,name,a):
  # PHP SDK execution metadata is not an S3 API parameter.
  a=dict(a)
  for key in ['@http','@context']:a.pop(key,None)
  methods={'GetObject':'get_object','PutObject':'put_object','ListObjectsV2':'list_objects_v2','GetBucketVersioning':'get_bucket_versioning','GetObjectLockConfiguration':'get_object_lock_configuration','GetObjectRetention':'get_object_retention'}
  assert name in methods and a['Bucket']==self.scope['bucket'] and a.get('ExpectedBucketOwner')==self.scope['owner'],'Outside isolated bucket'
  if 'Key' in a:assert a['Key'].startswith(self.scope['prefix']) and '..' not in a['Key'],'Outside isolated key'
  if name=='ListObjectsV2':assert a['Prefix'].startswith(self.scope['prefix']),'Outside isolated listing'
  if name=='PutObject':
   assert a['IfNoneMatch']=='*' and a['ServerSideEncryption']=='AES256','Create-only encrypted writes required'
   a['Body']=base64.b64decode(a.pop('body64'),validate=True)
  r=getattr(self.s3,methods[name])(**a);r.pop('ResponseMetadata',None)
  if 'Body' in r:r['body64']=base64.b64encode(r.pop('Body').read()).decode()
  return r
 def loop(self):
  done=set()
  while not self.stopped:
   for p in (self.lab/'ipc').glob('*.request'):
    if p.name in done:continue
    done.add(p.name);q=json.loads(p.read_text());a=q['args']
    try:reply={'success':True,'result':self.request(q['operation'],a)}
    except Exception as ex:reply={'success':False,'error':getattr(ex,'response',{}).get('Error',{}).get('Code',type(ex).__name__)}
    temp=p.with_suffix('.reply-tmp');temp.write_text(json.dumps(reply,default=lambda x:x.isoformat()));temp.rename(p.with_suffix('.response'))
    with (self.lab/'live-events.jsonl').open('a') as f:f.write(json.dumps({'operation':q['operation'],'key':a.get('Key'),'success':reply['success'],'error':reply.get('error')})+'\n')
   time.sleep(.02)
 def stop(self):
  self.stopped=True;self.thread.join(timeout=50)
