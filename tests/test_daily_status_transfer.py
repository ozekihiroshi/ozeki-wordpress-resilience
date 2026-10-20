import importlib.util,json,tempfile,unittest,time
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
r=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('wire',r/'tools/daily-status-transfer.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Transfer(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
        self.c=dict(site_id='site',status_file=str(p/'status'),transfer_health=str(p/'health'),report_file=str(p/'source'),producer_health=str(p/'producer'),state=str(p/'missing'))
        self.v=dict(format='owr-daily-admin-v1',site_id='site',observed_at=m.now(),missing_due_slot=False,runs=[],attempts=[])
    def tearDown(self):self.tmp.cleanup()
    def send(self,c,q):return dict(site_id='site',nonce=q['nonce'],report=self.v,producer_state='ok')
    def test_success_and_repeat(self):
        self.assertTrue(m.relay(self.c,self.send));self.assertTrue(m.relay(self.c,self.send))
    def test_failure_preserves_report(self):
        m.relay(self.c,self.send);before=Path(self.c['status_file']).read_bytes()
        def fail(c,q):raise TimeoutError()
        self.assertFalse(m.relay(self.c,fail))
        self.assertEqual(before,Path(self.c['status_file']).read_bytes())
        self.assertEqual(json.loads(Path(self.c['transfer_health']).read_bytes())['state'],'transfer_failed')
    def test_nonce_and_scope(self):
        for k,v in [('nonce','wrong'),('site_id','other')]:
            def bad(c,q):return dict(self.send(c,q),**{k:v})
            self.assertFalse(m.relay(self.c,bad))
            self.assertFalse(Path(self.c['status_file']).exists())
    def test_rollback_and_same_time_mutation(self):
        m.relay(self.c,self.send)
        self.v['missing_due_slot']=True
        self.assertFalse(m.relay(self.c,self.send))
        self.v['observed_at']='2000-01-01T00:00:00Z'
        self.assertFalse(m.relay(self.c,self.send))
    def test_source_stale_and_failed(self):
        self.v['observed_at']='2000-01-01T00:00:00Z'
        self.assertFalse(m.relay(self.c,self.send))
        self.assertEqual(json.loads(Path(self.c['transfer_health']).read_bytes())['state'],'source_stale')
        def failed(c,q):return dict(self.send(c,q),producer_state='failed')
        self.assertFalse(m.relay(self.c,failed))
        self.assertEqual(json.loads(Path(self.c['transfer_health']).read_bytes())['state'],'source_failed')
    def test_strip_secret_and_reject_future(self):
        self.v['secret']='DO-NOT-TRANSFER'
        self.assertTrue(m.relay(self.c,self.send))
        self.assertNotIn(b'DO-NOT-TRANSFER',Path(self.c['status_file']).read_bytes())
        self.v['observed_at']='2099-01-01T00:00:00Z'
        self.assertFalse(m.relay(self.c,self.send))
    def test_publish_failure_retains_previous(self):
        p=Path(self.c['report_file']);p.write_text('previous')
        self.assertFalse(m.publish(self.c));self.assertEqual(p.read_text(),'previous')
    def test_duplicate_keys_and_symlink(self):
        with self.assertRaises(ValueError):m.t.decode(b'{"a":1,"a":2}',30)
        p=Path(self.c['status_file']);p.symlink_to(self.c['report_file'])
        Path(self.c['report_file']).write_text(json.dumps(self.v))
        self.assertFalse(m.relay(self.c,self.send))
    def test_output_cannot_overwrite_source_or_health(self):
        c=dict(self.c,report_file=self.c['state']+'/daily.sqlite')
        with self.assertRaises(ValueError):m.publish(c)
        self.assertFalse(Path(c['report_file']).exists())
        with self.assertRaises(ValueError):m.relay(dict(self.c,transfer_health=self.c['status_file']),self.send)
if __name__=='__main__':unittest.main()
