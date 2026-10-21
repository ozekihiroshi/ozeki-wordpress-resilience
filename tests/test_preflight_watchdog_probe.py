import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('probe',ROOT/'tools/preflight-watchdog-probe.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Probe(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.at=datetime.now(timezone.utc).isoformat()
  self.c=dict(site_id='site',config_sha256='a'*64,monitor_id='preflight',report_file=str(self.root/'report'),health_file=str(self.root/'health'))
  self.q=dict(format='owr-watchdog-probe-v1',nonce='a'*32)
  self.r=dict(format='owr-preflight-admin-v1',site_id='site',config_sha256='a'*64,attempted_at=self.at,result=dict(production_ready=False,state='needs_configuration',host_observation=dict(state='validated_report',unverified=['writers']),issues=[]))
  self.h=dict(format='owr-preflight-transfer-v1',site_id='site',config_sha256='a'*64,state='ok',attempted_at=self.at,report_at=self.at)
 def tearDown(self):self.tmp.cleanup()
 def probe(self):
  Path(self.c['report_file']).write_text(json.dumps(self.r));Path(self.c['health_file']).write_text(json.dumps(self.h));return m.endpoint(self.c,self.q)
 def test_preserves_inspection_time(self):
  old=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();self.r['attempted_at']=old;self.h['report_at']=old;self.h['state']='source_stale';self.assertEqual(self.probe()['heartbeat']['completed_at'],old)
 def test_receiver_failure(self):
  self.h['state']='transfer_failed';self.assertEqual(self.probe()['status'],'invalid')
 def test_mismatched_pair(self):
  self.h['report_at']='wrong';self.assertEqual(self.probe()['status'],'invalid')
 def test_wrong_profile(self):
  self.r['config_sha256']='b'*64;self.assertEqual(self.probe()['status'],'invalid')
 def test_missing(self):self.assertEqual(m.endpoint(self.c,self.q)['status'],'missing')
 def test_invalid_nonce(self):
  self.q['nonce']='wrong'
  with self.assertRaises(ValueError):m.endpoint(self.c,self.q)
 def test_publication_window_keeps_committed_time(self):
  old=(datetime.now(timezone.utc)-timedelta(seconds=20)).isoformat();self.h['report_at']=old
  self.assertEqual(self.probe()['heartbeat']['completed_at'],old)
 def test_stalled_health_cannot_refresh_progress(self):
  old=(datetime.now(timezone.utc)-timedelta(minutes=6)).isoformat();self.h['report_at']=old
  self.assertEqual(self.probe()['heartbeat']['completed_at'],old)
  self.r['attempted_at']=datetime.now(timezone.utc).isoformat()
  self.assertEqual(self.probe()['heartbeat']['completed_at'],old)
 def test_health_ahead_of_report_rejected(self):
  self.r['attempted_at']=(datetime.now(timezone.utc)-timedelta(seconds=20)).isoformat()
  self.assertEqual(self.probe()['status'],'invalid')
 def test_no_private_fields(self):
  self.r['secret']='never-send';self.assertNotIn('never-send',json.dumps(self.probe()))
if __name__=='__main__':unittest.main()
