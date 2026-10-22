import datetime as dt, importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'tools/rbr-approved-kit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Approval(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.trust=self.root/'trust';self.trust.mkdir()
  self.key=self.root/'private.pem';subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(self.key)],check=True,capture_output=True)
  (self.trust/'public.pem').write_bytes(subprocess.check_output(['openssl','pkey','-in',str(self.key),'-pubout']))
  self.approval=self.root/'approval.json';self.signature=self.root/'approval.sig';self.receipt=self.root/'receipt.json'
  self.ref={'locator':{'version_id':'fixed-one'},'sha256':'a'*64,'size_bytes':10};self.receipt.write_bytes(m.k.canonical(self.ref))
  now=dt.datetime.now(dt.timezone.utc);self.a={'format':'owr-rbr-kit-approval-v1','algorithm':'rsa-sha256','site_id':'corporate-test','set_id':'kit-test','sequence':1,'issued_at':(now-dt.timedelta(minutes=1)).isoformat(),'expires_at':(now+dt.timedelta(hours=1)).isoformat(),'scope':'generated-private-reconstruction','public_activation':False,'root_receipt':self.ref}
  self.pin={'status':'active','site_id':'corporate-test','public_key_sha256':m.v.digest((self.trust/'public.pem').read_bytes()),'minimum_sequence':1};self.sign()
 def sign(self):
  self.approval.write_bytes(m.k.canonical(self.a));self.signature.write_bytes(subprocess.check_output(['openssl','dgst','-sha256','-sign',str(self.key),str(self.approval)]));self.pin['approved_document_sha256']=m.v.digest(self.approval.read_bytes());self.save_pin()
 def save_pin(self):(self.trust/'pin.json').write_bytes(m.k.canonical(self.pin))
 def verify(self):return m.verify(self.trust,self.approval,self.signature,self.receipt,'corporate-test','kit-test')
 def denied(self):
  with patch.object(m.c,'current',return_value={'revision':1}),patch.object(m.k,'fetch') as fetch:
   with self.assertRaises((ValueError,FileNotFoundError)):m.execute(self.trust,self.approval,self.signature,self.receipt,'corporate-test','kit-test',self.root/'work',self.root/'out')
   fetch.assert_not_called();self.assertFalse((self.root/'work').exists())
 def test_valid_signature(self):
  with patch.object(m.c,'current',return_value={'revision':1}):self.assertEqual(self.verify(),{'revision':1})
 def test_missing_signature(self):self.signature.unlink();self.denied()
 def test_tampered_document(self):self.approval.write_bytes(self.approval.read_bytes()+b' ');self.denied()
 def test_wrong_fixed_version(self):self.receipt.write_bytes(m.k.canonical({'locator':{'version_id':'other'}}));self.denied()
 def test_expired(self):self.a['expires_at']=self.a['issued_at'];self.sign();self.denied()
 def test_future(self):self.a['issued_at']=self.a['expires_at'];self.sign();self.denied()
 def test_wrong_site(self):self.a['site_id']='other';self.sign();self.denied()
 def test_wrong_set(self):self.a['set_id']='other';self.sign();self.denied()
 def test_stale_sequence(self):self.pin['minimum_sequence']=2;self.save_pin();self.denied()
 def test_revoked_pin(self):self.pin['status']='revoked';self.save_pin();self.denied()
 def test_wrong_key(self):self.pin['public_key_sha256']='0'*64;self.save_pin();self.denied()
 def test_unapproved_document(self):self.pin['approved_document_sha256']='0'*64;self.save_pin();self.denied()
 def test_public_activation(self):self.a['public_activation']=True;self.sign();self.denied()
 def test_current_authority_rejection(self):
  with patch.object(m.c,'current',side_effect=ValueError('revoked authority')),patch.object(m.k,'fetch') as f:
   with self.assertRaises(ValueError):m.execute(self.trust,self.approval,self.signature,self.receipt,'corporate-test','kit-test',self.root/'work',self.root/'out')
   f.assert_not_called()
 def test_change_after_fetch(self):
  with patch.object(m.c,'current',side_effect=[{'revision':1},{'revision':2}]),patch.object(m.k,'fetch'):
   with self.assertRaisesRegex(ValueError,'Trust changed'):m.execute(self.trust,self.approval,self.signature,self.receipt,'corporate-test','kit-test',self.root/'work',self.root/'out')
if __name__=='__main__':unittest.main()
