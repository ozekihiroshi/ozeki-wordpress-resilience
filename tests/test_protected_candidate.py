import importlib.util,unittest,tempfile,subprocess,json,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('candidate',ROOT/'tools/verify-protected-candidate.py');v=importlib.util.module_from_spec(s);s.loader.exec_module(v)
class CandidateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.trust=self.root/'trust';self.trust.mkdir();self.bundle=self.root/'bundle';self.bundle.mkdir();self.now=datetime.datetime.now(datetime.timezone.utc)
  subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(self.root/'key')],check=True,capture_output=True)
  subprocess.run(['openssl','pkey','-in',str(self.root/'key'),'-pubout','-out',str(self.trust/'public.pem')],check=True,capture_output=True)
  self.roles={'database':'database.sql.gz','site':'wordpress-files.tar.gz','runtime':'runtime-images.tar.gz','php_configuration':'uploads.ini','source_configuration':'source-configuration.json','capture_evidence':'capture.json','quarantine_evidence':'initial-live-quarantine-restore.json','recovery_instructions':'recovery-notes.txt'}
  for f in self.roles.values():(self.bundle/f).write_bytes(b'fixture')
  self.assets=[self.entry(role,name) for role,name in self.roles.items()]
  self.approval=self.root/'approval.json';self.signature=self.root/'signature';self.anchor=self.root/'anchor.json';self.build()
 def tearDown(self):self.tmp.cleanup()
 def write(self,p,o):p.write_text(json.dumps(o))
 def entry(self,role,name):
  return {'role':role,'filename':name,'locator':{'bucket':'test-bucket','region':'ap-northeast-1','key':'sites/wp-ceri-link/sets/TEST/'+name,'version_id':'v1','size_bytes':(self.bundle/name).stat().st_size,'sha256':v.digest(self.bundle/name),'writer_role':'my-ssm-role'},'retention':{'mode':'GOVERNANCE','last_modified':self.now.isoformat(),'retain_until':(self.now+datetime.timedelta(days=35)).isoformat()},'verification':{'reader_role':'OwrM1RecoveryReader','checked_at':self.now.isoformat(),'size_and_sha256_match':True}}
 def build(self,changes=None):
  deadline=min(e['retention']['retain_until'] for e in self.assets)
  self.write(self.bundle/'protected-candidate.json',{'format':'owr-protected-candidate-v1','site_id':'wp-ceri-link','set_id':'TEST','state':'storage_verified_candidate','production_recovery_approved':False,'malware_cleanliness':'unverified','assets':self.assets,'minimum_asset_retention_until':deadline})
  self.write(self.anchor,{'format':'owr-protected-candidate-anchor-v1','site_id':'wp-ceri-link','set_id':'TEST','manifest':self.entry('manifest','protected-candidate.json'),'minimum_retention_until':deadline})
  a={'format':'owr-protected-candidate-approval-v1','algorithm':'rsa-sha256','site_id':'wp-ceri-link','set_id':'TEST','sequence':1,'scope':'storage_integrity_candidate_only','issued_at':self.now.isoformat(),'expires_at':(self.now+datetime.timedelta(days=7)).isoformat(),'anchor_sha256':v.digest(self.anchor)};a.update(changes or {});self.write(self.approval,a)
  subprocess.run(['openssl','dgst','-sha256','-sign',str(self.root/'key'),'-out',str(self.signature),str(self.approval)],check=True,capture_output=True)
  self.write(self.trust/'pin.json',{'status':'active','site_id':'wp-ceri-link','set_id':'TEST','minimum_sequence':1,'public_key_sha256':v.digest(self.trust/'public.pem'),'approved_document_sha256':v.digest(self.approval),'bucket':'test-bucket','region':'ap-northeast-1'})
 def verify(self):return v.verify(self.trust,self.approval,self.signature,self.anchor,self.bundle,'wp-ceri-link','TEST')
 def test_valid(self):self.assertTrue(self.verify()['passed'])
 def test_expired(self):
  self.build({'expires_at':(self.now-datetime.timedelta(seconds=1)).isoformat()})
  with self.assertRaises(ValueError):self.verify()
 def test_wrong_scope(self):
  self.build({'scope':'production'})
  with self.assertRaises(ValueError):self.verify()
 def test_short_retention(self):
  self.assets[0]['retention']['retain_until']=(self.now+datetime.timedelta(days=1)).isoformat();self.build()
  with self.assertRaises(ValueError):self.verify()
 def test_missing_version(self):
  self.assets[0]['locator']['version_id']='null';self.build()
  with self.assertRaises(ValueError):self.verify()
 def test_wrong_bucket(self):
  self.assets[0]['locator']['bucket']='other';self.build()
  with self.assertRaises(ValueError):self.verify()
 def test_missing_asset(self):
  self.assets.pop();self.build()
  with self.assertRaises(ValueError):self.verify()
 def test_mutated_asset(self):
  (self.bundle/'database.sql.gz').write_bytes(b'changed')
  with self.assertRaises(ValueError):self.verify()
 def test_changed_manifest(self):
  with (self.bundle/'protected-candidate.json').open('a') as f:f.write(' ')
  with self.assertRaises(ValueError):self.verify()
 def test_bad_signature(self):
  self.signature.write_bytes(b'invalid')
  with self.assertRaises(ValueError):self.verify()
 def test_revoked(self):
  p=self.trust/'pin.json';d=json.loads(p.read_text());d['status']='revoked';self.write(p,d)
  with self.assertRaises(ValueError):self.verify()
 def test_trust_inside_bundle(self):
  with self.assertRaises(ValueError):v.verify(self.bundle,self.approval,self.signature,self.anchor,self.bundle,'wp-ceri-link','TEST')
if __name__=='__main__':unittest.main()
