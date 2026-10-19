#!/usr/bin/env python3
"""Verify a protected candidate. Integrity approval only; never executes site code."""
import argparse,datetime,hashlib,json,re,subprocess
from pathlib import Path

def check(v,message):
 if not v:raise ValueError(message)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def date(s):
 d=datetime.datetime.fromisoformat(s.replace('Z','+00:00'));check(d.tzinfo is not None,'Naive time');return d

def verify(trust,approval,signature,anchor,bundle,site,set_id):
 now=datetime.datetime.now(datetime.timezone.utc)
 check(not trust.resolve().is_relative_to(bundle.resolve()),'Trust must be independent')
 pin=json.loads((trust/'pin.json').read_text())
 check(pin['status']=='active' and pin['site_id']==site and pin['set_id']==set_id,'Wrong or revoked trust')
 check(digest(trust/'public.pem')==pin['public_key_sha256'],'Wrong public key')
 check(approval.stat().st_size<65536 and digest(approval)==pin['approved_document_sha256'],'Unapproved document')
 result=subprocess.run(['openssl','dgst','-sha256','-verify',str(trust/'public.pem'),'-signature',str(signature),str(approval)],capture_output=True,timeout=10)
 check(result.returncode==0,'Invalid signature')
 a=json.loads(approval.read_text())
 check(a['format']=='owr-protected-candidate-approval-v1' and a['algorithm']=='rsa-sha256','Wrong approval format')
 check(a['site_id']==site and a['set_id']==set_id and a['scope']=='storage_integrity_candidate_only','Wrong approval scope')
 check(type(a['sequence']) is int and a['sequence']>=pin['minimum_sequence'],'Stale approval')
 check(date(a['issued_at'])<=now<date(a['expires_at']),'Expired or future approval')
 check(digest(anchor)==a['anchor_sha256'],'Anchor changed')
 root=json.loads(anchor.read_text());check(root['format']=='owr-protected-candidate-anchor-v1' and root['site_id']==site and root['set_id']==set_id,'Wrong anchor')
 prefix='sites/'+site+'/sets/'+set_id+'/'
 def validate_entry(e):
  loc=e['locator'];name=e['filename'];ret=e['retention'];obs=e['verification']
  check(re.fullmatch(r'[A-Za-z0-9._-]+',name) is not None and name not in ('.','..'),'Unsafe filename')
  check(loc['bucket']==pin['bucket'] and loc['region']==pin['region'] and loc['key']==prefix+name,'Wrong storage locator')
  check(isinstance(loc['version_id'],str) and loc['version_id'] not in ('','null'),'Unpinned version')
  check(ret['mode']=='GOVERNANCE' and (date(ret['retain_until'])-date(ret['last_modified'])).total_seconds()>35*86400-1,'Retention missing or short')
  check(date(ret['retain_until'])>now and date(ret['retain_until'])>=date(a['expires_at']),'Retention expired or shorter than approval')
  check(obs['size_and_sha256_match'] is True and obs['reader_role']=='OwrM1RecoveryReader' and loc['writer_role']=='my-ssm-role','Independent check missing')
  check(date(obs['checked_at'])<=date(a['issued_at']),'Observation after approval')
  path=bundle/name;check(not path.is_symlink() and path.is_file(),'Missing or linked asset')
  check(path.stat().st_size==loc['size_bytes'] and digest(path)==loc['sha256'],'Asset changed')
  return date(ret['retain_until'])
 check(root['manifest']['filename']=='protected-candidate.json','Wrong manifest filename')
 end=validate_entry(root['manifest'])
 m=json.loads((bundle/'protected-candidate.json').read_text())
 check(m['format']=='owr-protected-candidate-v1' and m['site_id']==site and m['set_id']==set_id,'Wrong manifest target')
 check(m['state']=='storage_verified_candidate' and m['production_recovery_approved'] is False and m['malware_cleanliness']=='unverified','Unsupported claim')
 required={'database':'database.sql.gz','site':'wordpress-files.tar.gz','runtime':'runtime-images.tar.gz','php_configuration':'uploads.ini','source_configuration':'source-configuration.json','capture_evidence':'capture.json','quarantine_evidence':'initial-live-quarantine-restore.json','recovery_instructions':'recovery-notes.txt'}
 check(len(m['assets'])==len(required) and {e['role']:e['filename'] for e in m['assets']}==required,'Incomplete assets')
 deadlines=[validate_entry(e) for e in m['assets']]
 check(date(m['minimum_asset_retention_until'])==min(deadlines),'Wrong asset minimum retention')
 check(date(root['minimum_retention_until'])==min(end,*deadlines),'Wrong set minimum retention')
 return {'passed':True,'site_id':site,'set_id':set_id,'assets_verified':len(deadlines),'approval_expires_at':a['expires_at'],'minimum_retention_until':root['minimum_retention_until'],'scope':a['scope'],'production_recovery_approved':False,'malware_cleanliness':'unverified','assets_executed':False}

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['trust','approval','signature','anchor','bundle','site','set-id']:p.add_argument('--'+n,required=True)
 a=p.parse_args()
 try:r=verify(Path(a.trust),Path(a.approval),Path(a.signature),Path(a.anchor),Path(a.bundle),a.site,a.set_id)
 except Exception as e:print(json.dumps({'passed':False,'error_type':type(e).__name__}));return 1
 print(json.dumps(r));return 0
if __name__=='__main__':raise SystemExit(main())
