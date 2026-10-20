import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('daily', ROOT / 'tools/first-site-daily.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)


class Daily(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.c = d.Coordinator(self.root / 'daily')
        self.now = d.gate.now()
        self.assets = {'database': b'sql', 'files': b'archive'}
        self.capture = dict(format='owr-first-site-capture-v1', attempt_id='a'*32,
                            site_id='generated-first-site', config_sha256='b'*64,
                            state='consistent', eligible_for_consistency_acceptance=True,
                            release_confirmed=True, production_recovery_approved=False,
                            queue=dict(state='absent', evidence='isolated'),
                            assets={k: dict(attempt_id='a'*32, bytes=len(v), sha256=d.gate.sha(v))
                                    for k, v in self.assets.items()})
        self.store = {}; self.puts = 0; self.gets = 0; self.fail = False
        self.modified = self.now.isoformat()
        self.until = (self.now + dt.timedelta(days=36)).isoformat()
        owner = self
        class Adapter:
            def __init__(self, path):
                self.path = path; path.mkdir(); self.ops = []
            def save(self):
                d.io.write_json(self.path / 'operations.json', self.ops)
            def put(self, bucket, key, body):
                owner.puts += 1
                event = dict(method='PUT', key=key, sha256=d.gate.sha(body), bytes=len(body), state='started')
                self.ops.append(event); self.save()
                owner.store[key] = body
                if owner.fail:
                    raise TimeoutError('ambiguous remote outcome')
                event.update(state='acknowledged', version_id='v1'); self.save()
                return 'v1'
            def get(self, loc):
                owner.gets += 1
                body = owner.store[loc['key']]
                self.ops.append(dict(method='GET', key=loc['key'], bytes=len(body),
                                     sha256=d.gate.sha(body), version_id='v1'))
                self.save()
                return dict(body=body, version_id='v1', reader_identity='OwrM1RecoveryReader',
                            mode='GOVERNANCE', last_modified=owner.modified, retain_until=owner.until)
        self.adapter = Adapter
    def tearDown(self):
        self.tmp.cleanup()
    def tick(self, now=None):
        return self.c.tick(now or self.now, lambda w: (self.capture, self.assets), self.adapter, lambda: None)
    def test_pending_and_duplicate(self):
        r = self.tick()
        self.assertEqual(r['state'], 'awaiting_approval')
        self.assertEqual(self.tick(), r); self.assertEqual(self.puts, 2)
        s = self.c.status(self.now)['runs'][0]
        self.assertTrue(s['storage_complete']); self.assertEqual(s['approval_state'], 'pending')
        self.assertFalse(s['restore_allowed'])
        self.assertFalse(list(self.c.root.rglob('*.pem')))
    def test_uncertain_put_blocks_next_day(self):
        self.fail = True
        self.assertEqual(self.tick()['state'], 'unknown')
        self.assertEqual(self.tick(self.now+dt.timedelta(days=1))['state'], 'unknown')
        self.assertEqual(self.puts, 1)
        with self.assertRaises((ValueError, KeyError, FileNotFoundError)):
            self.c.reconcile(d.schedule.slot(self.now))
    def test_bad_capture_never_put(self):
        self.capture['release_confirmed'] = False
        self.assertEqual(self.tick()['state'], 'unknown'); self.assertEqual(self.puts, 0)
    def test_lock_refuses_overlap(self):
        with self.c.locked():
            with self.assertRaises(BlockingIOError):
                self.tick()
        self.assertEqual(self.puts, 0)
    def test_interrupted_blocks_new_capture(self):
        with self.c.locked() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?)',
                       (d.schedule.slot(self.now), 'crashed', 'running', 'started', None))
            db.commit()
        self.assertEqual(self.tick()['state'], 'unknown'); self.assertEqual(self.puts, 0)
    def test_receipt_commit_crash_reconcile_without_put(self):
        original = d.verify_saved
        with patch.object(d, 'verify_saved', side_effect=OSError('simulated crash after durable receipt')):
            r = self.tick()
        self.assertEqual(r['state'], 'unknown')
        d.verify_saved = original
        self.c.reconcile(r['day'])
        self.assertEqual(self.tick()['state'], 'awaiting_approval'); self.assertEqual(self.puts, 2)
    def test_mutated_candidate_status_and_approval_rejected(self):
        r = self.tick()
        (self.c.root / r['id'] / 'candidate.json').write_text('{}')
        s = self.c.status(self.now)['runs'][0]
        self.assertFalse(s['storage_complete']); self.assertTrue(s['evidence_error'])
        with self.assertRaises(ValueError):
            self.c.approve(r['day'], self.root / 'operator', 'x', 'y', self.adapter)
    def test_separate_signature_approval_and_expiry(self):
        r = self.tick()
        work = self.c.root / r['id']; trust = self.root / 'operator'
        subprocess.run(['python3', str(ROOT/'tools/first-site-lab-sign.py'), '--candidate',
                        str(work/'candidate.json'), '--operator', str(trust)],
                       check=True, capture_output=True)
        document_hash = d.gate.sha((trust/'approved.json').read_bytes())
        key_hash = d.gate.sha((trust/'public.pem').read_bytes())
        signature = (trust/'approved.sig').read_bytes()
        (trust/'approved.sig').write_bytes(b'bad')
        gets = self.gets
        with self.assertRaises(ValueError):
            self.c.approve(r['day'], trust, document_hash, key_hash, self.adapter)
        self.assertEqual(self.gets, gets)
        self.assertEqual(self.c.status(self.now)['runs'][0]['approval_state'], 'pending')
        (trust/'approved.sig').write_bytes(signature)
        result = self.c.approve(r['day'], trust, document_hash, key_hash, self.adapter)
        self.assertEqual(result['state'], 'approved')
        self.assertFalse(result['isolated_restore_verified'])
        self.assertEqual(self.c.status(self.now+dt.timedelta(days=8))['runs'][0]['approval_state'], 'expired')
    def test_status_does_not_mutate_ledger(self):
        self.tick()
        p = self.c.root/'daily.sqlite'; before = p.read_bytes()
        self.c.status(self.now)
        self.assertEqual(p.read_bytes(), before)
    def test_clock_rollback_and_next_slot(self):
        self.tick()
        self.assertEqual(self.tick(self.now-dt.timedelta(days=1))['reason'], 'clock_moved_backwards')
        self.assertEqual(self.puts, 2)
        self.assertEqual(self.tick(self.now+dt.timedelta(days=1))['state'], 'awaiting_approval')
        self.assertEqual(self.puts, 4)
    def test_existing_soak_ledger_rejected(self):
        wrong = self.root/'soak'; wrong.mkdir(); (wrong/'state.sqlite').touch()
        with self.assertRaises(ValueError):
            d.Coordinator(wrong)
    def test_missing_approval_record_not_displayed_as_approved(self):
        r = self.tick()
        with self.c.locked() as db:
            self.c.change(db, r['day'], 'approved', 'injected_missing_evidence', r['digest'])
        status = self.c.status(self.now)['runs'][0]
        self.assertEqual(status['approval_state'], 'unverified')
        self.assertTrue(status['evidence_error'])


if __name__ == '__main__':
    unittest.main()
