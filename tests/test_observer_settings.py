import importlib.util,json,sqlite3,tempfile,unittest,uuid,time
from pathlib import Path
from unittest.mock import MagicMock
ROOT=Path(__file__).resolve().parents[1]
def load(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'tools'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('observer-settings');dispatch=m.bridge.dispatch
class SettingsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'source.sqlite';self.state=self.root/'delivery'
  with sqlite3.connect(self.source) as db:db.execute('CREATE TABLE outbox(id TEXT PRIMARY KEY,payload TEXT)')
  self.key=self.root/'key';self.key.write_text(json.dumps(dict(token='t'*30,user='u'*30)));self.key.chmod(0o600)
  self.policy=dict(profiles=dict(push=dict(transport='pushover',credentials_file=str(self.key))),required_kinds=sorted(m.KINDS))
  self.pfile=self.root/'policy.json';self.pfile.write_text(json.dumps(self.policy))
  self.settings=dict(format='owr-notification-settings-v1',site_id='site',revision=2,revision_token='rev2',channels=[dict(id='phone',label='Phone',profile='push',provider='pushover',recipient='iPhone',enabled=True,kinds=sorted(m.KINDS),retry=60,expire=300)])
  self.old,_=m.bridge.compile_settings(self.settings,self.policy['profiles'],self.source,self.state)
  self.provider=MagicMock();self.provider.send.return_value={'receipt':'r'*30};self.provider.poll.return_value=dict(acknowledged=False,expired=False)
  dispatch.run(self.old,now=1000,factory=lambda c:self.provider)
  self.c=dict(site_id='site',inbox_db=str(self.root/'inbox.sqlite'),state=str(self.root/'control'),delivery_state=str(self.state),policy_file=str(self.pfile))
 def req(self):return dict(format='owr-observer-settings-request-v1',request_id=str(uuid.uuid4()),created_at=int(time.time()),expected_hash=m.bridge.digest(m.live.current(self.state)),settings=json.loads(json.dumps(self.settings)))
 def receive(self,v):return m.receive(self.c,dict(site_id='site',nonce='a'*32,requests=[v]))
 def event(self,n,transition='opened',subject='incident'):
  e=dict(event_id=f'{n:064x}',site='site',domain='watchdog',kind='monitor_stopped',subject=subject,transition=transition,observed_at='2026-10-19T00:00:00+00:00')
  with sqlite3.connect(self.source) as db:db.execute('INSERT INTO outbox VALUES(?,?)',(e['event_id'],json.dumps(e)))
 def rows(self):
  with sqlite3.connect(self.state/'dispatch.sqlite') as db:return db.execute('SELECT channel,event,status,receipt,attempts,next_at,poll_at FROM deliveries ORDER BY rowid').fetchall()
 def test_cutover_preserves_pending_and_new_route(self):
  self.event(1);v=self.req();self.receive(v);r=m.apply_pending(self.c);self.assertEqual(r['last_request']['outcome'],'applied')
  before=self.rows();self.assertEqual(before[0][2],'pending');self.event(2,subject='new')
  dispatch.run(m.live.current(self.state),now=1001,factory=lambda c:self.provider);after=self.rows();self.assertEqual(len(after),2);self.assertNotEqual(after[0][0],after[1][0])
 def test_unknown_and_receipt_attempts_preserved(self):
  self.event(1);dispatch.run(self.old,now=1001,factory=lambda c:self.provider)
  self.event(2,subject='other');self.provider.send.side_effect=RuntimeError();dispatch.run(self.old,now=1002,factory=lambda c:self.provider)
  before=self.rows();self.receive(self.req());m.apply_pending(self.c);self.assertEqual(before,self.rows())
  calls=self.provider.send.call_count;dispatch.run(m.live.current(self.state),now=1003,factory=lambda c:self.provider);self.assertEqual(calls,self.provider.send.call_count)
 def test_disabled_old_route_receives_resolution(self):
  self.event(1);dispatch.run(self.old,now=1001,factory=lambda c:self.provider)
  self.settings['channels'].append(dict(self.settings['channels'][0],id='replacement'));self.settings['channels'][0]['enabled']=False
  self.receive(self.req());m.apply_pending(self.c);self.event(2,'resolved')
  dispatch.run(m.live.current(self.state),now=1062,factory=lambda c:self.provider);self.provider.cancel.assert_called_once_with('r'*30)
 def test_no_last_route_disable(self):
  self.settings['channels'][0]['enabled']=False;self.receive(self.req());r=m.apply_pending(self.c)
  self.assertEqual(r['last_request']['reason'],'policy');self.assertEqual(m.live.current(self.state),self.old)
 def test_unapproved_profile(self):
  self.settings['channels'][0]['profile']='evil';self.receive(self.req());self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'rejected')
 def test_stale_hash(self):
  v=self.req();v['expected_hash']='0'*64;self.receive(v);self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'conflict')
 def test_expired(self):
  v=self.req();v['created_at']-=86401;self.receive(v);self.assertEqual(m.apply_pending(self.c)['last_request']['reason'],'expired')
 def test_credential_freeze_failure_keeps_old(self):
  self.key.chmod(0o644);self.receive(self.req());self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'rejected');self.assertEqual(m.live.current(self.state),self.old)
 def test_repeat_and_lost_ack(self):
  v=self.req();self.receive(v);self.receive(v);m.apply_pending(self.c);before=m.live.current(self.state);m.apply_pending(self.c);self.assertEqual(m.live.current(self.state),before)
 def test_crash_after_apply_before_ledger(self):
  v=self.req();self.receive(v);candidate,binding=m.bridge.compile_settings(self.settings,self.policy['profiles'],self.source,self.state,True,True)
  m.live.apply(candidate,binding,v['expected_hash']);before=m.live.current(self.state)
  self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'applied');self.assertEqual(m.live.current(self.state),before)
 def test_request_identity_conflict(self):
  v=self.req();self.receive(v);v['created_at']-=1
  with self.assertRaises(ValueError):self.receive(v)
 def test_foreign_site(self):
  v=self.req();v['settings']['site_id']='other'
  with self.assertRaises(ValueError):self.receive(v)
 def test_lock_retains_request(self):
  import fcntl
  self.receive(self.req())
  with (self.state/'dispatch.lock').open('a') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);self.assertIsNone(m.apply_pending(self.c)['last_request'])
  self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'applied')
 def test_key_snapshot_stable(self):
  self.receive(self.req());m.apply_pending(self.c);active=m.live.current(self.state);path=active['channels'][0]['provider']['credentials_file'];self.key.write_text('rotated');self.assertIn('u'*30,Path(path).read_text())
 def test_exchange_requires_durable_ack(self):
  directory=self.root/'requests';directory.mkdir();v=self.req();path=directory/(v['request_id']+'.json');path.write_text(json.dumps(v))
  c=dict(site_id='site',lock_file=str(self.root/'lock'),requests_dir=str(directory))
  with self.assertRaises(ValueError):m.exchange(c,lambda c,p:dict(nonce=p['nonce'],acknowledgements=[]))
  self.assertTrue(path.exists());m.exchange(c,lambda c,p:m.receive(self.c,p));self.assertFalse(path.exists())
 def test_unapproved_mail_recipient(self):
  self.policy['profiles']['mail']=dict(transport='smtp_starttls',host='mail.example.invalid',port=587,**{'from':'sender@example.invalid'})
  self.policy['allowed_recipients']={'mail':['approved@example.invalid']};self.pfile.write_text(json.dumps(self.policy))
  self.settings['channels'][0].update(provider='smtp_starttls',profile='mail',recipient='unapproved@example.invalid');self.receive(self.req())
  self.assertEqual(m.apply_pending(self.c)['last_request']['reason'],'policy');self.assertEqual(m.live.current(self.state),self.old)
 def test_required_alarm_cannot_be_omitted(self):
  self.settings['channels'][0]['kinds']=['monitor_stopped'];self.receive(self.req());self.assertEqual(m.apply_pending(self.c)['last_request']['outcome'],'rejected')
 def test_adopt_preserves_state(self):
  root=self.root/'observer';root.mkdir();old=dict(state=str(root),admin_site_id='site',alerts=self.old)
  (root/'binding.json').write_text(json.dumps(old));(root/'keep').write_text('incidents and heartbeats')
  self.event(1);before=self.source.read_bytes();m.enable(dict(old,configuration=self.c))
  self.assertEqual(before,self.source.read_bytes());self.assertEqual((root/'keep').read_text(),'incidents and heartbeats');self.assertEqual(m.live.current(self.state),self.old)
 def test_adopt_rejects_other_changes(self):
  root=self.root/'observer';root.mkdir();old=dict(state=str(root),admin_site_id='site',alerts=self.old,stale_after_seconds=300);(root/'binding.json').write_text(json.dumps(old))
  with self.assertRaises(ValueError):m.enable(dict(old,configuration=self.c,stale_after_seconds=600))
if __name__=='__main__':unittest.main()
