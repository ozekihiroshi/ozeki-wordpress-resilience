import importlib.util,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
s=importlib.util.spec_from_file_location('observer',Path(__file__).with_name('watchdog-observer.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ObserverTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.cfg=dict(state=self.tmp.name,monitor_id='test-watchdog',stale_after_seconds=5,ssh={})
  self.now=datetime.now(timezone.utc);self.events=[]
  self.h=dict(format='owr-monitor-heartbeat-v1',monitor_id='test-watchdog',completed_at=self.now.isoformat(),undelivered=0,open_incidents=0)
 def transport(self,c,p):return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='test-watchdog',status='present',heartbeat=self.h)
 def tick(self,seconds=0,transport=None):return m.observe(self.cfg,now=self.now+timedelta(seconds=seconds),transport=transport or self.transport,sender=self.events.append)
 def test_replay_not_fresh(self):
  self.tick();r=self.tick(6);self.assertEqual(r['reachability']['active'],[]);self.assertIn('monitor_stopped',r['watchdog']['active'])
 def test_nonce_mismatch(self):
  def bad(c,p):r=self.transport(c,p);r['nonce']='0'*32;return r
  self.assertFalse(self.tick(transport=bad)['reachable'])
 def test_rollback(self):
  self.tick();self.h=dict(self.h,completed_at=(self.now-timedelta(seconds=1)).isoformat());self.assertIn('heartbeat_invalid',self.tick(1)['watchdog']['active'])
 def test_same_time_mutation(self):
  self.tick();self.h=dict(self.h,undelivered=1);self.assertIn('heartbeat_invalid',self.tick(1)['watchdog']['active'])
 def test_future(self):
  self.h=dict(self.h,completed_at=(self.now+timedelta(seconds=30)).isoformat());self.assertIn('heartbeat_invalid',self.tick()['watchdog']['active'])
 def test_invalid_survives_disconnect(self):
  self.tick();self.h={};self.tick(1)
  def fail(c,p):raise OSError('down')
  self.assertIn('heartbeat_invalid',self.tick(2,fail)['watchdog']['active'])
 def test_clock_rollback(self):
  self.tick(2)
  with self.assertRaises(ValueError):self.tick(1)
 def test_endpoint_rejects_extra_fields(self):
  with self.assertRaises(ValueError):m.endpoint({},dict(format='owr-watchdog-probe-v1',nonce='a'*32,path='/etc/passwd'))
 def test_independent_dispatch(self):
  example=Path(__file__).with_name('observer.example.json')
  if not example.exists():example=Path(__file__).resolve().parents[1]/'examples/watchdog-observer/observer.example.json'
  config=json.loads(example.read_text())['alerts']
  config['source_outbox']=str(Path(self.tmp.name)/'alerts.sqlite');config['state']=str(Path(self.tmp.name)/'delivery')
  self.cfg['alerts']=config
  sent=[]
  class Provider:
   def send(self,event):sent.append(event);return {}
  def tick(n):return m.observe(self.cfg,now=self.now+timedelta(seconds=n),transport=self.transport,factory=lambda c:Provider())
  tick(0);r=tick(6)
  self.assertFalse(r['delivery_failed']);self.assertEqual(len(sent),1)
  tick(7);self.assertEqual(len(sent),1)
if __name__=='__main__':unittest.main()
