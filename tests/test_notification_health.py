import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
d=load('notification-dispatch-lab')
runtime=load('monitor-runtime-lab')


class HealthTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.source=self.root/'source.sqlite'
        self.event=dict(event_id='a'*64,site='lab',domain='daily',kind='backup_missing',subject='day',transition='opened',observed_at='2026-10-19T00:00:00+00:00')
        with sqlite3.connect(self.source) as db:
            db.execute('CREATE TABLE outbox(payload TEXT)');db.execute('INSERT INTO outbox VALUES(?)',(json.dumps(self.event),))
        self.config=dict(source_outbox=str(self.source),state=str(self.root/'delivery'),channels=[dict(id='mail',provider=dict(transport='smtp_test')),dict(id='push',provider=dict(transport='pushover'),kinds=['backup_missing'])],health=dict(monitor_id='delivery-lab',backlog_seconds=300,ack_seconds=300))
        self.mail=MagicMock();self.mail.send.return_value={}
        self.push=MagicMock();self.push.send.return_value={'receipt':'r'*30};self.push.poll.return_value=dict(acknowledged=0,expired=0)
        self.factory=lambda c:self.push if c['transport']=='pushover' else self.mail
        self.events=[]
        self.watch=dict(monitor_id='delivery-lab',heartbeat_file=str(self.root/'delivery/delivery-heartbeat.json'),watchdog_state=str(self.root/'watch'),stale_after_seconds=900)
    def tick(self,now=1000):
        d.run(self.config,now=now,factory=self.factory)
        return json.loads((self.root/'delivery/delivery-health.json').read_text())
    def kinds(self,report):return {p['kind'] for p in report['problems']}
    def watch_tick(self,now):
        return runtime.run_watchdog(self.watch,datetime.fromtimestamp(now,timezone.utc),sender=self.events.append)

    def test_unknown_alerts_independent_watchdog_once(self):
        self.mail.send.side_effect=OSError('secret')
        report=self.tick()
        self.assertIn('delivery_unknown',self.kinds(report))
        self.assertNotIn('secret',json.dumps(report))
        self.assertIn('notification_delivery_failed',self.watch_tick(1000)['active'])
        self.watch_tick(1001);self.assertEqual(len(self.events),1)
        self.push.send.assert_called_once()
    def test_empty_queue_bad_configuration_detected(self):
        with sqlite3.connect(self.source) as db:db.execute('DELETE FROM outbox')
        self.factory=lambda c:(_ for _ in ()).throw(ValueError('secret'))
        self.assertEqual(self.kinds(self.tick()),{'channel_configuration_failed'})
    def test_backlog_boundary_and_recovery(self):
        self.mail.send.side_effect=d.push.DeliveryError('retry')
        self.assertNotIn('delivery_backlog',self.kinds(self.tick()))
        self.assertNotIn('delivery_backlog',self.kinds(self.tick(1299)))
        self.assertIn('delivery_backlog',self.kinds(self.tick(1300)))
        self.watch_tick(1300)
        self.mail.send.side_effect=None
        self.push.poll.return_value=dict(acknowledged=1,expired=0)
        self.assertTrue(self.tick(1500)['healthy'])
        self.assertEqual(self.watch_tick(1500)['active'],[])
        self.assertEqual(self.events[-1]['transition'],'resolved')
    def test_waiting_ack_deadline_and_ack_recovery(self):
        self.tick()
        self.assertNotIn('ack_overdue',self.kinds(self.tick(1299)))
        self.assertIn('ack_overdue',self.kinds(self.tick(1300)))
        self.push.poll.return_value=dict(acknowledged=1,expired=0)
        self.assertTrue(self.tick(1400)['healthy'])
    def test_expired_ack_and_poll_failure(self):
        self.tick();self.push.poll.side_effect=OSError()
        self.assertIn('receipt_check_failed',self.kinds(self.tick(1060)))
        self.push.poll.side_effect=None;self.push.poll.return_value=dict(acknowledged=0,expired=1)
        self.assertIn('ack_expired',self.kinds(self.tick(1400)))
    def test_resolved_expired_ack_not_permanently_unhealthy(self):
        self.tick();self.push.poll.return_value=dict(acknowledged=0,expired=1);self.tick(1060)
        with sqlite3.connect(self.source) as db:db.execute('INSERT INTO outbox VALUES(?)',(json.dumps(dict(self.event,event_id='b'*64,transition='resolved')),))
        self.assertTrue(self.tick(1120)['healthy'])
    def test_stopped_worker_detected_and_recovery(self):
        self.tick();self.watch_tick(1000)
        self.assertIn('monitor_stopped',self.watch_tick(1900)['active'])
        self.push.poll.return_value=dict(acknowledged=1,expired=0)
        self.tick(1901)
        self.assertEqual(self.watch_tick(1901)['active'],[])
    def test_source_failure_does_not_refresh_heartbeat(self):
        self.tick();path=self.root/'delivery/delivery-heartbeat.json';before=path.read_bytes()
        self.source.unlink()
        with self.assertRaises(sqlite3.Error):self.tick(1010)
        self.assertEqual(before,path.read_bytes())
    def test_invalid_report_does_not_clear_watchdog_failure(self):
        self.mail.send.side_effect=OSError();self.tick();self.watch_tick(1000)
        (self.root/'delivery/delivery-heartbeat.json').write_text('{}')
        active=self.watch_tick(1010)['active']
        self.assertIn('heartbeat_invalid',active);self.assertIn('notification_delivery_failed',active)
    def test_watchdog_delivery_failure_is_persisted(self):
        self.mail.send.side_effect=OSError();self.tick()
        def fail(event):raise OSError()
        result=runtime.run_watchdog(self.watch,datetime.fromtimestamp(1000,timezone.utc),sender=fail)
        self.assertEqual(result['undelivered'],1)
        self.assertEqual(self.watch_tick(1001)['undelivered'],0)
    def test_clock_rollback_rejected(self):
        self.tick()
        with self.assertRaises(ValueError):self.tick(999)
    def test_bad_alarm_selection_rejected_before_delivery(self):
        for kinds in ([],['typo'],['backup_missing','backup_missing'],None):
            with self.subTest(kinds=kinds):
                self.config['channels'][1]['kinds']=kinds
                with self.assertRaises(ValueError):self.tick()
        self.push.send.assert_not_called()
    def test_duplicate_id_and_unsupported_provider(self):
        self.config['channels'][1]['id']='mail'
        with self.assertRaises(ValueError):self.tick()
        self.config['channels'][1]['id']='push';self.config['channels'][1]['provider']['transport']='line'
        with self.assertRaises(ValueError):self.tick()
    def test_health_threshold_validation(self):
        self.config['health']['ack_seconds']=0
        with self.assertRaises(ValueError):self.tick()
    def test_restart_keeps_wait_deadline(self):
        self.tick();self.tick(1200)
        self.assertIn('ack_overdue',self.kinds(self.tick(1300)))
    def test_existing_delivery_records_survive_health_upgrade(self):
        self.tick()
        with sqlite3.connect(self.root/'delivery/dispatch.sqlite') as db:
            db.execute('DROP TABLE delivery_health_clock');db.execute('DROP TABLE delivery_health_meta')
        self.tick(1100)
        self.push.send.assert_called_once();self.mail.send.assert_called_once()
    def test_cli_uses_active_health_for_historical_expiry(self):
        self.tick()
        config_file=self.root/'config.json';config_file.write_text(json.dumps(self.config))
        result=[dict(status='accepted',receipt_state='expired',poll_error=0)]
        with patch('sys.argv',['dispatch','--config',str(config_file)]),patch.object(d,'run',return_value=result),patch('builtins.print'):
            self.assertEqual(d.main(),0)
        report_path=self.root/'delivery/delivery-health.json'
        report=json.loads(report_path.read_text());report['healthy']=False;report_path.write_text(json.dumps(report))
        with patch('sys.argv',['dispatch','--config',str(config_file)]),patch.object(d,'run',return_value=result),patch('builtins.print'):
            self.assertEqual(d.main(),1)


if __name__=='__main__':unittest.main()
