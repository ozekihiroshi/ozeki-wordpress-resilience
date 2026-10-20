import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('probe',Path(__file__).with_name('daily-watchdog-probe.py'))
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
class ProbeTests(unittest.TestCase):
    def test_fixed_scope_and_original_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'report.json'
            config=dict(monitor_id='daily-source',site_id='test-site',report_file=str(p))
            packet=dict(format='owr-watchdog-probe-v1',nonce='a'*32)
            self.assertEqual(probe.endpoint(config,packet)['status'],'missing')
            value=dict(format='owr-daily-admin-v1',site_id='test-site',observed_at='2020-01-01T00:00:00+00:00',
                       missing_due_slot=False,runs=[],attempts=[])
            p.write_text(json.dumps(value));before=p.read_bytes()
            r=probe.endpoint(config,packet)
            self.assertEqual(r['heartbeat']['completed_at'],value['observed_at'])
            self.assertEqual(r['nonce'],packet['nonce'])
            self.assertEqual(p.read_bytes(),before)
            for key,invalid in [('site_id','wrong'),('observed_at','2999-01-01T00:00:00+00:00')]:
                p.write_text(json.dumps({**value,key:invalid}))
                self.assertEqual(probe.endpoint(config,packet)['status'],'invalid')
            for invalid in [{**packet,'path':'/etc/passwd'},{**packet,'nonce':'bad'}]:
                with self.assertRaises(ValueError):probe.endpoint(config,invalid)
if __name__=='__main__': unittest.main()
