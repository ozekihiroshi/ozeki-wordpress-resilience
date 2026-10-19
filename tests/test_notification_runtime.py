import importlib.util,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch,MagicMock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runtime',ROOT/'tools/notification-runtime.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.now=datetime.now(timezone.utc)
        self.relay=dict(monitor_id='site-relay',heartbeat_file=str(self.root/'relay.json'),cycle_lock=str(self.root/'relay.lock'),transfer_config=str(self.root/'transfer.json'))
        self.worker=dict(monitor_id='site-worker',heartbeat_file=str(self.root/'worker.json'),cycle_lock=str(self.root/'worker.lock'),stage_config=str(self.root/'stage.json'),publish_config=str(self.root/'publish.json'),delivery_state=str(self.root/'delivery'),requests_dir=str(self.root/'requests'))
        self.config=dict(delivery={},targets=[dict(role=role,monitor_id='site-'+role,heartbeat_file=str(self.root/(role+'.json')),watchdog_state=str(self.root/('watch-'+role)),stale_after_seconds=10) for role in ('relay','worker')])
        self.events=[]
        Path(self.relay['transfer_config']).write_text(json.dumps(dict(relay_monitor_id='site-relay',relay_heartbeat_file=self.relay['heartbeat_file'])))
    def beat(self,role,offset=0,errors=None):r.heartbeat(self.relay if role=='relay' else self.worker,errors or [],self.now+timedelta(seconds=offset))
    def tick(self,offset=0,sender=None):return r.watchdog(self.config,self.now+timedelta(seconds=offset),sender or self.events.append)
    def test_startup_grace_then_both_missing(self):
        self.assertFalse(self.tick()['relay']['active']);result=self.tick(10)
        self.assertEqual(result['relay']['active'],['monitor_stopped']);self.assertEqual(result['worker']['active'],['monitor_stopped'])
    def test_relay_stopped_worker_live(self):
        self.beat('relay');self.beat('worker');self.tick();self.beat('worker',11);result=self.tick(11)
        self.assertEqual(result['relay']['active'],['monitor_stopped']);self.assertEqual(result['worker']['active'],[])
    def test_worker_stopped_relay_live(self):
        self.beat('relay');self.beat('worker');self.tick();self.beat('relay',11);result=self.tick(11)
        self.assertEqual(result['worker']['active'],['monitor_stopped']);self.assertEqual(result['relay']['active'],[])
    def test_persistent_dedup_and_resolution(self):
        self.tick();self.tick(10);self.tick(11);self.assertEqual(len(self.events),2)
        self.beat('relay',12);self.beat('worker',12);self.tick(12);self.tick(13)
        self.assertEqual(len(self.events),4);self.assertEqual([e['transition'] for e in self.events].count('resolved'),2)
    def test_failed_alert_delivery_retried_from_outbox(self):
        self.tick()
        def fail(e):raise OSError()
        self.assertEqual(self.tick(10,fail)['relay']['undelivered'],1)
        self.tick(11);self.assertEqual(len(self.events),2)
    def test_worker_errors_are_distinct_from_stopping(self):
        self.beat('relay');self.beat('worker',errors=['intake']);result=self.tick()
        self.assertEqual(result['worker']['active'],['notification_delivery_failed'])
    def test_malformed_heartbeat_does_not_resolve_stop(self):
        self.tick();self.tick(10);Path(self.worker['heartbeat_file']).write_text('{}');result=self.tick(11)
        self.assertIn('monitor_stopped',result['worker']['active']);self.assertIn('heartbeat_invalid',result['worker']['active'])
    def test_watchdog_clock_rollback_not_refreshed(self):
        self.tick(10);self.assertTrue(self.tick(9)['relay']['error'])
    def test_relay_failure_does_not_refresh_heartbeat(self):
        self.beat('relay');before=Path(self.relay['heartbeat_file']).read_bytes()
        with patch.object(r.transfer,'exchange',side_effect=OSError()):
            with self.assertRaises(OSError):r.cycle('relay',self.relay)
        self.assertEqual(before,Path(self.relay['heartbeat_file']).read_bytes())
    def test_relay_success_has_completion_time(self):
        with patch.object(r.transfer,'exchange',return_value=dict(stored=0,report_received=True)):
            self.assertTrue(r.cycle('relay',self.relay,now=self.now)['healthy'])
        self.assertEqual(json.loads(Path(self.relay['heartbeat_file']).read_text())['completed_at'],self.now.isoformat())
    def test_overlapping_cycle_refused(self):
        with open(self.relay['cycle_lock'],'a') as lock:
            r.fcntl.flock(lock,r.fcntl.LOCK_EX|r.fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):r.cycle('relay',self.relay)
    def test_sender_heartbeat_cannot_move_backwards(self):
        self.beat('relay')
        with self.assertRaises(ValueError):self.beat('relay',-1)
    def test_remote_heartbeat_replay_preserves_timestamp(self):
        config=dict(relay_monitor_id='site-relay',relay_heartbeat_file=str(self.root/'remote.json'))
        self.beat('relay');value=json.loads(Path(self.relay['heartbeat_file']).read_text());r.transfer.store_heartbeat(value,config)
        before=Path(config['relay_heartbeat_file']).stat().st_mtime_ns;r.transfer.store_heartbeat(value,config)
        self.assertEqual(before,Path(config['relay_heartbeat_file']).stat().st_mtime_ns)
    def test_remote_heartbeat_invalid_scope_future_and_rollback(self):
        config=dict(relay_monitor_id='site-relay',relay_heartbeat_file=str(self.root/'remote.json'));self.beat('relay');value=json.loads(Path(self.relay['heartbeat_file']).read_text());r.transfer.store_heartbeat(value,config)
        for changes in [dict(monitor_id='site-worker'),dict(completed_at=(self.now+timedelta(days=1)).isoformat()),dict(completed_at=(self.now-timedelta(seconds=1)).isoformat()),dict(undelivered=1)]:
            with self.assertRaises(ValueError):r.transfer.store_heartbeat(dict(value,**changes),config)
    def test_intake_failure_does_not_skip_normal_dispatch(self):
        bridge=MagicMock();bridge.digest.return_value='hash';bridge.dispatch.run.return_value=[];bridge.status.return_value=dict(channels=[])
        config=dict(admin_binding=dict(site_id='site'))
        def read(path,limit):return dict(site_id='site',worker_status=str(self.root/'status.json'))
        with patch.object(r.transfer,'read_file',side_effect=read),patch.object(r.transfer,'stage',side_effect=OSError()),patch.object(r.live,'current',return_value=config),patch.object(r.live,'load',return_value=bridge),patch.object(r.live,'tests'),patch.object(r.transfer,'publish'):
            result=r.cycle('worker',self.worker,now=self.now)
        bridge.dispatch.run.assert_called_once();self.assertFalse(result['healthy']);self.assertEqual(json.loads(Path(self.worker['heartbeat_file']).read_text())['undelivered'],1)
    def test_one_broken_watch_state_does_not_hide_other(self):
        original=r.watch.run_watchdog
        def run(c,**kw):
            if c['monitor_id']=='site-relay':raise OSError()
            return original(c,**kw)
        with patch.object(r.watch,'run_watchdog',side_effect=run):
            self.tick();result=self.tick(10)
        self.assertTrue(result['relay']['error']);self.assertEqual(result['worker']['active'],['monitor_stopped'])
    def test_independent_push_outbox_survives_worker_stop(self):
        self.config.pop('delivery');path=self.root/'alerts.json';self.config['alert_dispatch_config']=str(path)
        path.write_text(json.dumps(dict(source_outbox=str(self.root/'alert-source.sqlite'),state=str(self.root/'alert-delivery'),channels=[dict(id='independent-push',provider=dict(transport='pushover',credentials_file='/not-used'))])))
        provider=MagicMock();provider.send.return_value={}
        r.watchdog(self.config,self.now,alert_factory=lambda c:provider)
        result=r.watchdog(self.config,self.now+timedelta(seconds=10),alert_factory=lambda c:provider)
        self.assertEqual(provider.send.call_count,2);self.assertEqual(result['alerts']['undelivered'],0);self.assertFalse(Path(self.worker['delivery_state']).exists())
    def test_independent_push_failure_remains_visible(self):
        path=self.root/'alerts.json';self.config['alert_dispatch_config']=str(path)
        path.write_text(json.dumps(dict(source_outbox=str(self.root/'alert-source.sqlite'),state=str(self.root/'alert-delivery'),channels=[dict(id='push',provider=dict(transport='pushover',credentials_file='/not-used'))])))
        provider=MagicMock();provider.send.side_effect=OSError()
        r.watchdog(self.config,self.now,alert_factory=lambda c:provider)
        result=r.watchdog(self.config,self.now+timedelta(seconds=10),alert_factory=lambda c:provider)
        self.assertGreater(result['alerts']['undelivered'],0)
        r.watchdog(self.config,self.now+timedelta(seconds=11),alert_factory=lambda c:provider);self.assertEqual(provider.send.call_count,2)

if __name__=='__main__':unittest.main()
