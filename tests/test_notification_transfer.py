import importlib.util,json,os,sqlite3,tempfile,time,unittest,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('transfer',ROOT/'tools/notification-transfer.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.requests=self.root/'requests';self.requests.mkdir();self.worker=self.root/'worker';self.worker.mkdir()
        self.server=dict(site_id='site',inbox_db=str(self.root/'inbox.sqlite'),report_file=str(self.root/'public.json'))
        self.client=dict(site_id='site',requests_dir=str(self.requests),relay_lock=str(self.root/'relay.lock'),status_file=str(self.root/'local.json'))
        self.stage=dict(site_id='site',inbox_db=self.server['inbox_db'],worker_requests=str(self.worker),stage_db=str(self.root/'stage.sqlite'),stage_lock=str(self.root/'stage.lock'))
        self.r=dict(request_id=str(uuid.uuid4()),site_id='site',channel_id='phone',revision=1,revision_token='rev1',created_at=int(time.time()))
        self.report=dict(format='owr-notification-admin-status-v1',site_id='site',revision=1,revision_token='rev1',completed_at='2026-01-01T00:00:00+00:00',simulated=True,channels=[dict(id='phone',counts={},receipts={},problems=[])],tests=[])
    def packet(self,requests=None):return dict(format='owr-notification-exchange-v1',site_id='site',nonce='a'*32,requests=[self.r] if requests is None else requests)
    def send(self,config,packet):return t.receive(t.body(packet),self.server)
    def queue(self):
        path=self.requests/(self.r['request_id']+'.json');path.write_text(json.dumps(self.r));return path
    def test_ack_is_durable_not_delivery(self):
        reply=self.send(None,self.packet());self.assertEqual(reply['acknowledgements'][0]['state'],'stored')
        with sqlite3.connect(self.server['inbox_db']) as db:self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],1)
    def test_idempotent_retry_and_content_conflict(self):
        one=self.send(None,self.packet());self.assertEqual(one,self.send(None,self.packet()))
        self.r['channel_id']='other'
        with self.assertRaises(ValueError):self.send(None,self.packet())
    def test_batch_rollback_on_conflict(self):
        self.send(None,self.packet());new=dict(self.r,request_id=str(uuid.uuid4()));conflict=dict(self.r,channel_id='other')
        with self.assertRaises(ValueError):self.send(None,self.packet([new,conflict]))
        with sqlite3.connect(self.server['inbox_db']) as db:self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],1)
    def test_lost_ack_retains_local_then_retries(self):
        path=self.queue()
        def lost(c,p):self.send(c,p);raise TimeoutError()
        with self.assertRaises(TimeoutError):t.exchange(self.client,lost)
        self.assertTrue(path.exists());t.exchange(self.client,self.send);self.assertFalse(path.exists())
    def test_wrong_nonce_and_hash_do_not_remove_requests(self):
        path=self.queue()
        for field in ('nonce','acknowledgements'):
            def wrong(c,p):
                reply=self.send(c,p);reply[field]='bad';return reply
            with self.assertRaises(ValueError):t.exchange(self.client,wrong)
            self.assertTrue(path.exists())
    def test_changed_file_not_deleted(self):
        path=self.queue()
        def modify(c,p):
            reply=self.send(c,p);path.write_text(json.dumps(dict(self.r,channel_id='changed')));return reply
        t.exchange(self.client,modify);self.assertTrue(path.exists())
    def test_stale_result_time_is_not_refreshed(self):
        Path(self.server['report_file']).write_text(json.dumps(self.report));t.exchange(self.client,self.send)
        self.assertEqual(json.loads(Path(self.client['status_file']).read_text())['completed_at'],self.report['completed_at'])
    def test_report_rollback_preserves_last_good_and_requests(self):
        Path(self.client['status_file']).write_text(json.dumps(dict(self.report,completed_at='2026-02-01T00:00:00+00:00')))
        Path(self.server['report_file']).write_text(json.dumps(self.report));path=self.queue()
        with self.assertRaises(ValueError):t.exchange(self.client,self.send)
        self.assertTrue(path.exists());self.assertIn('2026-02',Path(self.client['status_file']).read_text())
    def test_report_filters_secrets(self):
        self.report['credentials']='secret';self.report['channels'][0]['receipt']='secret'
        self.assertNotIn('secret',json.dumps(t.report(self.report,'site')))
    def test_report_wrong_site_counter_and_future(self):
        for key,value in [('site_id','other'),('completed_at','2099-01-01T00:00:00+00:00'),('revision',True)]:
            with self.assertRaises(ValueError):t.report(dict(self.report,**{key:value}),'site')
        self.report['channels'][0]['counts']={'accepted':True}
        with self.assertRaises(ValueError):t.report(self.report,'site')
    def test_invalid_request_fields_and_scope(self):
        for value in [dict(self.r,site_id='other'),dict(self.r,path='/etc/passwd'),dict(self.r,request_id='../bad'),dict(self.r,revision=True)]:
            with self.assertRaises(ValueError):self.send(None,self.packet([value]))
    def test_duplicate_json_and_limits(self):
        for raw in [b'{"x":1,"x":2}',b' '*32769]:
            with self.assertRaises(ValueError):t.receive(raw,self.server)
        with self.assertRaises(ValueError):self.send(None,self.packet([self.r]*21))
    def test_symlink_and_fifo_are_rejected(self):
        path=self.queue();path.unlink();path.symlink_to(self.root/'missing')
        with self.assertRaises(OSError):t.exchange(self.client,self.send)
        path.unlink();os.mkfifo(path)
        with self.assertRaises(ValueError):t.exchange(self.client,self.send)
    def test_stage_durable_and_no_recreation_after_consumption(self):
        self.send(None,self.packet());self.assertEqual(t.stage(self.stage)['staged'],1)
        target=self.worker/(self.r['request_id']+'.json');self.assertEqual(json.loads(target.read_text()),self.r)
        target.unlink();self.assertEqual(t.stage(self.stage)['staged'],0);self.assertFalse(target.exists())
    def test_stage_recovers_written_file_before_ledger_commit(self):
        self.send(None,self.packet());t.atomic(self.worker/(self.r['request_id']+'.json'),self.r)
        self.assertEqual(t.stage(self.stage)['staged'],1)
    def test_stage_conflict_does_not_overwrite(self):
        self.send(None,self.packet());target=self.worker/(self.r['request_id']+'.json');t.atomic(target,dict(self.r,channel_id='other'))
        with self.assertRaises(ValueError):t.stage(self.stage)
        self.assertEqual(json.loads(target.read_text())['channel_id'],'other')
    def test_stage_does_not_rewrite_processed_identity(self):
        self.send(None,self.packet());t.stage(self.stage)
        with sqlite3.connect(self.server['inbox_db']) as db:db.execute('UPDATE inbox SET payload=?',(json.dumps(dict(self.r,channel_id='changed')),))
        with self.assertRaises(ValueError):t.stage(self.stage)
    def test_busy_relay_leaves_queue(self):
        path=self.queue()
        with open(self.client['relay_lock'],'a') as lock:
            t.fcntl.flock(lock,t.fcntl.LOCK_EX|t.fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):t.exchange(self.client,self.send)
        self.assertTrue(path.exists())
    def test_ssh_has_pinning_no_agent_no_forwarding(self):
        config=dict(self.client,host='worker.example.invalid',user='ingress',port=22,identity_file='/private/key',known_hosts='/private/known')
        cmd=t.command(config)
        for option in ['StrictHostKeyChecking=yes','IdentityAgent=none','ClearAllForwardings=yes','HostKeyAlias=owr-notification-site']:self.assertIn(option,cmd)
        self.assertEqual(cmd[-1],'notification-exchange')
        with self.assertRaises(ValueError):t.command(dict(config,host='-oProxyCommand=bad'))
    def test_publish_safe_fields_only(self):
        self.report['secret']='never';source=self.root/'raw.json';source.write_text(json.dumps(self.report));target=self.root/'filtered.json'
        t.publish(dict(site_id='site',worker_status=str(source),public_status=str(target)))
        self.assertNotIn('never',target.read_text());self.assertEqual(target.stat().st_mode&0o777,0o640)
    def test_remote_capacity_rejects_new_but_allows_status_poll(self):
        self.send(None,self.packet())
        with sqlite3.connect(self.server['inbox_db']) as db:db.executemany('INSERT INTO inbox VALUES(?,?,?)',[(str(i),'{}',0) for i in range(9999)])
        self.assertEqual(self.send(None,self.packet([]))['acknowledgements'],[])
        with self.assertRaises(ValueError):self.send(None,self.packet([dict(self.r,request_id=str(uuid.uuid4()))]))
    def test_missing_remote_report_preserves_previous_completion(self):
        output=Path(self.client['status_file']);output.write_text(json.dumps(self.report));before=output.read_bytes()
        self.assertFalse(t.exchange(self.client,self.send)['report_received']);self.assertEqual(output.read_bytes(),before)
    def test_invalid_remote_report_preserves_unacknowledged_request(self):
        path=self.queue();Path(self.server['report_file']).write_text(json.dumps(dict(self.report,site_id='wrong')))
        with self.assertRaises(ValueError):t.exchange(self.client,self.send)
        self.assertTrue(path.exists());self.assertFalse(Path(self.server['inbox_db']).exists())
    def test_relay_created_queue_lock_is_group_writable(self):
        old=os.umask(0o027)
        try:t.exchange(self.client,self.send)
        finally:os.umask(old)
        self.assertEqual((self.requests/'.request.lock').stat().st_mode&0o777,0o660)
    def test_concurrent_identical_receipts_remain_single(self):
        from concurrent.futures import ThreadPoolExecutor
        def attempt(_):
            # A bounded receiver may refuse a busy DB; the sender retains and retries.
            for retry in range(3):
                try:return self.send(None,self.packet())
                except sqlite3.OperationalError as exc:
                    if 'locked' not in str(exc) or retry==2:raise
                    time.sleep(.1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            replies=list(pool.map(attempt,range(4)))
        self.assertEqual(replies,[replies[0]]*4)
        with sqlite3.connect(self.server['inbox_db']) as db:self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0],1)

if __name__=='__main__':unittest.main()
