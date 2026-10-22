import importlib.util,json,datetime as dt,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('update',Path(__file__).resolve().parents[1]/'tools/update-current-recovery-trust.py');u=importlib.util.module_from_spec(s);s.loader.exec_module(u)
@unittest.skipUnless(hasattr(os,'geteuid') and os.geteuid()==0,'dedicated root lab required')
class Update(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/run',prefix='owr-update-');self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.path=self.root/'current.json';self.c=self.root/'candidate.json'
  p=patch.object(u.g,'AUTHORITY',self.path);p.start();self.addCleanup(p.stop)
  now=dt.datetime.now(dt.timezone.utc)
  self.x={'format':'owr-current-recovery-trust-v1','revision':1,'issued_at':(now-dt.timedelta(seconds=1)).isoformat(),'expires_at':(now+dt.timedelta(hours=1)).isoformat(),'revoked_key_sha256':[],'sets':[{'site_id':'site','set_id':'set','status':'active','minimum_sequence':1,'public_key_sha256':'a'*64,'approved_document_sha256':'b'*64}]}
  self.put();self.run_update('absent');self.old=self.path.read_bytes();self.x['revision']=2
 def put(self):self.c.write_text(json.dumps(self.x));return u.sha(self.c.read_bytes())
 def run_update(self,expected=None,apply=True):return u.deploy(self.c,expected or u.sha(self.old),u.sha(self.c.read_bytes()),apply)
 def reject(self):
  self.put()
  with self.assertRaises((ValueError,OSError)):self.run_update()
  self.assertEqual(self.path.read_bytes(),self.old)
 def test_success_readback(self):self.put();self.assertTrue(self.run_update()['applied']);self.assertEqual(u.read_current(),self.c.read_bytes())
 def test_dry_run(self):self.put();self.assertFalse(self.run_update(apply=False)['applied']);self.assertEqual(self.path.read_bytes(),self.old)
 def test_old_revision(self):self.x['revision']=1;self.reject()
 def test_stale_expected(self):
  self.put();self.run_update()
  with self.assertRaises(ValueError):self.run_update()
 def test_review_hash_changed(self):
  h=self.put();self.c.write_text('{}')
  with self.assertRaises(ValueError):u.deploy(self.c,u.sha(self.old),h,True)
 def test_sequence_rollback(self):self.x['sets'][0]['minimum_sequence']=0;self.reject()
 def test_changed_key_without_generation(self):self.x['sets'][0]['public_key_sha256']='c'*64;self.reject()
 def test_missing_tombstone(self):self.x['sets']=[];self.reject()
 def test_expired(self):self.x['expires_at']=self.x['issued_at'];self.reject()
 def test_revocation_sticky(self):
  self.x['sets'][0]['status']='revoked';self.x['revoked_key_sha256']=['a'*64];self.put();self.run_update();self.old=self.path.read_bytes();self.x['revision']=3;self.x['revoked_key_sha256']=[];self.reject()
 def test_revoked_set_sticky(self):
  self.x['sets'][0]['status']='revoked';self.put();self.run_update();self.old=self.path.read_bytes();self.x['revision']=3;self.x['sets'][0]['status']='active';self.reject()
 def test_lock_contention(self):
  self.put()
  with self.path.with_suffix('.lock').open('r+b') as f:
   u.fcntl.flock(f,u.fcntl.LOCK_EX|u.fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.run_update()
  self.assertEqual(self.path.read_bytes(),self.old)
 def test_valid_sequence_decrease(self):
  self.x['sets'][0]['minimum_sequence']=2;self.put();self.run_update();self.old=self.path.read_bytes();self.x['revision']=3;self.x['sets'][0]['minimum_sequence']=1;self.reject()
 def test_expired_current_can_be_refreshed(self):
  old=json.loads(self.old);now=dt.datetime.now(dt.timezone.utc)
  old['issued_at']=(now-dt.timedelta(hours=2)).isoformat();old['expires_at']=(now-dt.timedelta(hours=1)).isoformat()
  self.path.write_text(json.dumps(old));self.old=self.path.read_bytes();self.put();self.assertTrue(self.run_update()['applied'])
 def test_staging_sync_failure_keeps_old(self):
  self.put()
  with patch.object(u.os,'fsync',side_effect=OSError('simulated')),self.assertRaises(OSError):self.run_update()
  self.assertEqual(self.path.read_bytes(),self.old);self.assertEqual(list(self.root.glob('.current-*')),[])
 def test_deployed_revocation_blocks_recovery_check(self):
  trust=self.root/'bundle';trust.mkdir();(trust/'public.pem').write_text('generated-public-fixture')
  doc=trust/'approved.json';doc.write_text(json.dumps({'sequence':2}))
  e=self.x['sets'][0];e.update(minimum_sequence=2,public_key_sha256=u.g.digest(trust/'public.pem'),approved_document_sha256=u.g.digest(doc))
  self.put();self.run_update();self.old=self.path.read_bytes()
  self.assertEqual(u.g.current(trust,doc,'site','set')['revision'],2)
  self.x['revision']=3;e['status']='revoked';self.put();self.run_update()
  with self.assertRaises(ValueError):u.g.current(trust,doc,'site','set')
 def test_replace_failure_keeps_old(self):
  self.put()
  with patch.object(u.os,'replace',side_effect=OSError('simulated')),self.assertRaises(OSError):self.run_update()
  self.assertEqual(self.path.read_bytes(),self.old);self.assertEqual(list(self.root.glob('.current-*')),[])
 def test_post_replace_sync_failure_inspect_new(self):
  self.put();real=u.os.fsync;calls=[]
  def fail(fd):
   calls.append(fd)
   if len(calls)==2:raise OSError('directory sync unknown')
   real(fd)
  with patch.object(u.os,'fsync',side_effect=fail),self.assertRaises(OSError):self.run_update()
  self.assertEqual(u.read_current(),self.c.read_bytes())
  with self.assertRaises(ValueError):self.run_update()
 def test_corrupt_current_not_bootstrap(self):
  self.path.write_text('{');self.put()
  with self.assertRaises(ValueError):self.run_update('absent')
 def test_symlink_current(self):
  self.path.rename(self.root/'old');self.path.symlink_to(self.root/'old');self.put()
  with self.assertRaises(OSError):self.run_update()
if __name__=='__main__':unittest.main()
