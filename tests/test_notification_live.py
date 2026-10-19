import importlib.util,json,sqlite3,tempfile,unittest,uuid,os
from pathlib import Path
from unittest.mock import MagicMock
ROOT=Path(__file__).resolve().parents[1]
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
live=load('notification-live');bridge=load('notification-admin-bridge');dispatch=bridge.dispatch

class LiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.source=self.root/'source.sqlite';self.state=self.root/'state'
        with sqlite3.connect(self.source) as db:db.execute('CREATE TABLE outbox(payload TEXT)')
        self.credentials=self.root/'secret';self.credentials.write_text(json.dumps(dict(token='t'*30,user='u'*30)));self.credentials.chmod(0o600)
        self.profiles={'push':dict(transport='pushover',credentials_file=str(self.credentials))}
        self.settings=dict(format='owr-notification-settings-v1',site_id='site',revision=1,revision_token='rev1',channels=[dict(id='phone',profile='push',provider='pushover',recipient='phone',enabled=True,kinds=['backup_missing'],retry=60,expire=300)])
        self.config,self.binding=bridge.compile_settings(self.settings,self.profiles,self.source,self.state)
        self.provider=MagicMock();self.provider.send.return_value={'receipt':'r'*30};self.provider.poll.return_value=dict(acknowledged=False,expired=False)
        self.factory=lambda c:self.provider
        dispatch.run(self.config,now=1000,factory=self.factory)
    def tearDown(self):self.temp.cleanup()
    def event(self,n,transition='opened',subject='incident'):
        event=dict(event_id=f'{n:064x}',site='site',domain='daily',subject=subject,kind='backup_missing',transition=transition,observed_at='2026-10-19T00:00:00+00:00')
        with sqlite3.connect(self.source) as db:db.execute('INSERT INTO outbox VALUES(?)',(json.dumps(event),))
        return event
    def apply(self,revision=2,enabled=True):
        self.settings['revision']=revision;self.settings['revision_token']='rev'+str(revision);self.settings['channels'][0]['enabled']=enabled
        candidate,binding=bridge.compile_settings(self.settings,self.profiles,self.source,self.state,True,True)
        self.config=live.apply(candidate,binding,bridge.digest(self.config));return self.config
    def rows(self):
        with sqlite3.connect(self.state/'dispatch.sqlite') as db:return db.execute('SELECT channel,event,status,receipt,attempts FROM deliveries ORDER BY rowid').fetchall()
    def request(self,**changes):
        spool=self.root/'requests';spool.mkdir(exist_ok=True)
        req=dict(request_id=str(uuid.uuid4()),channel_id='phone',site_id='site',revision=2,revision_token='rev2',created_at=1000);req.update(changes)
        (spool/(req['request_id']+'.json')).write_text(json.dumps(req));return spool
    def test_pending_preserved_and_no_historical_replay(self):
        self.event(1);self.apply();rows=self.rows();self.assertEqual(len(rows),1);self.assertEqual(rows[0][0],'phone');self.assertEqual(rows[0][2],'pending')
        self.event(2,subject='new');dispatch.run(self.config,now=1001,factory=self.factory)
        rows=self.rows();self.assertEqual(len(rows),2);self.assertNotEqual(rows[0][0],rows[1][0]);self.assertEqual(self.provider.send.call_count,2)
    def test_unknown_not_resent_after_switch(self):
        self.event(1);self.provider.send.side_effect=RuntimeError();dispatch.run(self.config,now=1001,factory=self.factory)
        self.apply();dispatch.run(self.config,now=1002,factory=self.factory);self.assertEqual(self.provider.send.call_count,1);self.assertEqual(self.rows()[0][2],'unknown')
    def test_retry_deadline_and_attempts_preserved(self):
        self.event(1);self.provider.send.side_effect=dispatch.push.DeliveryError('retry');dispatch.run(self.config,now=1001,factory=self.factory)
        before=self.rows();self.apply();self.assertEqual(before,self.rows());dispatch.run(self.config,now=1002,factory=self.factory);self.assertEqual(self.provider.send.call_count,1)
    def test_disabled_route_cancels_old_receipt(self):
        self.event(1);dispatch.run(self.config,now=1001,factory=self.factory);self.apply(enabled=False)
        self.event(2,'resolved');self.event(3,subject='new');dispatch.run(self.config,now=1062,factory=self.factory)
        self.provider.cancel.assert_called_once_with('r'*30);self.assertEqual(len(self.rows()),2)
    def test_old_recipient_and_credentials_are_pinned(self):
        self.event(1);self.apply();old=self.config['channels'][0]['provider']['credentials_file'];self.credentials.write_text('rotated')
        self.assertIn('u'*30,Path(old).read_text());self.assertEqual(os.stat(old).st_mode&0o777,0o600)
    def test_stale_apply_is_atomic(self):
        self.apply();old=self.config;candidate,binding=bridge.compile_settings(self.settings,self.profiles,self.source,self.state,True,True)
        binding['revision']=3
        with self.assertRaises(ValueError):live.apply(candidate,binding,'bad')
        self.assertEqual(live.current(self.state),old)
    def test_repeated_apply_is_idempotent(self):
        self.apply();candidate,binding=bridge.compile_settings(self.settings,self.profiles,self.source,self.state,True,True)
        self.assertEqual(live.apply(candidate,binding,'stalehash'),self.config)
    def test_foreign_site_rejected(self):
        self.apply();self.settings.update(site_id='foreign',revision=3)
        c,b=bridge.compile_settings(self.settings,self.profiles,self.source,self.state,True,True)
        with self.assertRaises(ValueError):live.apply(c,b,bridge.digest(self.config))
    def test_source_identity_mutation_rejected(self):
        self.event(1);self.apply()
        with sqlite3.connect(self.source) as db:db.execute("UPDATE outbox SET payload=replace(payload,'incident','tampered')")
        with self.assertRaises(ValueError):dispatch.run(self.config,now=1002,factory=self.factory)
    def test_status_requires_completed_new_revision(self):
        self.apply();b=dict(self.config['admin_binding'],config_hash=bridge.digest(self.config))
        with self.assertRaises(ValueError):bridge.status(self.config,b)
        dispatch.run(self.config,now=1002,factory=self.factory);self.assertEqual(len(bridge.status(self.config,b)['channels']),1)
    def test_test_send_once_and_normal_priority(self):
        self.apply();spool=self.request();live.tests(self.config,spool,1001,self.factory);live.tests(self.config,spool,1002,self.factory)
        self.provider.send.assert_called_once();event=self.provider.send.call_args.args[0];self.assertEqual(event['transition'],'resolved');self.assertEqual(event['kind'],'notification_test')
    def test_test_send_rate_limit(self):
        self.apply();spool=self.request();live.tests(self.config,spool,1001,self.factory);self.request();rows=live.tests(self.config,spool,1002,self.factory)
        self.assertIn('blocked',[r['status'] for r in rows]);self.provider.send.assert_called_once()
    def test_expired_stale_foreign_and_disabled_requests(self):
        self.apply()
        for fields in [dict(created_at=1),dict(revision_token='old'),dict(site_id='other'),dict(channel_id='unknown')]:
            live.tests(self.config,self.request(**fields),1001,self.factory)
        self.provider.send.assert_not_called()
    def test_test_unknown_not_retried(self):
        self.apply();self.provider.send.side_effect=RuntimeError();spool=self.request();live.tests(self.config,spool,1001,self.factory)
        rows=live.tests(self.config,spool,1100,self.factory);self.assertEqual(rows[0]['status'],'unknown');self.provider.send.assert_called_once()
    def test_switch_lock_excludes_worker_and_operator(self):
        import fcntl
        with (self.state/'dispatch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.apply()
    def test_rejected_and_waiting_report_survive_disabled_channel(self):
        self.event(1);dispatch.run(self.config,now=1001,factory=self.factory);self.apply(enabled=False);dispatch.run(self.config,now=1002,factory=self.factory)
        report=bridge.status(self.config,dict(self.config['admin_binding'],config_hash=bridge.digest(self.config)))
        self.assertEqual(report['channels'][0]['receipts']['waiting'],1)
    def test_rotated_key_only_applies_to_new_route(self):
        self.apply();old_path=self.config['channels'][-1]['provider']['credentials_file']
        self.credentials.write_text(json.dumps(dict(token='x'*30,user='y'*30)))
        self.apply(revision=3);new_path=self.config['channels'][-1]['provider']['credentials_file']
        self.assertNotEqual(old_path,new_path);self.assertIn('u'*30,Path(old_path).read_text());self.assertIn('y'*30,Path(new_path).read_text())
    def test_failed_snapshot_rolls_back_cutover(self):
        self.event(1);self.credentials.chmod(0o644)
        with self.assertRaises(ValueError):self.apply()
        self.assertEqual(live.current(self.state),self.config);self.assertEqual(self.rows(),[])
    def test_old_worker_cannot_send_after_switch(self):
        old=self.config;self.apply()
        with self.assertRaises(ValueError):dispatch.run(old,now=1001,factory=self.factory)
        self.provider.send.assert_not_called()
    def test_interrupted_test_send_becomes_unknown(self):
        self.apply();spool=self.request();live.tests(self.config,spool,1001,self.factory)
        with sqlite3.connect(self.state/'dispatch.sqlite') as db:db.execute("UPDATE test_requests SET status='sending'")
        result=live.tests(self.config,spool,1002,self.factory)
        self.assertEqual(result[0]['status'],'unknown');self.provider.send.assert_called_once()
    def test_test_result_keeps_original_revision(self):
        self.apply();spool=self.request();live.tests(self.config,spool,1001,self.factory);self.apply(revision=3)
        result=live.tests(self.config,spool,1002,self.factory)
        self.assertEqual(result[0]['revision_token'],'rev2')
    def test_fifo_request_cannot_block_worker(self):
        self.apply();spool=self.request();path=next(spool.glob('*.json'));path.unlink();os.mkfifo(path)
        self.assertEqual(live.tests(self.config,spool,1001,self.factory),[]);self.provider.send.assert_not_called()
    def test_symlink_request_is_not_followed(self):
        self.apply();spool=self.request();path=next(spool.glob('*.json'));path.unlink();path.symlink_to(self.credentials)
        self.assertEqual(live.tests(self.config,spool,1001,self.factory),[]);self.provider.send.assert_not_called()

if __name__=='__main__':unittest.main()
