import importlib.util
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import json
from pathlib import Path
import smtplib
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]


def load(name, folder='tools'):
    spec = importlib.util.spec_from_file_location(name, ROOT/folder/(name+'.py'))
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj)
    return obj


runtime = load('monitor-runtime-lab')
smtp = load('smtp-test-receiver')
fixtures = load('test_operations_monitor_lab', 'tests')
NOW = datetime(2026,10,19,0,0,tzinfo=timezone.utc)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OperationsMonitorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.config = dict(monitor_id='isolated-queue-lab', monitor=self.fixture.config,
                           heartbeat_file=str(self.root/'heartbeat.json'))
        self.watch = dict(monitor_id='isolated-queue-lab', heartbeat_file=self.config['heartbeat_file'],
                          watchdog_state=str(self.root/'watch'), stale_after_seconds=30)
        self.events = []

    def worker(self, now=NOW, sender=None):
        return runtime.run_monitor(self.config, now, sender or self.events.append)

    def watchdog(self, now=NOW, sender=None):
        return runtime.run_watchdog(self.watch, now, sender or self.events.append)

    def test_alerts_do_not_mean_monitor_stopped(self):
        self.worker()
        self.assertEqual(self.watchdog()['active'], [])

    def test_stop_and_recovery_deduplicated(self):
        self.worker()
        self.watchdog()
        self.assertEqual(self.watchdog(NOW+timedelta(seconds=30))['active'], ['monitor_stopped'])
        count=len(self.events)
        self.watchdog(NOW+timedelta(seconds=31))
        self.assertEqual(count,len(self.events))
        self.worker(NOW+timedelta(seconds=32))
        self.assertEqual(self.watchdog(NOW+timedelta(seconds=32))['active'], [])
        self.assertEqual(self.events[-1]['transition'],'resolved')

    def test_no_first_heartbeat_startup_grace(self):
        self.assertEqual(self.watchdog()['active'], [])
        self.assertEqual(self.watchdog(NOW+timedelta(seconds=30))['active'], ['monitor_stopped'])

    def test_worker_exception_does_not_refresh_heartbeat(self):
        self.worker()
        before=Path(self.config['heartbeat_file']).read_bytes()
        with patch.object(runtime.monitor,'tick',side_effect=RuntimeError()):
            with self.assertRaises(RuntimeError): self.worker(NOW+timedelta(seconds=40))
        self.assertEqual(Path(self.config['heartbeat_file']).read_bytes(),before)

    def test_completed_monitor_pushes_heartbeat(self):
        path=self.root/'ssh.json';path.write_text('{}');self.config['heartbeat_ssh_config']=str(path)
        transfer=MagicMock()
        with patch.object(runtime,'load',return_value=transfer):
            self.assertEqual(self.worker()['heartbeat_delivery'],'acknowledged')
        transfer.send.assert_called_once()
        sent=json.loads(transfer.send.call_args.args[1])
        self.assertEqual(sent['completed_at'],NOW.isoformat())

    def test_injected_sender_does_not_freeze_completion_clock(self):
        with patch.object(runtime,'datetime') as clock:
            clock.now.side_effect=[NOW,NOW+timedelta(seconds=1)]
            runtime.run_monitor(self.config,sender=self.events.append)
        self.assertEqual(json.loads(Path(self.config['heartbeat_file']).read_text())['completed_at'],
                         (NOW+timedelta(seconds=1)).isoformat())

    def test_transfer_failure_keeps_local_record_for_retry(self):
        path=self.root/'ssh.json';path.write_text('{}');self.config['heartbeat_ssh_config']=str(path)
        transfer=MagicMock();transfer.send.side_effect=OSError()
        with patch.object(runtime,'load',return_value=transfer):
            with self.assertRaises(OSError):self.worker()
        self.assertTrue(Path(self.config['heartbeat_file']).is_file())

    def test_delivery_failure_uses_independent_watchdog_outbox(self):
        def fail(event): raise OSError('unavailable')
        result=self.worker(sender=fail)
        self.assertEqual(result['undelivered'],1)
        self.assertEqual(self.watchdog()['active'], ['notification_delivery_failed'])
        self.worker(NOW+timedelta(seconds=1))
        self.assertEqual(self.watchdog(NOW+timedelta(seconds=1))['active'], [])

    def test_watchdog_delivery_retries_and_survives_crash(self):
        self.watchdog()
        def fail(event): raise OSError()
        self.assertEqual(self.watchdog(NOW+timedelta(seconds=30), fail)['undelivered'],1)
        ids=[]
        def crash(event):
            ids.append(event['event_id'])
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.watchdog(NOW+timedelta(seconds=31),crash)
        self.watchdog(NOW+timedelta(seconds=32),lambda event: ids.append(event['event_id']))
        self.assertEqual(ids[0],ids[1])

    def test_corrupt_heartbeat_does_not_resolve_stop(self):
        self.worker();self.watchdog(NOW+timedelta(seconds=30))
        Path(self.config['heartbeat_file']).write_text('{}')
        self.assertIn('monitor_stopped',self.watchdog(NOW+timedelta(seconds=31))['active'])

    def test_future_and_replayed_heartbeat_rejected(self):
        self.worker();self.watchdog()
        path=Path(self.config['heartbeat_file'])
        data=json.loads(path.read_text())
        # A worker can finish just after the watchdog sampled its start time.
        data['completed_at']=(NOW+timedelta(seconds=1)).isoformat();path.write_text(json.dumps(data))
        self.assertEqual(self.watchdog()['active'],[])
        data['completed_at']=(NOW+timedelta(seconds=60)).isoformat();path.write_text(json.dumps(data))
        self.assertIn('heartbeat_invalid',self.watchdog()['active'])
        data['completed_at']=(NOW-timedelta(seconds=1)).isoformat();path.write_text(json.dumps(data))
        self.assertIn('heartbeat_invalid',self.watchdog()['active'])

    def test_wrong_monitor_id_rejected(self):
        self.worker();path=Path(self.config['heartbeat_file']);data=json.loads(path.read_text())
        data['monitor_id']='another-site';path.write_text(json.dumps(data))
        self.assertIn('heartbeat_invalid',self.watchdog()['active'])

    def test_unreadable_heartbeat_is_alerted(self):
        with patch.object(Path,'exists',side_effect=PermissionError()):
            active,_=runtime.heartbeat_state(self.watch,NOW,NOW,None)
        self.assertEqual(active,{'heartbeat_invalid'})

    def test_stopped_monitor_preserves_delivery_failure(self):
        def fail(event):raise OSError()
        self.worker(sender=fail);self.watchdog()
        Path(self.config['heartbeat_file']).unlink()
        self.assertEqual(set(self.watchdog(NOW+timedelta(seconds=30))['active']),
                         {'notification_delivery_failed','monitor_stopped'})

    def test_credentials_must_be_owner_only(self):
        path=self.root/'credentials.json';path.write_text('{}');path.chmod(0o644)
        config=dict(transport='smtp_starttls',host='smtp.example.invalid',port=587,credentials_file=str(path),
                    **{'from':'a@example.invalid','to':'b@example.invalid'})
        with self.assertRaises(ValueError):runtime.delivery.send(config,{})

    def test_tls_verifies_server_certificate(self):
        import ssl
        config=dict(transport='smtp_tls',host='smtp.example.invalid',port=465,
                    **{'from':'a@example.invalid','to':'b@example.invalid'})
        event=dict(event_id='abc',transition='opened',kind='monitor_stopped',observed_at=NOW.isoformat())
        client=MagicMock();client.__enter__.return_value=client;client.send_message.return_value={}
        with patch.object(runtime.delivery.smtplib,'SMTP_SSL',return_value=client) as factory:
            runtime.delivery.send(config,event)
        context=factory.call_args.kwargs['context']
        self.assertTrue(context.check_hostname);self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)

    def test_overlapping_worker_excluded(self):
        with runtime.locked(Path(self.config['monitor']['monitor_state'])):
            with self.assertRaises(BlockingIOError):self.worker()

    def test_watchdog_clock_rollback_and_config_binding(self):
        self.watchdog()
        with self.assertRaises(ValueError):self.watchdog(NOW-timedelta(seconds=1))
        self.watch['monitor_id']='other'
        with self.assertRaises(ValueError):self.watchdog()

    def test_smtp_delivery_rejection_retry_and_message_identity(self):
        reject=self.root/'reject';reject.touch()
        with smtp.receiver(self.root/'mail',reject) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                config=dict(transport='smtp_test',host='127.0.0.1',port=server.server_address[1],
                            **{'from':'owr@example.invalid','to':'operator@example.invalid'})
                self.assertEqual(self.worker(sender=lambda e:runtime.delivery.send(config,e))['undelivered'],1)
                reject.unlink()
                self.assertEqual(self.worker(sender=lambda e:runtime.delivery.send(config,e))['undelivered'],0)
                messages=list((self.root/'mail').glob('*.eml'))
                self.assertEqual(len(messages),1)
                mail=BytesParser(policy=policy.default).parsebytes(messages[0].read_bytes())
                body=json.loads(mail.get_content())
                self.assertEqual(mail['Message-ID'],f"<{body['event_id']}@owr.invalid>")
                self.assertEqual(body['kind'],'backup_missing')
            finally:server.shutdown();thread.join()

    def test_plaintext_external_smtp_and_header_injection_rejected(self):
        config=dict(transport='smtp_test',host='192.0.2.1',port=25,**{'from':'a@example.invalid','to':'b@example.invalid'})
        with self.assertRaises(ValueError):runtime.delivery.send(config,{})
        config['host']='127.0.0.1';config['to']='bad\r\nBcc: victim@example.invalid'
        with self.assertRaises(ValueError):runtime.delivery.send(config,{})

    def test_starttls_required_before_login_and_send(self):
        config=dict(transport='smtp_starttls',host='smtp.example.invalid',port=587,
                    **{'from':'a@example.invalid','to':'b@example.invalid'})
        event=dict(event_id='abc',transition='opened',kind='monitor_stopped',observed_at=NOW.isoformat())
        client=MagicMock();client.__enter__.return_value=client
        client.starttls.side_effect=smtplib.SMTPNotSupportedError()
        with patch.object(runtime.delivery.smtplib,'SMTP',return_value=client):
            with self.assertRaises(smtplib.SMTPNotSupportedError):runtime.delivery.send(config,event)
        client.send_message.assert_not_called();client.login.assert_not_called()


if __name__=='__main__':unittest.main()
