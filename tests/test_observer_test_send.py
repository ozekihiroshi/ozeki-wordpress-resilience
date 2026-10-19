import json,sqlite3,time,unittest,uuid
import test_observer_settings as fixtures
m=fixtures.m

class ObserverTestSendTests(unittest.TestCase):
 receive=fixtures.SettingsTests.receive
 rows=fixtures.SettingsTests.rows
 def setUp(self):
  fixtures.SettingsTests.setUp(self)
  self.receive(fixtures.SettingsTests.req(self));m.apply_pending(self.c)
  self.provider.reset_mock();self.provider.send.return_value={}
 def req(self,**kw):
  v=dict(format='owr-observer-test-request-v1',site_id='site',request_id=str(uuid.uuid4()),created_at=int(time.time()),expected_hash=m.bridge.digest(m.live.current(self.state)),revision=2,revision_token='rev2',channel_id='phone');v.update(kw);return v
 def run_tests(self,**kw):return m.tests(self.c,factory=lambda c:self.provider,**kw)
 def test_success_duplicate_and_fixed_body(self):
  v=self.req();self.receive(v);self.receive(v);before=self.rows()
  self.assertEqual(self.run_tests()[0]['status'],'accepted');self.run_tests();self.provider.send.assert_called_once()
  event=self.provider.send.call_args.args[0];self.assertEqual(event['kind'],'notification_test');self.assertEqual(event['transition'],'resolved');self.assertEqual(before,self.rows())
 def test_revision_expiry_route_and_hash(self):
  for change in [dict(revision=1),dict(revision_token='old'),dict(expected_hash='0'*64),dict(channel_id='missing'),dict(created_at=int(time.time())-301)]:self.receive(self.req(**change))
  self.assertTrue(all(r['status']=='blocked' for r in self.run_tests()));self.provider.send.assert_not_called()
 def test_injection_and_foreign_site(self):
  for change in [dict(body='arbitrary'),dict(recipient='other'),dict(site_id='foreign')]:
   with self.assertRaises(ValueError):self.receive(self.req(**change))
 def test_external_rate_limit(self):
  self.receive(self.req());self.receive(self.req());self.run_tests();r=self.run_tests()
  self.assertEqual([x['status'] for x in r],['blocked','accepted']);self.provider.send.assert_called_once()
 def test_failure_never_retried(self):
  for outcome in ['retry','rejected','unknown']:
   with self.subTest(outcome=outcome):
    self.provider.send.side_effect=m.bridge.dispatch.push.DeliveryError(outcome)
    self.receive(self.req());r=self.run_tests(now=time.time()+60*(['retry','rejected','unknown'].index(outcome)))
    self.assertEqual(r[0]['status'],outcome);calls=self.provider.send.call_count;self.run_tests();self.assertEqual(calls,self.provider.send.call_count)
 def test_unknown_after_crash(self):
  v=self.req();self.receive(v);self.run_tests()
  with sqlite3.connect(self.state/'dispatch.sqlite') as db:db.execute("UPDATE observer_tests SET status='sending'")
  self.assertEqual(self.run_tests()[0]['status'],'unknown');self.provider.send.assert_called_once()
 def test_dispatch_lock_leaves_pending(self):
  import fcntl
  self.receive(self.req())
  with (self.state/'dispatch.lock').open('a') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):self.run_tests()
  self.assertEqual(self.run_tests()[0]['status'],'accepted')
 def test_cutover_blocks_old_request_preserves_results(self):
  self.receive(self.req());self.run_tests();self.receive(self.req())
  self.settings.update(revision=3,revision_token='rev3');self.receive(fixtures.SettingsTests.req(self));m.apply_pending(self.c)
  r=self.run_tests();self.assertEqual([x['status'] for x in r],['blocked','accepted']);self.assertEqual(r[1]['revision'],2);self.provider.send.assert_called_once()
 def test_status_allowlist(self):
  self.receive(self.req());self.run_tests();r=m.status(self.c)['tests'][0]
  self.assertEqual(set(r),{'request_id','channel_id','revision','revision_token','status'})
 def test_one_send_per_cycle_and_disabled_route(self):
  self.settings.update(revision=3,revision_token='rev3')
  self.settings['channels'] += [dict(self.settings['channels'][0],id='second'),dict(self.settings['channels'][0],id='disabled',enabled=False)]
  self.receive(fixtures.SettingsTests.req(self));m.apply_pending(self.c)
  for channel in ['disabled','phone','second']:self.receive(self.req(revision=3,revision_token='rev3',channel_id=channel))
  first=self.run_tests();self.assertEqual(self.provider.send.call_count,1);self.assertEqual(len(first),2)
  self.run_tests();self.assertEqual(self.provider.send.call_count,2)
 def test_public_report_validation(self):
  status=m.load('observer-status')
  self.receive(self.req());self.run_tests()
  # Public serialization contains only fixed result fields, never delivery credentials.
  public=json.dumps(m.status(self.c));self.assertNotIn('credentials_file',public);self.assertNotIn('receipt',public)

if __name__=='__main__':unittest.main()
