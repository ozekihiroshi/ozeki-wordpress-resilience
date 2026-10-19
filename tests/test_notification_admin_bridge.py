import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bridge',ROOT/'tools/notification-admin-bridge.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class BridgeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.settings=dict(format='owr-notification-settings-v1',site_id='site-lab',revision=1,revision_token='revision-lab',channels=[dict(id='push',profile='push-profile',provider='pushover',recipient='test phone',enabled=True,kinds=['backup_missing'],retry=60,expire=300)])
        self.profiles={'push-profile':dict(transport='pushover',credentials_file='/secret/reference.json')}
        self.source=self.root/'source.sqlite'
        with sqlite3.connect(self.source) as db:
            db.execute('CREATE TABLE outbox(payload TEXT)')
            db.execute('INSERT INTO outbox VALUES(?)',(json.dumps(dict(event_id='a'*64,site='lab',domain='daily',kind='backup_missing',subject='test',transition='opened',observed_at='2026-10-19T00:00:00+00:00')),))
    def compile(self):return b.compile_settings(self.settings,self.profiles,self.source,self.root/'delivery',include_existing=True)
    def delivered(self):
        config,binding=self.compile();provider=MagicMock();provider.send.return_value={'receipt':'r'*30}
        b.dispatch.run(config,now=1000,factory=lambda c:provider)
        return config,binding
    def test_exact_selection_and_private_binding(self):
        config,binding=self.compile()
        self.assertEqual(config['channels'][0]['kinds'],['backup_missing'])
        self.assertNotIn('/secret',json.dumps(binding))
        self.assertEqual(binding['revision_token'],'revision-lab')
    def test_settings_do_not_modify_profiles(self):
        before=json.dumps(self.profiles,sort_keys=True);self.compile()
        self.assertEqual(before,json.dumps(self.profiles,sort_keys=True))
    def test_unknown_profile_rejected(self):
        self.settings['channels'][0]['profile']='unknown'
        with self.assertRaises(KeyError):self.compile()
    def test_profile_path_rejected(self):
        self.settings['channels'][0]['profile']='../secret'
        with self.assertRaises(ValueError):self.compile()
    def test_provider_mismatch_rejected(self):
        self.profiles['push-profile']['transport']='smtp_tls'
        with self.assertRaises(ValueError):self.compile()
    def test_disabled_channel_not_activated(self):
        self.settings['channels'][0]['enabled']=False
        with self.assertRaises(ValueError):self.compile()
    def test_unknown_kind_and_interval_rejected(self):
        self.settings['channels'][0]['kinds']=['other']
        with self.assertRaises(ValueError):self.compile()
        self.settings['channels'][0]['kinds']=['backup_missing'];self.settings['channels'][0]['expire']=1
        with self.assertRaises(ValueError):self.compile()
    def test_email_header_injection_rejected(self):
        self.settings['channels'][0].update(provider='smtp_tls',recipient='test@example.invalid\r\nBcc:x@example.invalid')
        self.profiles['push-profile']['transport']='smtp_tls'
        with self.assertRaises(ValueError):self.compile()
    def test_existing_state_never_replaced(self):
        self.delivered()
        with self.assertRaises(ValueError):self.compile()
    def test_status_omits_secrets_and_keeps_ack_separate(self):
        config,binding=self.delivered();report=b.status(config,binding,simulated=True)
        self.assertEqual(report['channels'][0]['counts'],{'accepted':1})
        self.assertEqual(report['channels'][0]['receipts'],{'waiting':1})
        self.assertNotIn('/secret',json.dumps(report));self.assertNotIn('r'*30,json.dumps(report))
    def test_wrong_binding_rejected(self):
        config,binding=self.delivered();binding['config_hash']='wrong'
        with self.assertRaises(ValueError):b.status(config,binding)
    def test_dispatcher_binding_mismatch_rejected(self):
        config,binding=self.delivered()
        with sqlite3.connect(self.root/'delivery/dispatch.sqlite') as db:db.execute('UPDATE settings SET binding=?',(json.dumps({}),))
        with self.assertRaises(ValueError):b.status(config,binding)
    def test_reader_respects_dispatch_lock(self):
        import fcntl
        config,binding=self.delivered()
        with (self.root/'delivery/dispatch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):b.status(config,binding)
    def test_historical_replay_requires_explicit_selection(self):
        with self.assertRaises(ValueError):b.compile_settings(self.settings,self.profiles,self.source,self.root/'delivery')

if __name__=='__main__':unittest.main()
