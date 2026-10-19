# Explain intent before any imports that may access local trust or remote hosts.
if __name__ == '__main__':
 import argparse, sys
 parser = argparse.ArgumentParser(description='Site-specific 2026-10-18 pilot; not a scheduler or general installer. See tools/README.md.')
 parser.add_argument('--execute-pilot', action='store_true', help='Explicitly run the reviewed, site-specific pilot (cloud/signing/Docker effects possible).')
 args = parser.parse_args()
 if not args.execute_pilot:
  parser.error('Execution disabled by default. Read tools/README.md before using --execute-pilot.')
 if sys.flags.optimize:
  parser.error('Optimized Python disables pilot checks; use normal Python without -O/-OO.')
"""Direct S3 transfer with separate EC2 role authorizations; never logs presigned URLs."""
import os,json,hashlib,subprocess,shlex,urllib.request,urllib.error,datetime,email.utils
from pathlib import Path
os.umask(0o077)
ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path.home()/'.local/share/owr-captures/wp-ceri-link-20261018T073750Z'
SET='RS-WP-CERI-20261018-001';BUCKET='ceri-link-resilience-prod-121426368082';PREFIX='sites/wp-ceri-link/sets/'+SET+'/'
WORK=Path.home()/'.local/share/owr-production'/SET
READ=WORK/'reader-download'
SCRIPT=Path(__file__).with_name('scoped-s3-presign.py').read_text(encoding='utf-8-sig')
def now():return datetime.datetime.now(datetime.timezone.utc)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,data):
 with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def auth(method,key,**extra):
 host='community' if method=='PUT' else 'dm'
 p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'python3 -c '+shlex.quote(SCRIPT)],input=json.dumps({'method':method,'key':key,**extra}).encode(),capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError('Scoped authorization failed: '+host)
 a=json.loads(p.stdout);assert a['role']==('my-ssm-role' if method=='PUT' else 'OwrM1RecoveryReader');return a
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):raise RuntimeError('Unexpected redirect')
client=urllib.request.build_opener(NoRedirect)
def request(a,method,data=None):
 try:return client.open(urllib.request.Request(a['url'],data=data,headers=a['headers'],method=method),timeout=300)
 except urllib.error.HTTPError as e:raise RuntimeError('S3 '+method+' HTTP '+str(e.code)) from None
 except Exception:raise RuntimeError('Transfer failed; request details suppressed') from None

def transfer(path,role):
 name=path.name;size=path.stat().st_size;digest=sha(path);receipt=WORK/(name+'.receipt.json');key=PREFIX+name
 if receipt.exists():
  rec=json.loads(receipt.read_text());assert rec['sha256']==digest and rec['size_bytes']==size and rec['key']==key
 else:
  marker=WORK/(name+'.put-started.json');assert not marker.exists(),'Uncertain prior PUT; inspect before retry'
  a=auth('PUT',key,size=size,sha256=digest)
  write(marker,{'key':key,'started_at':now().isoformat(),'sha256':digest,'size_bytes':size})
  with path.open('rb') as f,request(a,'PUT',f) as response:
   version=response.headers.get('x-amz-version-id');assert version and version!='null'
   assert response.headers.get('x-amz-server-side-encryption')=='AES256'
   rec={'bucket':BUCKET,'region':'ap-northeast-1','key':key,'version_id':version,'size_bytes':size,'sha256':digest,'put_acknowledged_at':now().isoformat(),'writer_role':'my-ssm-role'}
  write(receipt,rec);print('Stored '+name+' '+str(size)+' bytes',flush=True)
 observed=WORK/(name+'.verified.json')
 if observed.exists():
  obj=json.loads(observed.read_text());assert (READ/name).is_file() and sha(READ/name)==digest and obj['locator']==rec;return obj
 a=auth('GET',key,version=rec['version_id']);temp=READ/(name+'.partial');assert not temp.exists() and not (READ/name).exists()
 with request(a,'GET') as response:
  h=response.headers
  assert h.get('x-amz-version-id')==rec['version_id'] and int(h['Content-Length'])==size
  assert h.get('x-amz-object-lock-mode')=='GOVERNANCE'
  until=datetime.datetime.fromisoformat(h['x-amz-object-lock-retain-until-date'].replace('Z','+00:00'));stored=email.utils.parsedate_to_datetime(h['Last-Modified'])
  assert (until-stored).total_seconds()>35*86400-1 and until>now()
  total=0;hashed=hashlib.sha256()
  with temp.open('xb') as f:
   for block in iter(lambda:response.read(1024*1024),b''):
    total+=len(block);assert total<=size;hashed.update(block);f.write(block)
   f.flush();os.fsync(f.fileno())
  assert total==size and hashed.hexdigest()==digest
  os.link(temp,READ/name);temp.unlink()
 obj={'role':role,'filename':name,'locator':rec,'retention':{'mode':'GOVERNANCE','retain_until':until.isoformat(),'last_modified':stored.isoformat(),'precision_tolerance_seconds':1},'verification':{'reader_role':'OwrM1RecoveryReader','checked_at':now().isoformat(),'size_and_sha256_match':True}}
 write(observed,obj);print('Independently verified '+name,flush=True);return obj

