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
import json,datetime,subprocess,shutil,importlib.util,os,tempfile
from pathlib import Path
os.umask(0o077)
base=Path(__file__).resolve().parent;repo=base.parents[1]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=mod('publisher',base/'publish-protected-candidate.py');v=mod('verifier',repo/'tools/verify-protected-candidate.py')
w=p.WORK;source=Path.home()/'.local/share/owr-trust/key-20261018';trust=Path.home()/'.local/share/owr-trust/wp-ceri-link'/p.SET
old=json.loads((source/'pin.json').read_text());assert old['status']=='active' and p.sha(source/'public.pem')==old['public_key_sha256']
anchor=json.loads((w/'candidate-anchor.json').read_text());now=p.now()
expires=min(now+datetime.timedelta(days=7),v.date(anchor['minimum_retention_until']))
assert expires>now+datetime.timedelta(days=1)
approval=w/'candidate-approval.json';sig=w/'candidate-approval.sig'
if not approval.exists():
 p.write(approval,{'format':'owr-protected-candidate-approval-v1','algorithm':'rsa-sha256','site_id':'wp-ceri-link','set_id':p.SET,'sequence':1,'issued_at':now.isoformat(),'expires_at':expires.isoformat(),'anchor_sha256':p.sha(w/'candidate-anchor.json'),'scope':'storage_integrity_candidate_only','consistency':'cross-asset point-in-time consistency unverified','malware_cleanliness':'unverified'})
 subprocess.run(['openssl','dgst','-sha256','-sign',str(source/'private.pem'),'-out',str(sig),str(approval)],check=True,capture_output=True)
 trust.mkdir(parents=True,exist_ok=False,mode=0o700);shutil.copyfile(source/'public.pem',trust/'public.pem')
 p.write(trust/'pin.json',{'status':'active','site_id':'wp-ceri-link','set_id':p.SET,'minimum_sequence':1,'public_key_sha256':p.sha(source/'public.pem'),'approved_document_sha256':p.sha(approval),'bucket':p.BUCKET,'region':'ap-northeast-1'})
result=v.verify(trust,approval,sig,w/'candidate-anchor.json',p.READ,'wp-ceri-link',p.SET)
# Negative checks use independent temporary copies; originals never altered.
checks=['valid_signature_and_all_downloaded_assets']
with tempfile.TemporaryDirectory(prefix='owr-candidate-negative-') as tmp:
 t=Path(tmp);ttrust=t/'trust';shutil.copytree(trust,ttrust)
 def rejected(name,fn):
  try:fn()
  except (ValueError,FileNotFoundError):checks.append(name);return
  raise RuntimeError('Negative verification unexpectedly passed: '+name)
 pin=json.loads((ttrust/'pin.json').read_text());revoked=dict(pin,status='revoked');(ttrust/'pin.json').write_text(json.dumps(revoked))
 rejected('revoked_pin',lambda:v.verify(ttrust,approval,sig,w/'candidate-anchor.json',p.READ,'wp-ceri-link',p.SET))
 (ttrust/'pin.json').write_text(json.dumps(dict(pin,minimum_sequence=2)))
 rejected('stale_sequence',lambda:v.verify(ttrust,approval,sig,w/'candidate-anchor.json',p.READ,'wp-ceri-link',p.SET))
 (ttrust/'pin.json').write_text(json.dumps(pin))
 rejected('wrong_site',lambda:v.verify(ttrust,approval,sig,w/'candidate-anchor.json',p.READ,'another-site',p.SET))
 bad=t/'bad.sig';raw=sig.read_bytes();bad.write_bytes(bytes([raw[0]^1])+raw[1:])
 rejected('signature_tampering',lambda:v.verify(ttrust,approval,bad,w/'candidate-anchor.json',p.READ,'wp-ceri-link',p.SET))
 badanchor=t/'anchor.json';badanchor.write_bytes((w/'candidate-anchor.json').read_bytes()+b' ')
 rejected('anchor_tampering',lambda:v.verify(ttrust,approval,sig,badanchor,p.READ,'wp-ceri-link',p.SET))
 bundle=t/'bundle';bundle.mkdir()
 for f in p.READ.iterdir():
  if f.is_file():os.link(f,bundle/f.name)
 path=bundle/'capture.json';path.unlink();path.write_bytes(b'tampered')
 rejected('asset_tampering',lambda:v.verify(ttrust,approval,sig,w/'candidate-anchor.json',bundle,'wp-ceri-link',p.SET))
 path.unlink()
 rejected('missing_asset',lambda:v.verify(ttrust,approval,sig,w/'candidate-anchor.json',bundle,'wp-ceri-link',p.SET))
# Store the signed envelope too; trust pin remains independently managed.
envelope=[p.transfer(w/'candidate-anchor.json','candidate_anchor'),p.transfer(approval,'candidate_approval'),p.transfer(sig,'candidate_signature')]
result=v.verify(trust,p.READ/'candidate-approval.json',p.READ/'candidate-approval.sig',p.READ/'candidate-anchor.json',p.READ,'wp-ceri-link',p.SET)
p.write(w/'signed-result.json',{'verification':result,'checks':checks,'envelope':envelope,'trust_directory':str(trust),'private_key_copied':False,'source_temp_archives':False,'server_temp_archives':False,'s3_transfer_method':'short_lived_role_scoped_presigned_requests','checked_at':p.now().isoformat()})
p.write(trust/'retrieval-envelope.json',{'site_id':'wp-ceri-link','set_id':p.SET,'envelope':envelope,'manifest':anchor['manifest']})
for name in ['candidate-approval.json','candidate-approval.sig','candidate-anchor.json']:
 shutil.copyfile(p.READ/name,trust/name)
shutil.copyfile(repo/'tools/verify-protected-candidate.py',trust/'verify-protected-candidate.py')
print(json.dumps({'passed':True,'verification':result,'checks':checks,'trust_directory':str(trust)}))
