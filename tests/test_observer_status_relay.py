import importlib.util,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('relay',ROOT/'tools/observer-status-relay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RelayTest(unittest.TestCase):
 def test_retention_binding_and_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);c=dict(site_id='site',monitor_id='source',status_file=str(p/'report'),transfer_health=str(p/'health'),lock_file=str(p/'pull'),loop_lock=str(p/'loop'))
   now=datetime.now(timezone.utc)
   report=dict(format='owr-observer-status-v1',site_id='site',monitor_id='source',observed_at=now.isoformat(),simulated=True,targets={k:dict(last_seen=None,active=[],pending=0,observation='missing') for k in ('watchdog','reachability')},delivery=dict(state='unknown',pending=0),history=[])
   def send(c,q):return dict(nonce=q['nonce'],report=report)
   self.assertEqual(m.tick(c,send)['state'],'ok');original=(p/'report').read_bytes()
   def fail(c,q):raise OSError('secret URL must not be exposed')
   self.assertEqual(m.tick(c,fail)['state'],'transfer_failed');self.assertEqual(original,(p/'report').read_bytes());self.assertNotIn('secret',(p/'health').read_text())
   report['monitor_id']='other';self.assertEqual(m.tick(c,send)['state'],'transfer_failed');self.assertEqual(original,(p/'report').read_bytes())
   # Wrong monitor rejected on first acquisition too.
   c2=dict(c,status_file=str(p/'new'));self.assertEqual(m.tick(c2,send)['state'],'transfer_failed');self.assertFalse((p/'new').exists())
   report['monitor_id']='source';report['observed_at']=(now-timedelta(seconds=1)).isoformat();self.assertEqual(m.tick(c,send)['state'],'transfer_failed');self.assertEqual(original,(p/'report').read_bytes())
   report['observed_at']=(now+timedelta(hours=1)).isoformat();self.assertEqual(m.tick(c,send)['state'],'transfer_failed');self.assertEqual(original,(p/'report').read_bytes())
   report['observed_at']=now.isoformat();self.assertEqual(m.tick(c,send)['state'],'ok')
   report['observed_at']=(now-timedelta(seconds=310)).isoformat();self.assertEqual(m.tick(c2,send)['state'],'source_stale')
 def test_path_alias(self):
  with tempfile.TemporaryDirectory() as d:
   c=dict(status_file=d+'/same',transfer_health=d+'/same',lock_file=d+'/pull',loop_lock=d+'/loop')
   with self.assertRaises(ValueError):m.tick(c)
if __name__=='__main__':unittest.main()
