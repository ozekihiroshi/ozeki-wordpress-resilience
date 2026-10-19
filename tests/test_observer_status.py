import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('observer-status')
class StatusTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.v=dict(format='owr-observer-status-v1',site_id='site',monitor_id='watchdog',observed_at=datetime.now(timezone.utc).isoformat(),simulated=True,targets={k:dict(last_seen=None,active=[],pending=0,observation='missing') for k in ('reachability','watchdog')},delivery=dict(state='unknown',pending=0),history=[])
  self.c=dict(site_id='site',status_file=str(self.root/'status.json'),lock_file=str(self.root/'lock'))
 def transport(self,c,p):return dict(nonce=p['nonce'],report=self.v)
 def test_allowlist(self):
  self.v['token']='SECRET';self.v['targets']['watchdog']['path']='/secret';self.assertNotIn('SECRET',json.dumps(m.clean(self.v,'site')));self.assertNotIn('/secret',json.dumps(m.clean(self.v,'site')))
 def test_site(self):
  with self.assertRaises(ValueError):m.clean(self.v,'other')
 def test_nonce(self):
  with self.assertRaises(ValueError):m.pull(self.c,lambda c,p:dict(nonce='0',report=self.v))
 def test_preserves_timestamp(self):
  self.assertEqual(m.pull(self.c,self.transport)['observed_at'],self.v['observed_at'])
 def test_rollback(self):
  m.pull(self.c,self.transport);self.v['observed_at']=(datetime.now(timezone.utc)-timedelta(seconds=50)).isoformat()
  with self.assertRaises(ValueError):m.pull(self.c,self.transport)
 def test_same_time_conflict(self):
  m.pull(self.c,self.transport);self.v['delivery']['state']='failed'
  with self.assertRaises(ValueError):m.pull(self.c,self.transport)
 def test_transport_failure_preserves_report(self):
  m.pull(self.c,self.transport);before=Path(self.c['status_file']).read_bytes()
  def fail(c,p):raise OSError()
  with self.assertRaises(OSError):m.pull(self.c,fail)
  self.assertEqual(before,Path(self.c['status_file']).read_bytes())
 def test_future(self):
  self.v['observed_at']='2099-01-01T00:00:00+00:00'
  with self.assertRaises(ValueError):m.clean(self.v,'site')
 def test_negative(self):
  self.v['delivery']['pending']=-1
  with self.assertRaises(ValueError):m.clean(self.v,'site')
 def test_endpoint_fixed_path(self):
  with self.assertRaises(ValueError):m.endpoint({},dict(site_id='site',nonce='a'*32,path='/etc/passwd'))
 def test_dispatch_failure_published(self):
  observer=load('watchdog-observer')
  cfg=dict(state=str(self.root/'state'),monitor_id='watchdog',stale_after_seconds=5,ssh={},admin_site_id='site',public_status_file=str(self.root/'public.json'),alerts=dict(source_outbox=str(self.root/'alerts.sqlite'),state=str(self.root/'delivery'),channels=[]))
  def probe(c,p):return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='watchdog',status='missing',heartbeat=None)
  observer.observe(cfg,transport=probe)
  report=json.loads((self.root/'public.json').read_text());self.assertEqual(report['delivery']['state'],'failed');self.assertEqual(report['targets']['watchdog']['observation'],'missing')
 def test_disappeared_completion_not_confirmed(self):
  observer=load('watchdog-observer')
  cfg=dict(state=str(self.root/'state'),monitor_id='watchdog',stale_after_seconds=5,ssh={},admin_site_id='site',public_status_file=str(self.root/'public.json'))
  def probe(c,p):return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='watchdog',status='present',heartbeat=dict(format='owr-monitor-heartbeat-v1',monitor_id='watchdog',completed_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat(),undelivered=0,open_incidents=0))
  observer.observe(cfg,transport=probe,sender=lambda e:None)
  def missing(c,p):return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],monitor_id='watchdog',status='missing',heartbeat=None)
  observer.observe(cfg,transport=missing,sender=lambda e:None)
  report=json.loads((self.root/'public.json').read_text());self.assertEqual(report['targets']['watchdog']['observation'],'missing');self.assertIsNotNone(report['targets']['watchdog']['last_seen'])
if __name__=='__main__':unittest.main()
