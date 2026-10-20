#!/usr/bin/env python3
"""Daily two-asset coordinator for generated first-site fixtures (Linux/WSL)."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sqlite3
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load('first_daily_gate', 'protected-first-site-set.py')
transport = load('first_daily_transport', 'queue-s3-adapter.py')
schedule = load('first_daily_schedule', 'daily-backup-lab.py')
io = load('first_daily_io', 'daily-s3-publication.py')
observations = load('first_restore_observations', 'first-site-restore-observations.py')
SITE = 'isolated-queue-lab'
FORMAT = 'owr-first-site-daily-v1'


def publish(work, capture, assets, adapter_factory=None, preflight=None):
    """Only a verified capture may reach PUT. No private key or signing callback."""
    gate.check(capture['site_id'] == 'generated-first-site', 'generated fixture only')
    gate.validate_capture(capture, assets)
    gate.check(sum(map(len, assets.values())) <= 128 * 1024**2, 'lab size limit')
    work = Path(work)
    set_id = 'AWS-' + secrets.token_hex(8)
    receipt = dict(format=FORMAT, set_id=set_id, storage_complete=False,
                   approval_state='pending', restore_allowed=False,
                   signature_created=False, production_recovery_approved=False)
    io.write_json(work / 'receipt.json', receipt)
    try:
        (preflight or transport.preflight)()
        adapter = (adapter_factory or transport.S3Adapter)(work / 'transfer-receipts')
        manifest = gate.build(assets, capture, SITE, set_id, transport.BUCKET,
                              transport.REGION, 'my-ssm-role', 'OwrM1RecoveryReader',
                              adapter.put, adapter.get)
        io.write_json(work / 'candidate.json', manifest)
        receipt.update(storage_complete=True,
                       manifest_sha256=gate.sha((work / 'candidate.json').read_bytes()),
                       config_sha256=capture['config_sha256'],
                       approval_expires_at=manifest['expires_at'],
                       minimum_retention_until=manifest['minimum_retention_until'])
        io.write_json(work / 'receipt.json', receipt)
        return receipt
    except Exception as exc:
        receipt['error_type'] = type(exc).__name__
        io.write_json(work / 'receipt.json', receipt)
        raise


def verify_saved(work):
    """Check durable local receipt bindings. Signature approval is a separate action."""
    work = Path(work)
    r = json.loads((work / 'receipt.json').read_bytes())
    gate.check(r['format'] == FORMAT and r['storage_complete'] is True
               and r['approval_state'] == 'pending' and r['restore_allowed'] is False
               and r['signature_created'] is False
               and r['production_recovery_approved'] is False, 'incomplete storage')
    raw = (work / 'candidate.json').read_bytes()
    gate.check(len(raw) < 65536 and gate.sha(raw) == r['manifest_sha256'], 'candidate changed')
    m = json.loads(raw)
    gate.check(m['format'] == gate.FORMAT and m['site_id'] == SITE
               and m['set_id'] == r['set_id']
               and m['paired']['site_id'] == 'generated-first-site'
               and m['paired']['config_sha256'] == r['config_sha256'], 'candidate target changed')
    gate.check(m['expires_at'] == r['approval_expires_at']
               and m['minimum_retention_until'] == r['minimum_retention_until'], 'deadline changed')
    gate.check(len(m['assets']) == 2 and {e['role'] for e in m['assets']} == set(gate.NAMES), 'two assets required')
    operations = json.loads((work / 'transfer-receipts' / 'operations.json').read_bytes())
    puts = [e for e in operations if e['method'] == 'PUT']
    gate.check(len(puts) == 2 and all(e['state'] == 'acknowledged' for e in puts), 'uncertain/incomplete PUT')
    for e in m['assets']:
        loc = e['locator']
        gate.check(loc['bucket'] == transport.BUCKET and loc['region'] == transport.REGION
                   and loc['key'] == f"sites/{SITE}/sets/{m['set_id']}/{gate.NAMES[e['role']]}"
                   and loc['version_id'] not in ('', 'null', None), 'invalid locator')
        def matches(op):
            return all(op.get(k) == v for k, v in dict(key=loc['key'], version_id=loc['version_id'],
                                                       sha256=loc['sha256'], bytes=loc['size_bytes']).items())
        gate.check(sum(matches(p) for p in puts) == 1, 'PUT receipt mismatch')
        gate.check(any(e['method'] == 'GET' and matches(e)
                       for e in operations), 'independent read receipt missing')
    return r


class Coordinator:
    def __init__(self, directory):
        self.root = Path(directory).resolve()
        gate.check(not (self.root / 'state.sqlite').exists(), 'existing three-asset ledger cannot be reused')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def locked(self):
        with (self.root / 'daily.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Keep the lock across capture/transfer; interruption cannot cause an automatic retry.
            with sqlite3.connect(self.root / 'daily.sqlite') as db:
                db.row_factory = sqlite3.Row
                db.execute('PRAGMA synchronous=FULL')
                db.execute('CREATE TABLE IF NOT EXISTS metadata(format TEXT NOT NULL)')
                row = db.execute('SELECT format FROM metadata').fetchone()
                if row:
                    gate.check(row[0] == FORMAT, 'wrong ledger format')
                else:
                    db.execute('INSERT INTO metadata VALUES(?)', (FORMAT,))
                db.execute('CREATE TABLE IF NOT EXISTS runs(day TEXT PRIMARY KEY,id TEXT,state TEXT,reason TEXT,digest TEXT)')
                db.execute('CREATE TABLE IF NOT EXISTS events(n INTEGER PRIMARY KEY,at TEXT,day TEXT,state TEXT,reason TEXT)')
                db.commit()
                for row in db.execute("SELECT day FROM runs WHERE state='running'").fetchall():
                    self.change(db, row['day'], 'unknown', 'interrupted_no_automatic_retry')
                yield db

    def change(self, db, day, state, reason, digest=None):
        db.execute('UPDATE runs SET state=?,reason=?,digest=? WHERE day=?', (state, reason, digest, day))
        db.execute('INSERT INTO events(at,day,state,reason) VALUES(?,?,?,?)',
                   (gate.now().isoformat(), day, state, reason))
        db.commit()

    def tick(self, now, capture_worker, adapter_factory=None, preflight=None):
        day = schedule.slot(now)
        with self.locked() as db:
            if db.execute("SELECT 1 FROM runs WHERE state='unknown'").fetchone():
                return dict(state='unknown', reason='operator_review_required')
            last = db.execute('SELECT MAX(day) FROM runs').fetchone()[0]
            if last and day < last:
                return dict(state='unknown', reason='clock_moved_backwards')
            old = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            if old:
                return dict(old)
            ident = 'first-daily-' + secrets.token_hex(12)
            work = self.root / ident
            work.mkdir(mode=0o700)
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?)', (day, ident, 'running', 'started', None))
            self.change(db, day, 'running', 'capture_started')
            try:
                capture, assets = capture_worker(work)
                publish(work, capture, assets, adapter_factory, preflight)
                receipt = verify_saved(work)
            except Exception as exc:
                io.write_json(work / 'failure.json', dict(error_type=type(exc).__name__,
                                                        at=gate.now().isoformat(), automatic_retry=False))
                self.change(db, day, 'unknown', 'capture_or_storage_incomplete_no_automatic_retry')
            else:
                self.change(db, day, 'awaiting_approval', 'stored_unsigned',
                            gate.sha((work / 'receipt.json').read_bytes()))
            return dict(db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone())

    def reconcile(self, day):
        """Explicit local evidence review; never re-PUT or manufacture missing receipts."""
        with self.locked() as db:
            row = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            gate.check(row is not None and row['state'] == 'unknown', 'unknown run required')
            work = self.root / row['id']
            verify_saved(work)
            self.change(db, day, 'awaiting_approval', 'stored_evidence_reconciled',
                        gate.sha((work / 'receipt.json').read_bytes()))

    def approve(self, day, trust, expected_document_hash, expected_key_hash, adapter_factory=None):
        trust = Path(trust).resolve()
        gate.check(not trust.is_relative_to(self.root) and not self.root.is_relative_to(trust),
                   'independent operator directory required')
        with self.locked() as db:
            row = db.execute('SELECT * FROM runs WHERE day=?', (day,)).fetchone()
            gate.check(row is not None and row['state'] == 'awaiting_approval', 'pending run required')
            work = self.root / row['id']
            gate.check(gate.sha((work / 'receipt.json').read_bytes()) == row['digest'], 'receipt changed')
            r = verify_saved(work)
            doc, sig = trust / 'approved.json', trust / 'approved.sig'
            gate.check(gate.sha(doc.read_bytes()) == expected_document_hash == r['manifest_sha256'],
                       'operator document pin mismatch')
            gate.check(gate.sha((trust / 'public.pem').read_bytes()) == expected_key_hash,
                       'operator public key pin mismatch')
            # Reject invalid/expired signatures before any network request.
            gate.authorize(trust, doc, sig, SITE, r['set_id'])
            adapter = (adapter_factory or transport.S3Adapter)(work / ('approval-read-' + secrets.token_hex(8)))
            _, verification = gate.fetch_verified(trust, doc, sig, SITE, r['set_id'],
                                                  r['config_sha256'], adapter.get)
            approval = dict(state='approved', approved_at=gate.now().isoformat(),
                            manifest_sha256=expected_document_hash, public_key_sha256=expected_key_hash,
                            approval_expires_at=r['approval_expires_at'], verification=verification,
                            isolated_restore_verified=False, production_recovery_approved=False)
            io.write_json(work / 'approval.json', approval)
            self.change(db, day, 'approved', 'independent_signature_and_fixed_versions_verified', row['digest'])
            return approval

    def record_restore(self, day, directory, expected_hash):
        api = SimpleNamespace(gate=gate, verify_saved=verify_saved, SITE=SITE, load=load)
        return observations.register(self, day, directory, expected_hash, api)

    def status(self, now):
        # status does not initialize, reconcile, or mutate the ledger.
        gate.check(now.tzinfo is not None, 'timezone required')
        path = self.root / 'daily.sqlite'
        rows = []
        restore_records = []
        recovery_attempts = []
        if path.exists():
            with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
                db.row_factory = sqlite3.Row
                rows = [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY day')]
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='recovery_attempts'").fetchone():
                    recovery_attempts = [dict(r) for r in db.execute('SELECT n,request_id,day,state,outcome,registration,error_type FROM recovery_attempts ORDER BY n')]
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='restore_observations'").fetchone():
                    restore_records = [dict(r) for r in db.execute('SELECT * FROM restore_observations ORDER BY n')]
        for row in rows:
            row.update(storage_complete=False, approval_state='unverified', restore_allowed=False)
            if row['state'] in ('awaiting_approval', 'approved'):
                try:
                    work = self.root / row['id']
                    r = verify_saved(work)
                    gate.check(gate.sha((work / 'receipt.json').read_bytes()) == row['digest'], 'receipt changed')
                    if row['state'] == 'approved':
                        a = json.loads((work / 'approval.json').read_bytes())
                        gate.check(a['state'] == 'approved'
                                   and a['manifest_sha256'] == r['manifest_sha256']
                                   and a['approval_expires_at'] == r['approval_expires_at']
                                   and a['verification']['passed'] is True
                                   and a['production_recovery_approved'] is False, 'approval record changed')
                    row['manifest_sha256'] = r['manifest_sha256']
                    if row['state'] == 'approved':
                        row['approved_key_sha256'] = a['public_key_sha256']
                    row['storage_complete'] = True
                    row['approval_state'] = ('expired' if gate.date(r['approval_expires_at']) <= now else
                                             'approved' if row['state'] == 'approved' else 'pending')
                    row['approval_expires_at'] = r['approval_expires_at']
                    # A status result is not authorization; recovery must reverify independent trust.
                except Exception:
                    row['evidence_error'] = True
            observations.aggregate(row, [r for r in restore_records if r['day']==row['day']],
                                   SimpleNamespace(gate=gate))
            attempts = [a for a in recovery_attempts if a['day']==row['day']]
            row['recovery_attempt'] = attempts[-1] if attempts else None
            attempt = row['recovery_attempt'] or {}
            row['phase'] = ('evidence_error' if row.get('evidence_error') or row.get('restore_evidence_error')
                            else 'approval_expired' if row['approval_state']=='expired'
                            else 'recovery_reviewed_closed' if attempt.get('state')=='reviewed_closed'
                            else 'recovery_running' if attempt.get('state')=='running'
                            else 'recovery_interrupted' if attempt.get('state')=='interrupted'
                            else 'registration_pending' if attempt.get('registration')=='pending'
                            else 'restore_failed' if attempt.get('outcome')=='failed'
                            else 'restore_failed' if row['approval_state']=='approved' and row['restore_state']=='failed'
                            else 'restore_verified' if row['approval_state']=='approved' and row['restore_verified']
                            else 'approved' if row['approval_state']=='approved'
                            else 'awaiting_approval' if row['approval_state']=='pending'
                            else row['state'])
        return dict(format=FORMAT, due_day=schedule.slot(now), runs=rows,
                    missing_due_slot=not any(r['day'] == schedule.slot(now) and r['storage_complete'] for r in rows),
                    production_recovery_approved=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    p = sub.add_parser('reconcile'); p.add_argument('--day', required=True)
    p = sub.add_parser('record-restore')
    p.add_argument('--day', required=True)
    p.add_argument('--directory', required=True)
    p.add_argument('--report-sha256', required=True)
    p = sub.add_parser('approve')
    for arg in ('day', 'trust', 'document-sha256', 'key-sha256'):
        p.add_argument('--' + arg, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    c = Coordinator(args.state)
    if args.command == 'status':
        result = c.status(gate.now())
    elif args.command == 'reconcile':
        c.reconcile(args.day); result = c.status(gate.now())
    elif args.command == 'record-restore':
        result = c.record_restore(args.day, args.directory, args.report_sha256)
    else:
        result = c.approve(args.day, args.trust, args.document_sha256, args.key_sha256)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
