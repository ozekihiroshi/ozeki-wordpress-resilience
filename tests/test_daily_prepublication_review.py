import unittest,tempfile,importlib.util,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('daily',Path(__file__).resolve().parents[1]/'tools/daily-backup-lab.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ReviewTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.c=m.Coordinator(self.t.name,'s3')
  def fail(work,report):
   (work/'candidate').mkdir();(work/'candidate/receipt.json').write_text(json.dumps(dict(storage_complete=False,restore_allowed=False,error_type='RuntimeError')))
   (work/'worker.log').write_text("Traceback (most recent call last):\n in preflight\n in authorize\n receipt['preflight'] = (preflight or transport.preflight)()\nRuntimeError: EC2 authorization failed for writer; sensitive details suppressed\n")
   raise RuntimeError()
  self.row=self.c.tick(datetime(2026,10,19,tzinfo=timezone.utc),fail);self.work=Path(self.row['report']).parent
  self.digest=hashlib.sha256((self.work/'worker.log').read_bytes()).hexdigest()
 def review(self,digest=None):return self.c.review_prepublication_failure('2026-10-19',self.row['id'],digest or self.digest,'test operator')
 def test_review_preserves_unknown_event_and_requires_explicit_retry(self):
  self.review()
  with self.c.locked() as db:self.assertEqual([r['state'] for r in db.execute('SELECT state FROM events')],['running','unknown','failed'])
  self.assertTrue((self.work/'operator-review.json').exists())
  self.assertEqual(self.c.tick(datetime(2026,10,19,tzinfo=timezone.utc),lambda *a:self.fail('must not auto retry'))['state'],'failed')
 def test_changed_log_rejected(self):
  with self.assertRaises(ValueError):self.review('0'*64)
 def test_possible_storage_attempt_rejected(self):
  (self.work/'candidate/transfer-receipts').mkdir()
  with self.assertRaises(ValueError):self.review()
 def test_later_failure_rejected(self):
  (self.work/'worker.log').write_text('RuntimeError: uncertain PUT')
  with self.assertRaises(ValueError):self.review(hashlib.sha256((self.work/'worker.log').read_bytes()).hexdigest())
 def test_completed_report_rejected(self):
  Path(self.row['report']).write_text('{}')
  with self.assertRaises(ValueError):self.review()
 def test_completed_preflight_rejected(self):
  p=self.work/'candidate/receipt.json';r=json.loads(p.read_text());r['preflight']={};p.write_text(json.dumps(r))
  with self.assertRaises(ValueError):self.review()
 def make_initial_drain_failure(self):
  (self.work/'candidate/receipt.json').unlink();(self.work/'candidate').rmdir()
  (self.work/'worker.log').write_text("Traceback (most recent call last):\n p, token = hold(); ready(p)\nRuntimeError: expected drained, got {'state': 'drain_timeout', 'time': 123.4}\n")
  self.digest=hashlib.sha256((self.work/'worker.log').read_bytes()).hexdigest()
 def test_initial_drain_review_preserves_failure(self):
  self.make_initial_drain_failure();r=self.review()
  self.assertIn('before capture',r['rationale'])
 def test_drain_with_candidate_rejected(self):
  self.make_initial_drain_failure();(self.work/'candidate').mkdir()
  with self.assertRaises(ValueError):self.review()
 def test_drain_after_external_started_rejected(self):
  self.make_initial_drain_failure();p=self.work/'worker.log';p.write_text(p.read_text().replace(' p, token', ' in run_external\n p, token'))
  self.digest=hashlib.sha256(p.read_bytes()).hexdigest()
  with self.assertRaises(ValueError):self.review()
if __name__=='__main__':unittest.main()
