import importlib.util
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('operations-monitor-lab')
r = load('monitored-restore-lab')
SET = 'AWS-0123456789abcdef'
NOW = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)


class OperationsMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('daily', 'journal'):
            (self.root/name).mkdir()
        self.config = dict(site='isolated-queue-lab', daily_state=str(self.root/'daily'),
                           restore_journal=str(self.root/'journal'), monitor_state=str(self.root/'monitor'),
                           test_inbox=str(self.root/'inbox'), start_day='2026-10-19', pending_seconds=60)
        with self.db() as db:
            db.executescript('''CREATE TABLE settings(key TEXT,value TEXT); INSERT INTO settings VALUES('storage','s3');
                CREATE TABLE runs(day TEXT PRIMARY KEY,state TEXT,report TEXT);
                CREATE TABLE events(n INTEGER PRIMARY KEY,at TEXT,day TEXT,state TEXT);''')

    def db(self):
        return sqlite3.connect(self.root/'daily/state.sqlite')

    def row(self, state, at=NOW-timedelta(minutes=5), day='2026-10-19'):
        work = self.root/'daily'/day
        work.mkdir(exist_ok=True)
        if state == 'awaiting_approval':
            (work/'candidate').mkdir(exist_ok=True)
            (work/'candidate/candidate.json').write_text(json.dumps(dict(expires_at=(NOW+timedelta(days=7)).isoformat())))
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?)', (day,state,str(work/'result.json')))
            db.execute('INSERT INTO events(at,day,state) VALUES(?,?,?)', (at.isoformat(),day,state))
        return work

    def kinds(self, result):
        return {x['kind'] for x in result['open_incidents']}

    def tick(self, now=NOW, send=None):
        return m.tick(self.config, now, send)

    def approved(self, expiry=NOW+timedelta(days=1)):
        work = self.row('approved')
        (work/'approval.json').write_text(json.dumps(dict(state='approved', approval_expires_at=expiry.isoformat())))

    def attempt(self, state, at=NOW-timedelta(hours=1), name='a'):
        (self.root/'journal'/f'{name}.json').write_text(json.dumps(dict(format='owr-restore-attempt-v1',
            attempt_id=name,set_id=SET,started_at=at.isoformat(),state=state)))

    def test_missing_grace_and_persistent_dedup(self):
        self.assertFalse(self.tick(NOW-timedelta(hours=5))['open_incidents'])
        self.assertEqual(self.kinds(self.tick()), {'backup_missing'})
        self.assertEqual(self.tick()['delivered_total'], 1)
        self.assertEqual(len(list((self.root/'inbox').glob('*.json'))), 1)

    def test_pending_starts_at_storage_completion(self):
        self.row('awaiting_approval', NOW)
        self.assertFalse(self.tick()['open_incidents'])
        self.assertEqual(self.kinds(self.tick(NOW+timedelta(seconds=60))), {'approval_pending'})

    def test_approval_expiry_boundary(self):
        self.approved(NOW)
        self.assertEqual(self.kinds(self.tick()), {'approval_expired'})

    def test_unsigned_candidate_deadline_expired(self):
        work = self.row('awaiting_approval')
        (work/'candidate/candidate.json').write_text(json.dumps(dict(expires_at=NOW.isoformat())))
        self.assertEqual(self.kinds(self.tick()), {'approval_pending', 'approval_expired'})

    def test_pending_resolves_after_approval(self):
        self.row('awaiting_approval')
        self.tick()
        self.approved()
        result = self.tick()
        self.assertFalse(result['open_incidents'])
        self.assertEqual(result['delivered_total'], 2)

    def test_failure_and_later_success_same_set(self):
        self.approved()
        self.attempt('failed')
        self.assertEqual(self.kinds(self.tick()), {'restore_failed'})
        self.attempt('running', NOW-timedelta(minutes=1), 'b')
        self.assertIn('restore_failed', self.kinds(self.tick()))
        self.attempt('succeeded', NOW, 'c')
        self.assertFalse(self.tick()['open_incidents'])

    def test_stale_running_attempt(self):
        self.approved()
        self.attempt('running')
        self.assertEqual(self.kinds(self.tick()), {'restore_incomplete'})

    def test_delivery_failure_retry_fifo(self):
        def unavailable(payload):
            raise OSError('secret must not be included')
        self.assertEqual(self.tick(send=unavailable)['undelivered'], 1)
        self.approved()
        result = self.tick()
        self.assertEqual(result['undelivered'], 0)
        self.assertEqual(result['delivered_total'], 2)
        self.assertNotIn('secret', ''.join(p.read_text() for p in (self.root/'inbox').glob('*.json')))

    def test_lost_ack_idempotent_receiver(self):
        def lost_ack(payload):
            m.inbox_delivery(self.root/'inbox', payload)
            raise OSError('lost acknowledgement')
        self.assertEqual(self.tick(send=lost_ack)['undelivered'], 1)
        self.assertEqual(self.tick()['undelivered'], 0)
        self.assertEqual(len(list((self.root/'inbox').glob('*.json'))), 1)

    def test_process_crash_after_receipt(self):
        def crash(payload):
            m.inbox_delivery(self.root/'inbox', payload)
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): self.tick(send=crash)
        self.assertEqual(self.tick()['delivered_total'], 1)
        self.assertEqual(len(list((self.root/'inbox').glob('*.json'))), 1)

    def test_reopened_incident_gets_new_event(self):
        self.row('awaiting_approval')
        self.tick()
        self.approved()
        self.tick()
        self.row('awaiting_approval')
        self.assertEqual(self.tick()['delivered_total'], 3)

    def test_invalid_threshold_rejected(self):
        self.config['pending_seconds'] = -1
        with self.assertRaises(ValueError): self.tick()

    def test_corrupt_source_preserves_incident(self):
        self.tick()
        (self.root/'daily/state.sqlite').write_bytes(b'corrupt')
        self.assertEqual(self.kinds(self.tick()), {'backup_missing', 'source_unreadable'})

    def test_missing_approval_is_fault_not_healthy(self):
        self.row('approved')
        self.assertEqual(self.kinds(self.tick()), {'source_unreadable'})

    def test_corrupt_restore_does_not_resolve_failure(self):
        self.approved()
        self.attempt('failed')
        self.tick()
        (self.root/'journal/a.json').write_text('{}')
        self.assertEqual(self.kinds(self.tick()), {'restore_failed','source_unreadable'})

    def test_read_only_does_not_reclassify_running(self):
        self.row('running')
        self.tick()
        with self.db() as db:
            self.assertEqual(db.execute('SELECT state FROM runs').fetchone()[0], 'running')

    def test_historical_gap_remains(self):
        self.approved()
        self.config['start_day'] = '2026-10-18'
        result = self.tick()
        self.assertEqual(result['open_incidents'][0]['subject'], '2026-10-18')

    def test_configuration_and_clock_rollback_rejected(self):
        self.tick()
        with self.assertRaises(ValueError): self.tick(NOW-timedelta(seconds=1))
        self.config['site'] = 'different'
        with self.assertRaises(ValueError): self.tick()

    def test_all_four_conditions_end_to_end(self):
        self.config['start_day'] = '2026-10-17'
        self.row('awaiting_approval', day='2026-10-18')
        self.approved(NOW)
        self.attempt('failed')
        self.assertEqual(self.kinds(self.tick()), {'backup_missing','approval_pending','approval_expired','restore_failed'})
        self.assertEqual(len(list((self.root/'inbox').glob('*.json'))), 4)

    def test_restore_worker_failure_is_journalled_and_notified(self):
        self.approved()
        report = self.root/'result.json'
        result = r.execute(self.root/'journal', SET, report,
                           lambda: r.process([sys.executable,'-c','raise SystemExit(7)'], self.root/'worker.log'), NOW)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(self.kinds(self.tick()), {'restore_failed'})

    def test_zero_exit_without_report_fails(self):
        result = r.execute(self.root/'journal', SET, self.root/'result.json', lambda: 0, NOW)
        self.assertEqual(result['state'], 'failed')

    def test_existing_report_cannot_be_reused(self):
        path = self.root/'old.json'
        path.write_text('{}')
        with self.assertRaises(ValueError): r.execute(self.root/'journal', SET, path, lambda: 0, NOW)

    def test_timeout_journalled(self):
        result = r.execute(self.root/'journal', SET, self.root/'result.json',
                           lambda: r.process([sys.executable,'-c','import time; time.sleep(60)'], self.root/'timeout.log', timeout=.05), NOW)
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['error_type'], 'TimeoutExpired')

    def test_success_requires_exact_cases_and_set(self):
        required = json.loads((ROOT/'schemas/approved-restore-required-cases.json').read_text())
        report = self.root/'result.json'
        data = dict(format='owr-wordpress-consistency-lab-v1', all_passed=True, resources_removed=True,
                    results=[dict(case=c,passed=True) for c in required],
                    external_evidence={'queue_recovery':{'signed_set':{'set_id':SET,'isolated_restore_verified':True}}})
        def worker():
            report.write_text(json.dumps(data))
            return 0
        result = r.execute(self.root/'journal', SET, report, worker, NOW)
        self.assertEqual(result['state'], 'succeeded')
        data['results'].pop()
        report.write_text(json.dumps(data))
        with self.assertRaises(ValueError): r.validate(report, SET)


if __name__ == '__main__':
    unittest.main()
