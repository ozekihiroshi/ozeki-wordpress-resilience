import importlib.util,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('view',ROOT/'tools/daily-admin-status.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Snapshot(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        with sqlite3.connect(self.root/'daily.sqlite') as db:
            db.execute('CREATE TABLE recovery_attempts(n INTEGER,request_id,day,state,outcome,registration,report_hash)')
            db.execute("INSERT INTO recovery_attempts VALUES(1,'trial','2026-10-20','interrupted','unknown','unavailable',NULL)")
        self.base=self.root/'recovery-attempts/trial';self.base.mkdir(parents=True)
        self.mock=patch.object(m.d.Coordinator,'status',return_value=dict(runs=[dict(day='2026-10-20',phase='approved',
             storage_complete=True,approval_state='approved',restore_state='not_observed',secret='NEVER-RENDER-SECRET')],
             missing_due_slot=False))
        self.mock.start()
    def tearDown(self):self.mock.stop();self.temp.cleanup()
    def get(self):return m.snapshot(self.root,'site')
    def test_readonly_and_whitelist(self):
        before=(self.root/'daily.sqlite').read_bytes()
        result=self.get()
        self.assertEqual(before,(self.root/'daily.sqlite').read_bytes())
        self.assertNotIn('NEVER-RENDER-SECRET',json.dumps(result))
        self.assertEqual(result['attempts'][0]['cleanup'],'not_recorded')
    def test_partial_cleanup(self):
        (self.base/'cleanup-progress.json').write_text('{}')
        self.assertEqual(self.get()['attempts'][0]['cleanup'],'incomplete')
    def test_invalid_close(self):
        (self.base/'cleanup-review.json').write_text('{"request_id":"other","resources_removed":true}')
        self.assertEqual(self.get()['attempts'][0]['cleanup'],'invalid')
    def test_closed_history(self):
        with sqlite3.connect(self.root/'daily.sqlite') as db:db.execute("UPDATE recovery_attempts SET state='reviewed_closed'")
        (self.base/'cleanup-review.json').write_text('{"request_id":"trial","resources_removed":true}')
        self.assertEqual(self.get()['attempts'][0]['cleanup'],'closed')
        self.assertEqual(self.get()['attempts'][0]['outcome'],'unknown')
    def test_automatic_cleanup_hash_binding(self):
        raw=b'{"isolated_restore":{"resources_removed":true}}'
        (self.base/'result.json').write_bytes(raw)
        with sqlite3.connect(self.root/'daily.sqlite') as db:
            db.execute("UPDATE recovery_attempts SET state='finished',outcome='succeeded',report_hash=?",(m.d.gate.sha(raw),))
        self.assertEqual(self.get()['attempts'][0]['cleanup'],'automatic_removed')
        (self.base/'result.json').write_bytes(raw+b' ')
        self.assertEqual(self.get()['attempts'][0]['cleanup'],'invalid')
    def test_missing_source_not_created(self):
        new=self.root/'missing'
        with self.assertRaises(ValueError):m.snapshot(new,'site')
        self.assertFalse(new.exists())
if __name__=='__main__':unittest.main()
