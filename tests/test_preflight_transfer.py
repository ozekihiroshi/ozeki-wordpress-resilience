import importlib.util,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('transfer',ROOT/'tools/preflight-transfer.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TransferTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.c=dict(site_id='site',config_sha256='a'*64,report_file=str(self.root/'report'),health_file=str(self.root/'health'))
  self.v=dict(format='owr-preflight-admin-v1',site_id='site',config_sha256='a'*64,attempted_at=datetime.now(timezone.utc).isoformat(),result=dict(production_ready=False,state='needs_configuration',host_observation=dict(state='validated_report',unverified=['writers']),issues=[]))
 def tearDown(self):self.tmp.cleanup()
 def wire(self,c,q):return dict(nonce=q['nonce'],report=self.v,source_state='ok')
 def test_transfer_preserves_source_time(self):
  r=m.pull(self.c,self.wire);self.assertEqual(r['state'],'ok');self.assertEqual(r['report_at'],self.v['attempted_at'])
 def test_stale(self):
  self.v['attempted_at']=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();self.assertEqual(m.pull(self.c,self.wire)['state'],'source_stale')
 def test_failure_preserves(self):
  m.pull(self.c,self.wire);old=Path(self.c['report_file']).read_bytes()
  def fail(*args):raise OSError()
  self.assertEqual(m.pull(self.c,fail)['state'],'transfer_failed');self.assertEqual(Path(self.c['report_file']).read_bytes(),old)
 def test_rollback(self):
  m.pull(self.c,self.wire);self.v['attempted_at']=(datetime.now(timezone.utc)-timedelta(seconds=10)).isoformat();self.assertEqual(m.pull(self.c,self.wire)['state'],'transfer_failed')
 def test_nonce(self):
  def wrong(c,q):return dict(nonce='0'*32,report=self.v,source_state='ok')
  self.assertEqual(m.pull(self.c,wrong)['state'],'transfer_failed')
 def test_strip(self):
  self.v['secret']='never';self.v['result']['private']='never';self.assertNotIn('never',json.dumps(m.clean(self.v,self.c)))
 def test_foreign(self):
  self.v['site_id']='other';self.assertEqual(m.pull(self.c,self.wire)['state'],'transfer_failed')
if __name__=='__main__':unittest.main()
