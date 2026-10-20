"""Regression: a fresh completion during a slow SSH exchange is not future data."""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import unittest
spec=importlib.util.spec_from_file_location('observer',Path(__file__).with_name('watchdog-observer.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class SlowProbe(unittest.TestCase):
    def test_real_elapsed_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg=dict(state=tmp,monitor_id='slow-probe',stale_after_seconds=30,ssh={})
            def transport(c,p):
                time.sleep(6)
                return dict(format='owr-watchdog-probe-result-v1',nonce=p['nonce'],
                    monitor_id='slow-probe',status='present',
                    heartbeat=dict(format='owr-monitor-heartbeat-v1',monitor_id='slow-probe',
                        completed_at=datetime.now(timezone.utc).isoformat(),undelivered=0,open_incidents=0))
            events=[]
            result=m.observe(cfg,transport=transport,sender=events.append)
            self.assertEqual(result['watchdog']['active'],[])
            self.assertEqual(events,[])
if __name__=='__main__':unittest.main()