def main():
 WORK.mkdir(parents=True,exist_ok=True,mode=0o700);READ.mkdir(exist_ok=True,mode=0o700)
 pre=json.loads((ROOT/'.local/production-preflight-20261018.json').read_text())
 assert (now()-datetime.datetime.fromisoformat(pre['checked_at'])).total_seconds()<7200
 assert json.loads((ROOT/'evidence-public/production-storage-canary.json').read_text())['passed']
 receipt=json.loads((SOURCE/'capture.json').read_text());assert receipt['passed']
 for a in receipt['assets']:assert (SOURCE/a['file']).stat().st_size==a['compressed_bytes'] and sha(SOURCE/a['file'])==a['sha256']
 pairs=[(SOURCE/a['file'],a['role']) for a in receipt['assets']]
 pairs += [(SOURCE/'uploads.ini','php_configuration'),(SOURCE/'source-configuration.json','source_configuration'),(SOURCE/'capture.json','capture_evidence'),(ROOT/'evidence-public/initial-live-quarantine-restore.json','quarantine_evidence')]
 notes=WORK/'recovery-notes.txt'
 if not notes.exists():notes.write_text('Storage-verified candidate for wp.ceri.link. Cross-asset consistency and malware cleanliness unverified.\nVerify independently pinned signed candidate manifest and all exact S3 versions before executing captured code.\nSite archive includes original secrets; replace wp-config with fresh DB credentials and salts.\nUse new volumes and DB; network none with shared loopback only, no ports. Disable cron, external HTTP and email.\nRuntime IDs: capture.json. SQL prefix: wp_. Never restore into demand or an existing DB.\nPrior local validation: 15343 file hashes, 12 tables/409 rows, 2 published pages, 23 media responses.\nThis signature does not authorize production publication.\n')
 pairs.append((notes,'recovery_instructions'))
 observations=[transfer(path,role) for path,role in pairs]
 manifest=WORK/'protected-candidate.json'
 payload={'format':'owr-protected-candidate-v1','site_id':'wp-ceri-link','site_url':'https://wp.ceri.link/','set_id':SET,'state':'storage_verified_candidate','capture_consistency':receipt['consistency'],'malware_cleanliness':'unverified','production_recovery_approved':False,'assets':observations,'minimum_asset_retention_until':min(x['retention']['retain_until'] for x in observations),'created_at':now().isoformat()}
 if not manifest.exists():write(manifest,payload)
 else:assert json.loads(manifest.read_text())['assets']==observations
 m=transfer(manifest,'protected_candidate_manifest');anchor=WORK/'candidate-anchor.json'
 if not anchor.exists():write(anchor,{'format':'owr-protected-candidate-anchor-v1','site_id':'wp-ceri-link','set_id':SET,'manifest':m,'minimum_retention_until':min(payload['minimum_asset_retention_until'],m['retention']['retain_until'])})
 print(json.dumps({'passed':True,'stage':'storage_and_independent_download_verified','assets':len(observations),'work':str(WORK),'anchor_sha256':sha(anchor)}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'passed':False,'error_type':type(e).__name__,'message':str(e) if isinstance(e,(AssertionError,RuntimeError)) else 'Details suppressed'}),flush=True);raise SystemExit(1)
