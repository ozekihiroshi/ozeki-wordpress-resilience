"""Security regression tests: rejected approvals must never reach Docker."""
import hashlib, json, os, subprocess, sys, tarfile, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
class ApprovalGateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.bundle=self.root/'bundle';self.bundle.mkdir();self.trust=self.root/'trust';self.trust.mkdir()
  boot=self.bundle/'bootstrap';boot.mkdir();(boot/'verify.php').write_text('<?php /* test */')
  with tarfile.open(self.bundle/'bootstrap.tar.gz','w:gz') as t:t.add(boot,arcname='bootstrap')
  self.write(self.bundle/'ram.json',{'site_id':'site','set_id':'set','assets':[]})
  self.write(self.bundle/'recovery-set.json',{'site_id':'site','set_id':'set','ram_sha256':self.sha(self.bundle/'ram.json')})
  anchor={'site_id':'site','set_id':'set'}
  for k,f in [('set','recovery-set.json'),('ram','ram.json'),('bootstrap','bootstrap.tar.gz')]:
   p=self.bundle/f;anchor[k]={'locator':{'version_id':'fixed'},'size_bytes':p.stat().st_size,'sha256':self.sha(p)}
  self.write(self.bundle/'anchor.json',anchor)
  subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(self.trust/'private.pem')],check=True,capture_output=True)
  subprocess.run(['openssl','pkey','-in',str(self.trust/'private.pem'),'-pubout','-out',str(self.trust/'public.pem')],check=True,capture_output=True)
  now=datetime.now(timezone.utc)
  self.data={'format':'owr-recovery-approval-v1','algorithm':'rsa-sha256','site_id':'site','set_id':'set','sequence':1,'issued_at':(now-timedelta(minutes=1)).isoformat(),'expires_at':(now+timedelta(days=1)).isoformat(),'anchor_sha256':self.sha(self.bundle/'anchor.json')}
  self.pin={'status':'active','site_id':'site','minimum_sequence':1,'public_key_sha256':self.sha(self.trust/'public.pem')}
  self.sign()
  self.bin=self.root/'bin';self.bin.mkdir();self.marker=self.root/'docker-called'
  docker=self.bin/'docker';docker.write_text('#!/bin/sh\ntouch "$OWR_TEST_MARKER"\nexit 99\n');docker.chmod(0o700)
 def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def write(self,p,data):p.write_text(json.dumps(data))
 def sign(self):
  self.write(self.trust/'approval.json',self.data)
  subprocess.run(['openssl','dgst','-sha256','-sign',str(self.trust/'private.pem'),'-out',str(self.trust/'approval.sig'),str(self.trust/'approval.json')],check=True,capture_output=True)
  self.pin['approved_document_sha256']=self.sha(self.trust/'approval.json');self.write(self.trust/'pin.json',self.pin)
 def run_gate(self,verify_only=False,omit=False):
  cmd=[sys.executable,'-O',str(ROOT/'tools/run-independent-recovery.py'),'--bundle',str(self.bundle),'--output',str(self.root/'out'),'--run','1']
  if not omit:cmd+=['--trust-dir',str(self.trust),'--approval',str(self.trust/'approval.json'),'--signature',str(self.trust/'approval.sig'),'--site-id','site','--set-id','set']
  if verify_only:cmd+=['--verify-only']
  return subprocess.run(cmd,capture_output=True,text=True,env={**os.environ,'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],'OWR_TEST_MARKER':str(self.marker)})
 def rejected(self):
  result=self.run_gate();self.assertNotEqual(result.returncode,0);self.assertFalse(self.marker.exists());self.assertFalse((self.root/'out').exists())
 def test_valid_preflight_no_side_effects(self):
  result=self.run_gate(True);self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(self.marker.exists());self.assertFalse((self.root/'out').exists())
 def test_valid_full_mode_reaches_docker(self):
  result=self.run_gate();self.assertTrue(self.marker.exists());self.assertNotEqual(result.returncode,0)
 def test_missing_arguments(self):
  self.assertNotEqual(self.run_gate(omit=True).returncode,0);self.assertFalse(self.marker.exists())
 def test_tampered_approval(self):
  with (self.trust/'approval.json').open('a') as f:f.write(' ')
  self.rejected()
 def test_missing_signature(self):(self.trust/'approval.sig').unlink();self.rejected()
 def test_revoked(self):self.pin['status']='revoked';self.sign();self.rejected()
 def test_expired(self):self.data['expires_at']='2000-01-01T00:00:00+00:00';self.sign();self.rejected()
 def test_wrong_site(self):self.data['site_id']='other';self.sign();self.rejected()
 def test_wrong_set(self):self.data['set_id']='other';self.sign();self.rejected()
 def test_stale(self):self.pin['minimum_sequence']=2;self.sign();self.rejected()
 def test_unknown_key(self):self.pin['public_key_sha256']='0'*64;self.sign();self.rejected()
 def test_changed_anchor(self):(self.bundle/'anchor.json').write_text('{}');self.rejected()
 def test_changed_bootstrap(self):(self.bundle/'bootstrap/verify.php').write_text('changed');self.rejected()
 def test_extra_bootstrap(self):(self.bundle/'bootstrap/extra.php').write_text('extra');self.rejected()
 def test_bootstrap_symlink(self):
  p=self.bundle/'bootstrap/verify.php';p.unlink();p.symlink_to(self.trust/'public.pem');self.rejected()
if __name__=='__main__':unittest.main()
