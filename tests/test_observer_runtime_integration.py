"""Real observer, watchdog state machine, dispatch and control; fake provider only."""
import json,sqlite3,time,uuid,unittest
from datetime import datetime,timezone,timedelta
import test_observer_settings as fixture

class RuntimeIntegration(unittest.TestCase):
 def setUp(self):
  fixture.SettingsTests.setUp(self)
  self.control=fixture.m;self.observer=fixture.load('watchdog-observer')
  self.receive(fixture.SettingsTests.req(self));self.control.apply_pending(self.c)
  self.cfg=dict(state=str(self.root/'observer'),monitor_id='runtime-lab',stale_after_seconds=5,ssh={},alerts=self.control.live.current(self.state),configuration=self.c,admin_site_id='site',public_status_file=str(self.root/'public.json'))
  self.start=datetime.now(timezone.utc)-timedelta(seconds=10)
  self.h=dict(format='owr-monitor-heartbeat-v1',monitor_id='runtime-lab',completed_at=self.start.isoformat(),undelivered=0,open_incidents=0)
  self.sent=[];self.cancelled=[];self.fail_test=False;self.fail_alarm=False
  parent=self
  class Provider:
   def send(self,event):
    parent.sent.append(event)
    if (event['kind']=='notification_test' and parent.fail_test) or (event['kind']!='notification_test' and parent.fail_alarm):raise OSError('fixture unavailable')
    return {'receipt':'r'*30} if event['transition']=='opened' else {}
   def poll(self,receipt):return dict(acknowledged=False,expired=False)
   def cancel(self,receipt):parent.cancelled.append(receipt)
  self.factory=lambda c:Provider()
  self.tick(self.start)
 receive=fixture.SettingsTests.receive
 rows=fixture.SettingsTests.rows
 def transport(self,c,p):return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='runtime-lab',status='present',heartbeat=self.h)
 def tick(self,now=None):return self.observer.observe(self.cfg,now=now,transport=self.transport,factory=self.factory)
 def report(self):return json.loads((self.root/'public.json').read_text())
 def request(self):
  return dict(format='owr-observer-test-request-v1',site_id='site',request_id=str(uuid.uuid4()),expected_hash=self.control.bridge.digest(self.control.live.current(self.state)),revision=2,revision_token='rev2',channel_id='phone',created_at=int(time.time()))
 def test_alarm_precedes_test_and_recovery_cancels_receipt(self):
  self.receive(self.request());self.tick()
  self.assertEqual([e['kind'] for e in self.sent],['monitor_stopped','notification_test'])
  self.assertEqual(self.report()['configuration']['tests'][0]['status'],'accepted')
  before=self.rows();self.tick();self.assertEqual(before,self.rows());self.assertEqual(len(self.sent),2)
  # Cancellation follows the existing receipt polling schedule; make it due in this fixture.
  with sqlite3.connect(self.state/'dispatch.sqlite') as db:db.execute('UPDATE deliveries SET poll_at=0')
  self.h['completed_at']=datetime.now(timezone.utc).isoformat();self.tick()
  self.assertEqual(self.cancelled,['r'*30]);self.assertEqual(self.report()['targets']['watchdog']['active'],[])
 def test_test_failure_keeps_alarm_receipt_and_no_retry(self):
  self.fail_test=True;self.receive(self.request());self.tick()
  self.assertEqual(self.report()['configuration']['tests'][0]['status'],'unknown')
  self.assertEqual(self.rows()[0][3],'r'*30);self.tick();self.assertEqual(len(self.sent),2)
 def test_alarm_failure_not_hidden_by_test_success(self):
  self.fail_alarm=True;self.receive(self.request());self.tick();r=self.report()
  self.assertEqual(r['delivery']['state'],'failed');self.assertGreater(r['delivery']['pending'],0)
  self.assertEqual(r['configuration']['tests'][0]['status'],'accepted')
 def test_transfer_stopped_does_not_deliver_then_resumes(self):
  directory=self.root/'spool';directory.mkdir();v=self.request();p=directory/(v['request_id']+'.json');p.write_text(json.dumps(v))
  self.tick();self.assertTrue(p.exists());self.assertEqual(self.report()['configuration']['tests'],[])
  self.control.exchange(dict(site_id='site',requests_dir=str(directory),lock_file=str(self.root/'relay.lock')),lambda c,p:self.control.receive(self.c,p))
  self.tick();self.assertFalse(p.exists());self.assertEqual(self.report()['configuration']['tests'][0]['status'],'accepted')
 def test_dispatch_stopped_reports_error_then_drains_once(self):
  import fcntl
  self.receive(self.request())
  with (self.state/'dispatch.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.tick()
  r=self.report();self.assertEqual(r['delivery']['state'],'failed');self.assertTrue(r['configuration']['test_processing_error']);self.assertEqual(self.sent,[])
  self.tick();self.assertFalse(self.report()['configuration']['test_processing_error']);self.assertEqual(len(self.sent),2)
  self.tick();self.assertEqual(len(self.sent),2)
 def test_observer_stopped_does_not_refresh_public_time(self):
  self.receive(self.request());before=(self.root/'public.json').read_bytes()
  # No observe call: accepted inbox must not invent a new public observation/result.
  self.control.status(self.c);self.assertEqual(before,(self.root/'public.json').read_bytes());self.assertEqual(self.sent,[])
 def test_expired_after_worker_stop_not_sent(self):
  v=self.request();v['created_at']-=301;self.receive(v);self.tick()
  self.assertEqual(self.report()['configuration']['tests'][0]['status'],'blocked');self.assertEqual([e['kind'] for e in self.sent],['monitor_stopped'])
 def test_state_pull_stopped_retains_prior_result(self):
  reader=self.root/'wp-report.json';reader.write_bytes((self.root/'public.json').read_bytes());before=reader.read_bytes()
  self.receive(self.request());self.tick();self.assertEqual(reader.read_bytes(),before)
  self.assertEqual(json.loads(reader.read_text())['configuration']['tests'],[])
  self.assertEqual(self.report()['configuration']['tests'][0]['status'],'accepted')

if __name__=='__main__':unittest.main()
