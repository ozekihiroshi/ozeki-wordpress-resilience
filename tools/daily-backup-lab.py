#!/usr/bin/env python3
"""Durable daily coordinator for the isolated fixture only (Linux/WSL)."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import secrets
import signal
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def slot(now, hour=3):
    if now.tzinfo is None or not 0 <= hour <= 23:
        raise ValueError('aware time and valid hour required')
    local = now.astimezone(JST)
    return (local.date() - timedelta(days=int(local.hour < hour))).isoformat()


class BeforeStartFailure(Exception):
    """No worker or side effect was started; explicit retry is safe."""


def publication():
    spec = importlib.util.spec_from_file_location('daily_publication', ROOT/'tools/daily-s3-publication.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def verify_report(path, storage='mock'):
    r = json.loads(Path(path).read_text())
    schema = 'daily-s3-required-cases.json' if storage == 's3' else 'daily-lab-required-cases.json'
    required = json.loads((ROOT / 'schemas' / schema).read_text())
    cases = r.get('results', [])
    if (r.get('format') != 'owr-wordpress-consistency-lab-v1'
            or r.get('all_passed') is not True or r.get('resources_removed') is not True
            or len(cases) != len(required) or {c['case'] for c in cases} != set(required)
            or any(c.get('passed') is not True for c in cases)):
        raise ValueError('incomplete lab evidence')
    if storage == 's3':
        recovered = r['external_evidence']['queue_recovery']
        if recovered.get('restore_performed') is not False: raise ValueError('daily publication must not restore')
        publication().verify_saved(Path(path).parent/'candidate', recovered['saved_set'])
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    signed = r['external_evidence']['queue_recovery']['signed_set']
    if signed.get('aws_calls') != 0 or signed.get('private_key_retained') is not False:
        raise ValueError('not the isolated mock-storage contract')
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Coordinator:
    def __init__(self, directory, storage='mock'):
        if storage not in ('mock', 's3'): raise ValueError('invalid storage')
        self.storage = storage
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def locked(self):
        with (self.root / 'coordinator.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with sqlite3.connect(self.root / 'state.sqlite') as db:
                db.row_factory = sqlite3.Row
                db.execute('PRAGMA synchronous=FULL')
                db.execute('CREATE TABLE IF NOT EXISTS runs(day TEXT PRIMARY KEY, id TEXT UNIQUE, state TEXT, report TEXT, reason TEXT, digest TEXT)')
                db.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)')
                existing = db.execute("SELECT value FROM settings WHERE key='storage'").fetchone()
                if existing and existing[0] != self.storage: raise ValueError('state directory storage mode mismatch')
                if not existing:
                    if self.storage == 's3' and db.execute('SELECT 1 FROM runs').fetchone(): raise ValueError('cannot reuse legacy state for S3')
                    db.execute("INSERT INTO settings VALUES('storage',?)", (self.storage,))
                    db.commit()
                db.execute('CREATE TABLE IF NOT EXISTS events(n INTEGER PRIMARY KEY, at TEXT, day TEXT, state TEXT, reason TEXT)')
                # Holding the OS lock proves that the previous coordinator exited.
                for row in db.execute("SELECT day FROM runs WHERE state='running'").fetchall():
                    self.change(db, row['day'], 'unknown', 'coordinator_interrupted')
                yield db

    def change(self, db, day, state, reason, digest=None):
        db.execute('UPDATE runs SET state=?,reason=?,digest=? WHERE day=?', (state, reason, digest, day))
        db.execute('INSERT INTO events(at,day,state,reason) VALUES(?,?,?,?)', (datetime.now(timezone.utc).isoformat(), day, state, reason))
        db.commit()

    def tick(self, now, worker, retry=False, hour=3):
        day = slot(now, hour)
        with self.locked() as db:
            # An unresolved previous day blocks new writes, including next-day runs.
            if db.execute("SELECT 1 FROM runs WHERE state='unknown'").fetchone():
                return {'state': 'unknown', 'reason': 'operator_review_required'}
            old = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            latest = db.execute('SELECT MAX(day) FROM runs').fetchone()[0]
            if latest and day < latest:
                return {'state': 'unknown', 'reason': 'clock_moved_backwards'}
            if old and (old['state'] in ('success', 'awaiting_approval', 'approved') or not retry):
                return dict(old)
            if old and old['state'] != 'failed':
                raise ValueError('retry requires a proven failure before storage started')
            ident = 'daily-' + secrets.token_hex(12)
            work = self.root / ident
            work.mkdir(mode=0o700)
            report = work / 'result.json'
            db.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?,?,?)', (day, ident, 'running', str(report), 'started', None))
            self.change(db, day, 'running', 'started')
            try:
                worker(work, report)
                digest = verify_report(report, self.storage)
            except BeforeStartFailure:
                self.change(db, day, 'failed', 'preflight_failed_no_worker_started')
            except Exception:
                # Never infer that a failed process made no storage changes.
                self.change(db, day, 'unknown', 'worker_or_evidence_incomplete')
            else:
                state = 'awaiting_approval' if self.storage == 's3' else 'success'
                self.change(db, day, state, 'stored_unsigned' if self.storage == 's3' else 'isolated_restore_verified', digest)
            return dict(db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone())

    def review_prepublication_failure(self, day, run_id, log_sha256, reviewer):
        """Explicit operator review of known lab failures before storage only.

        Logs are operator-reviewed local evidence, not a security attestation.
        Never use this to retry an uncertain storage request.
        """
        if self.storage != 's3' or not reviewer.strip():
            raise ValueError('S3 operator review required')
        with self.locked() as db:
            row = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            if not row or row['state'] != 'unknown' or row['id'] != run_id:
                raise ValueError('review must identify the unknown run')
            work = Path(row['report']).parent
            raw = (work/'worker.log').read_bytes()
            if hashlib.sha256(raw).hexdigest() != log_sha256:
                raise ValueError('reviewed log changed')
            trace = raw.decode().split('Traceback (most recent call last):')[-1]
            directory = work/'candidate'
            before_capture = ("p, token = hold(); ready(p)" in trace
                and re.search(r"RuntimeError: expected drained, got \{'state': 'drain_timeout', 'time': [0-9.]+\}\s*$", trace)
                and not directory.exists()
                and 'run_external' not in trace and 'in publish' not in trace)
            if Path(row['report']).exists():
                raise ValueError('completed report requires reconciliation')
            if not before_capture:
                required = ["receipt['preflight'] = (preflight or transport.preflight)()", "in preflight", "in authorize"]
                if (not all(x in trace for x in required) or
                    not trace.rstrip().endswith('RuntimeError: EC2 authorization failed for writer; sensitive details suppressed')):
                    raise ValueError('not a reviewed failure before storage')
                if set(x.name for x in directory.iterdir()) != {'receipt.json'}:
                    raise ValueError('additional publication evidence requires reconciliation')
                receipt = json.loads((directory/'receipt.json').read_text())
                if (receipt.get('storage_complete') is not False or receipt.get('restore_allowed') is not False
                        or receipt.get('error_type') != 'RuntimeError' or 'preflight' in receipt):
                    raise ValueError('unexpected publication receipt')
            source = ROOT/'tools/daily-s3-publication.py'
            review = dict(format='owr-prepublication-operator-review-v1', day=day, run_id=run_id,
                          reviewer=reviewer, log_sha256=log_sha256,
                          publication_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          rationale=('Reviewed initial writer drain timeout before capture and publication' if before_capture else 'Reviewed writer authorization failure before adapter construction and PUT'),
                          fixture_source_sha256=hashlib.sha256((ROOT/'tools/run-wordpress-consistency-lab.py').read_bytes()).hexdigest(),
                          previous_state='unknown', automatic_retry=False)
            # Preserve the reviewed attempt and its evidence even after the next run replaces the daily row.
            with (work/'operator-review.json').open('x') as f:
                json.dump(review, f, indent=2); f.flush(); os.fsync(f.fileno())
            self.change(db, day, 'failed', 'operator_reviewed_failure_before_storage_started')
            return review

    def reconcile(self, day):
        with self.locked() as db:
            row = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            if not row or row['state'] != 'unknown':
                raise ValueError('only an unknown run can be reconciled')
            digest = verify_report(row['report'], self.storage)
            state = 'awaiting_approval' if self.storage == 's3' else 'success'
            self.change(db, day, state, 'operator_reconciled_complete_evidence', digest)
            return {'state': state, 'day': day}

    def approve(self, day, signature, public_key, expected_hash, expected_key_hash, operator_dir):
        if self.storage != 's3': raise ValueError('approval requires S3 state')
        if Path(operator_dir).resolve().is_relative_to(self.root): raise ValueError('operator trust must be outside daily state')
        with self.locked() as db:
            row = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            if not row or row['state'] != 'awaiting_approval': raise ValueError('no pending approval')
            if verify_report(row['report'], self.storage) != row['digest']: raise ValueError('stored report changed')
            work = Path(row['report']).parent
            try:
                approved = publication().approve(work/'candidate/candidate.json', signature, public_key, expected_hash, expected_key_hash, operator_dir)
            except Exception:
                self.change(db, day, 'awaiting_approval', 'approval_rejected_or_read_failed', row['digest'])
                raise
            publication().write_json(work/'approval.json', approved)
            self.change(db, day, 'approved', 'independent_signature_and_fixed_versions_verified', row['digest'])
            return approved

    def status(self, now, hour=3):
        with self.locked() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY day')]
            due = slot(now, hour)
            complete = [r['day'] for r in rows if r['state'] in ('success', 'awaiting_approval', 'approved')]
            pending = [r['day'] for r in rows if r['state'] == 'awaiting_approval']
            expired = []
            for r in rows:
                if r['state'] == 'approved':
                    try:
                        approval = json.loads((Path(r['report']).parent/'approval.json').read_text())
                        if datetime.fromisoformat(approval['approval_expires_at']) <= now: expired.append(r['day'])
                    except Exception: expired.append(r['day'])
            last = max(complete, default=None)
            missing = []
            if rows:
                day = datetime.fromisoformat(rows[0]['day']).date()
                while day.isoformat() <= due:
                    if day.isoformat() not in complete:
                        missing.append(day.isoformat())
                    day += timedelta(days=1)
            elif not last:
                missing = [due]
            return {'due_day': due, 'last_success_day': max([r['day'] for r in rows if r['state'] == 'success'], default=None), 'last_storage_complete_day': last, 'last_approved_day': max([r['day'] for r in rows if r['state'] == 'approved'], default=None), 'storage': self.storage, 'awaiting_approval_days': pending, 'expired_or_unreadable_approval_days': expired, 'attention_required': due not in complete or bool(missing) or bool(pending) or bool(expired) or any(r['state'] == 'unknown' for r in rows), 'missing_days': missing, 'runs': rows}


def lab_worker(work, report, storage='mock'):
    try:
        for args in [('docker', 'info'), ('docker', 'image', 'inspect', 'owr-external-lab:local')]:
            subprocess.run(args, check=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        (work / 'preflight.json').write_text(json.dumps({'command': list(args), 'error_type': type(exc).__name__, 'worker_started': False}) + '\n')
        raise BeforeStartFailure() from exc
    command = [sys.executable, '-u', str(ROOT / 'tools/run-wordpress-consistency-lab.py'), '--execute-lab', '--external', '--lab-image', 'owr-external-lab:local', '--output', str(report)]
    if storage == 's3': command += ['--daily-s3-stage', str(work/'candidate')]
    with (work / 'worker.log').open('xb') as log:
        p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            if p.wait(timeout=1800) != 0:
                raise RuntimeError('lab worker failed')
        finally:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGTERM)
                try:
                    p.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['tick', 'status', 'reconcile', 'approve'])
    p.add_argument('--state-dir', type=Path, required=True)
    p.add_argument('--execute-lab', action='store_true')
    p.add_argument('--retry-failed', action='store_true')
    p.add_argument('--day')
    p.add_argument('--hour-jst', type=int, default=3, choices=range(24))
    p.add_argument('--storage', choices=['mock','s3'], default='mock')
    p.add_argument('--signature', type=Path)
    p.add_argument('--trusted-public-key', type=Path)
    p.add_argument('--expected-document-sha256')
    p.add_argument('--expected-key-sha256')
    p.add_argument('--operator-dir', type=Path)
    a = p.parse_args()
    if a.action == 'approve' and not all([a.day,a.signature,a.trusted_public_key,a.expected_document_sha256,a.expected_key_sha256,a.operator_dir]): p.error('approval requires day, signature, operator-selected public key, both independent hashes and operator directory')
    if a.action == 'tick' and not a.execute_lab:
        p.error('tick requires --execute-lab')
    c = Coordinator(a.state_dir, a.storage)
    now = datetime.now(timezone.utc)
    try:
        if a.action == 'tick':
            result = c.tick(now, lambda work,report: lab_worker(work,report,a.storage), a.retry_failed, a.hour_jst)
        elif a.action == 'approve':
            result = c.approve(a.day,a.signature,a.trusted_public_key,a.expected_document_sha256,a.expected_key_sha256,a.operator_dir)
        elif a.action == 'reconcile':
            result = c.reconcile(a.day)
        else:
            result = c.status(now, a.hour_jst)
    except BlockingIOError:
        result = {'state': 'busy'}
    print(json.dumps(result, indent=2))
    return 0 if result.get('state') in ('success','awaiting_approval','approved') or (a.action == 'status' and not result.get('attention_required', True)) else 2


if __name__ == '__main__':
    sys.exit(main())
