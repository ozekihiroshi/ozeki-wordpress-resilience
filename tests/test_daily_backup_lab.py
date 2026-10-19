import importlib.util
import json
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location('daily', ROOT / 'tools/daily-backup-lab.py')
d = importlib.util.module_from_spec(s)
s.loader.exec_module(d)
NOW = datetime(2026, 10, 19, 0, tzinfo=timezone.utc)


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.c = d.Coordinator(self.tmp.name)
        self.calls = 0
        self.report = {'format': 'owr-wordpress-consistency-lab-v1', 'all_passed': True, 'resources_removed': True,
                       'results': [{'case': x, 'passed': True} for x in json.loads((ROOT / 'schemas/daily-lab-required-cases.json').read_text())],
                       'external_evidence': {'queue_recovery': {'signed_set': {'aws_calls': 0, 'private_key_retained': False}}}}

    def worker(self, work, report):
        self.calls += 1
        report.write_text(json.dumps(self.report))

    def test_daily_slot_jst_boundary(self):
        self.assertEqual(d.slot(datetime(2026, 10, 18, 17, 59, tzinfo=timezone.utc)), '2026-10-18')
        self.assertEqual(d.slot(datetime(2026, 10, 18, 18, tzinfo=timezone.utc)), '2026-10-19')
        with self.assertRaises(ValueError): d.slot(datetime(2026, 10, 19))

    def test_duplicate_no_second_worker(self):
        first = self.c.tick(NOW, self.worker)
        self.assertEqual(first['state'], 'success')
        self.assertEqual(self.c.tick(NOW, self.worker, retry=True)['id'], first['id'])
        self.assertEqual(self.calls, 1)

    def test_next_day_new_id(self):
        one = self.c.tick(NOW, self.worker)
        two = self.c.tick(NOW + timedelta(days=1), self.worker)
        self.assertNotEqual(one['id'], two['id'])
        self.assertEqual(self.calls, 2)

    def test_preflight_failure_requires_explicit_retry(self):
        def fail(*args): raise d.BeforeStartFailure()
        first = self.c.tick(NOW, fail)
        self.assertEqual(first['state'], 'failed')
        self.assertEqual(self.c.tick(NOW, self.worker)['state'], 'failed')
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.c.tick(NOW, self.worker, retry=True)['state'], 'success')

    def test_unknown_blocks_today_and_tomorrow(self):
        def fail(*args): raise RuntimeError('uncertain PUT')
        self.assertEqual(self.c.tick(NOW, fail)['state'], 'unknown')
        self.assertEqual(self.c.tick(NOW, self.worker, retry=True)['state'], 'unknown')
        self.assertEqual(self.c.tick(NOW + timedelta(days=1), self.worker)['state'], 'unknown')
        self.assertEqual(self.calls, 0)

    def test_missing_report_not_success(self):
        self.assertEqual(self.c.tick(NOW, lambda *args: None)['state'], 'unknown')

    def test_partial_and_cleanup_failure_not_success(self):
        self.report['resources_removed'] = False
        self.assertEqual(self.c.tick(NOW, self.worker)['state'], 'unknown')
        self.report['resources_removed'] = True
        self.report['results'].pop()
        with self.assertRaises(ValueError):
            path = Path(self.tmp.name) / 'bad.json'
            path.write_text(json.dumps(self.report))
            d.verify_report(path)

    def test_reconcile_complete_report_without_rerunning(self):
        def late_failure(work, report):
            self.worker(work, report)
            raise RuntimeError('lost exit status')
        self.assertEqual(self.c.tick(NOW, late_failure)['state'], 'unknown')
        self.assertEqual(self.c.reconcile(d.slot(NOW))['state'], 'success')
        self.assertEqual(self.c.tick(NOW, self.worker)['state'], 'success')
        self.assertEqual(self.calls, 1)

    def test_reconcile_incomplete_does_not_clear_unknown(self):
        self.c.tick(NOW, lambda *a: None)
        with self.assertRaises(FileNotFoundError): self.c.reconcile(d.slot(NOW))
        self.assertEqual(self.c.status(NOW)['runs'][0]['state'], 'unknown')

    def test_process_crash_recovers_unknown(self):
        def child(): self.c.tick(NOW, lambda *args: os._exit(23))
        p = multiprocessing.get_context('fork').Process(target=child)
        p.start(); p.join(10)
        self.assertEqual(p.exitcode, 23)
        self.assertEqual(self.c.status(NOW)['runs'][0]['state'], 'unknown')

    def test_process_lock_prevents_concurrent_work(self):
        def child(queue):
            try:
                self.c.tick(NOW, self.worker)
                queue.put('unexpected')
            except BlockingIOError: queue.put('busy')
        ctx = multiprocessing.get_context('fork')
        q = ctx.Queue()
        with self.c.locked():
            p = ctx.Process(target=child, args=(q,)); p.start(); p.join(10)
            self.assertEqual(q.get(timeout=2), 'busy')
            status = subprocess.run([sys.executable, str(ROOT/'tools/daily-backup-lab.py'), 'status', '--state-dir', self.tmp.name], capture_output=True, text=True, timeout=10)
            self.assertEqual(status.returncode, 2)
            self.assertEqual(json.loads(status.stdout), {'state': 'busy'})
            self.assertEqual(status.stderr, '')

    def test_missed_days_not_backfilled_as_success(self):
        self.c.tick(NOW, self.worker)
        self.c.tick(NOW + timedelta(days=3), self.worker)
        status = self.c.status(NOW + timedelta(days=3))
        self.assertEqual(status['missing_days'], ['2026-10-20', '2026-10-21'])
        self.assertTrue(status['attention_required'])

    def test_clock_rollback_does_not_capture_old_day(self):
        self.c.tick(NOW, self.worker)
        self.assertEqual(self.c.tick(NOW - timedelta(days=1), self.worker)['reason'], 'clock_moved_backwards')
        self.assertEqual(self.calls, 1)
        self.assertTrue(self.c.status(NOW - timedelta(days=1))['attention_required'])

    def test_failed_case_and_wrong_storage_rejected(self):
        path = Path(self.tmp.name) / 'bad.json'
        self.report['results'][0]['passed'] = False
        path.write_text(json.dumps(self.report))
        with self.assertRaises(ValueError): d.verify_report(path)
        self.report['results'][0]['passed'] = True
        self.report['external_evidence']['queue_recovery']['signed_set']['aws_calls'] = 1
        path.write_text(json.dumps(self.report))
        with self.assertRaises(ValueError): d.verify_report(path)


if __name__ == '__main__': unittest.main()
