import datetime as dt
import json
import unittest
import test_first_site_daily as fixture
from test_first_capture_entry import Entry, Backend, e
class AdmittedDaily(Entry):
 def setUp(self):
  super().setUp();self.remote=fixture.Daily();self.remote.setUp();self.coordinator=fixture.d.Coordinator(self.root/'daily')
 def tearDown(self):self.remote.tearDown();super().tearDown()
 def tick_daily(self,b=None):return self.coordinator.tick_admitted(self.now,admission=self.paths,backend=b or Backend(),adapter_factory=self.remote.adapter,preflight=lambda:None)
 def test_daily_success_pending_duplicate(self):
  r=self.tick_daily();self.assertEqual(r['state'],'awaiting_approval');self.assertEqual(self.remote.puts,2)
  b=Backend();b.preflight=lambda c:self.fail('duplicate capture');self.assertEqual(self.tick_daily(b),r);self.assertEqual(self.remote.puts,2)
  status=self.coordinator.status(self.now)['runs'][0];self.assertTrue(status['storage_complete']);self.assertEqual(status['approval_state'],'pending');self.assertFalse(status['restore_allowed'])
 def test_daily_bad_admission_zero_capture_and_put(self):
  self.change('review',{});b=Backend();b.preflight=lambda c:self.fail('must not start')
  self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertEqual(self.remote.puts,0);self.assertIsNone(b.token)
  self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertEqual(self.remote.puts,0)
 def test_daily_late_rejection_zero_put(self):
  b=Backend();b.preflight=lambda c:self.change('review',{})
  self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertIsNone(b.token);self.assertEqual(self.remote.puts,0)
 def test_daily_release_failure_zero_put(self):
  b=Backend();b.fail='release';self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertEqual(self.remote.puts,0)
 def test_daily_evidence_changed_during_capture_zero_put(self):
  b=Backend();release=b.release
  def changed(token):self.change('review',{});return release(token)
  b.release=changed
  self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertTrue(b.released);self.assertEqual(self.remote.puts,0)
 def test_daily_storage_preflight_change_no_put(self):
  row=self.coordinator.tick_admitted(self.now,admission=self.paths,backend=Backend(),adapter_factory=self.remote.adapter,preflight=lambda:self.change('review',{}))
  self.assertEqual(row['state'],'unknown');self.assertEqual(self.remote.puts,0)
 def test_daily_uncertain_put_no_retry(self):
  self.remote.fail=True;self.assertEqual(self.tick_daily()['state'],'unknown');self.assertEqual(self.remote.puts,1)
  self.assertEqual(self.tick_daily()['state'],'unknown');self.assertEqual(self.remote.puts,1)
for name in Entry.__dict__:
 if name.startswith('test_'):setattr(AdmittedDaily,name,None)
del Entry
if __name__=='__main__':unittest.main()
