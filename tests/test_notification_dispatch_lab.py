import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import urllib.error
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dispatch', ROOT/'tools/notification-dispatch-lab.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Notifications(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.credentials = self.root/'credentials.json'
        self.credentials.write_text(json.dumps(dict(token='t'*30,user='u'*30)))
        self.credentials.chmod(0o600)
        self.provider_config = dict(transport='pushover', credentials_file=str(self.credentials))
        self.source = self.root/'source.sqlite'
        with sqlite3.connect(self.source) as db:
            db.execute('CREATE TABLE outbox(payload TEXT)')
        self.event = dict(event_id='a'*64,site='isolated-lab',domain='daily',kind='backup_missing',
                          subject='2026-10-19',transition='opened',observed_at='2026-10-19T00:00:00+00:00')
        self.config = dict(state=str(self.root/'state'),source_outbox=str(self.source),channels=[
            dict(id='mail',provider=dict(transport='smtp_test')),
            dict(id='push',provider=self.provider_config,kinds=['backup_missing'])])
        self.mail, self.push = MagicMock(), MagicMock()
        self.mail.send.return_value = {}
        self.push.send.return_value = {'receipt':'r'*30}
        self.push.poll.return_value = dict(acknowledged=0,expired=0)
        self.factory = lambda c: self.push if c['transport']=='pushover' else self.mail
        self.add(self.event)

    def add(self,event):
        with sqlite3.connect(self.source) as db:
            db.execute('INSERT INTO outbox VALUES(?)',(json.dumps(event),))

    def run_tick(self,now=0):
        return d.run(self.config,now=now,factory=self.factory)

    def test_mail_failure_does_not_block_push_and_restart_does_not_resend(self):
        self.mail.send.side_effect=OSError('secret')
        result=self.run_tick()
        self.assertTrue(any(r['channel']=='mail' and r['status']=='unknown' for r in result))
        self.push.send.assert_called_once()
        self.run_tick(1)
        self.push.send.assert_called_once()
        self.mail.send.assert_called_once()

    def test_push_failure_does_not_block_mail(self):
        self.push.send.side_effect=d.push.DeliveryError('rejected')
        self.run_tick()
        self.mail.send.assert_called_once()

    def test_quota_retry_backoff(self):
        self.push.send.side_effect=[d.push.DeliveryError('retry'),{'receipt':'r'*30}]
        self.run_tick()
        self.run_tick(59)
        self.assertEqual(self.push.send.call_count,1)
        self.run_tick(60)
        self.assertEqual(self.push.send.call_count,2)

    def test_ack_is_not_resolution(self):
        self.run_tick()
        self.push.poll.return_value=dict(acknowledged=1,expired=0)
        result=self.run_tick(60)
        self.assertTrue(any(r['receipt_state']=='acknowledged' for r in result))
        self.push.cancel.assert_not_called()
        self.run_tick(120)
        self.push.poll.assert_called_once()

    def test_resolution_cancels_receipt(self):
        self.run_tick()
        self.add(dict(self.event,event_id='b'*64,transition='resolved'))
        self.run_tick(60)
        self.push.cancel.assert_called_once_with('r'*30)
        self.assertEqual(self.push.send.call_count,2)

    def test_expiry_visible(self):
        self.run_tick()
        self.push.poll.return_value=dict(acknowledged=0,expired=1)
        self.assertTrue(any(r['receipt_state']=='expired' for r in self.run_tick(60)))

    def test_poll_failure_visible_and_backed_off(self):
        self.run_tick()
        self.push.poll.side_effect=OSError()
        self.assertTrue(any(r['poll_error'] for r in self.run_tick(60)))
        self.run_tick(120)
        self.push.poll.assert_called_once()

    def test_stale_open_not_sent_after_resolution_imported(self):
        self.add(dict(self.event,event_id='b'*64,transition='resolved'))
        self.run_tick()
        self.assertEqual(self.push.send.call_count,1)
        self.assertEqual(self.push.send.call_args.args[0]['transition'],'resolved')

    def test_noncritical_filtered(self):
        self.add(dict(self.event,event_id='c'*64,kind='approval_pending'))
        self.run_tick()
        self.assertEqual(self.push.send.call_count,1)
        self.assertEqual(self.mail.send.call_count,2)

    def test_source_readonly(self):
        before=self.source.read_bytes()
        self.run_tick()
        self.assertEqual(before,self.source.read_bytes())

    def test_crash_sending_becomes_unknown(self):
        self.run_tick()
        with sqlite3.connect(self.root/'state/dispatch.sqlite') as db:
            db.execute("UPDATE deliveries SET status='sending' WHERE channel='push'")
        self.assertTrue(any(r['status']=='unknown' for r in self.run_tick(1)))
        self.push.send.assert_called_once()

    def test_config_change_preserves_records(self):
        self.run_tick()
        self.config['channels'][1]['kinds'].append('other')
        with self.assertRaises(ValueError):self.run_tick(1)

    def test_conflicting_id_rejected(self):
        self.run_tick()
        self.add(dict(self.event,kind='other'))
        with self.assertRaises(ValueError):self.run_tick(1)

    def test_provider_request_and_minimal_body(self):
        provider=d.push.Adapter(self.provider_config)
        reply=MagicMock()
        reply.__enter__.return_value.read.return_value=json.dumps(dict(status=1,receipt='r'*30)).encode()
        with patch.object(provider.opener,'open',return_value=reply) as request:
            provider.send(dict(self.event,secret='NEVER-SEND'))
        req=request.call_args.args[0]
        self.assertEqual(req.full_url,'https://api.pushover.net/1/messages.json')
        body=urllib.parse.parse_qs(req.data.decode())
        self.assertEqual(body['priority'],['2'])
        self.assertNotIn('NEVER-SEND',req.data.decode())

    def test_http_failures_and_secret_redaction(self):
        provider=d.push.Adapter(self.provider_config)
        for code,outcome in [(400,'rejected'),(302,'rejected'),(429,'retry'),(503,'unknown')]:
            with self.subTest(code=code), patch.object(provider.opener,'open',side_effect=
                    urllib.error.HTTPError('https://secret',code,'secret',{},None)):
                with self.assertRaises(d.push.DeliveryError) as caught:provider.send(self.event)
                self.assertEqual(str(caught.exception),outcome)

    def test_lost_response_never_claims_accepted(self):
        provider=d.push.Adapter(self.provider_config)
        with patch.object(provider.opener,'open',side_effect=TimeoutError('secret')):
            with self.assertRaises(d.push.DeliveryError) as caught:provider.send(self.event)
        self.assertEqual(str(caught.exception),'unknown')

    def test_credentials_and_config_restrictions(self):
        self.credentials.chmod(0o644)
        with self.assertRaises(ValueError):d.push.Adapter(self.provider_config)
        self.credentials.chmod(0o600)
        link=self.root/'link';link.symlink_to(self.credentials)
        with self.assertRaises(OSError):d.push.Adapter(dict(self.provider_config,credentials_file=str(link)))
        for extra in [dict(retry=1),dict(expire=20000),dict(endpoint='http://elsewhere')]:
            with self.assertRaises(ValueError):d.push.Adapter(dict(self.provider_config,**extra))

    def test_receipt_paths_and_bad_receipt(self):
        provider=d.push.Adapter(self.provider_config)
        with patch.object(provider,'request',return_value=dict(acknowledged=1,expired=0)) as req:
            provider.poll('r'*30)
            req.assert_called_with('receipts/'+'r'*30+'.json')
            provider.cancel('r'*30)
            req.assert_called_with('receipts/'+'r'*30+'/cancel.json')
        with self.assertRaises(ValueError):provider.cancel('../evil')

    def test_broken_channel_configuration_does_not_block_other(self):
        def factory(config):
            if config['transport']=='smtp_test':raise ValueError('bad credentials')
            return self.push
        result=d.run(self.config,now=0,factory=factory)
        self.assertTrue(any(r['channel']=='mail' and r['status']=='pending' for r in result))
        self.push.send.assert_called_once()

    def test_malformed_response_is_unknown(self):
        provider=d.push.Adapter(self.provider_config)
        reply=MagicMock()
        reply.__enter__.return_value.read.return_value=b'{}'
        with patch.object(provider.opener,'open',return_value=reply):
            with self.assertRaises(d.push.DeliveryError) as caught:provider.send(self.event)
        self.assertEqual(str(caught.exception),'unknown')

    def test_redirect_disabled(self):
        self.assertIsNone(d.push.NoRedirect().redirect_request(None,None,302,'',{},'https://other'))


if __name__=='__main__':unittest.main()
