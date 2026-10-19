#!/usr/bin/env python3
"""Journal an isolated approved-set restore, including nonzero exits and lost workers."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def write(path, data):
    temp = path.with_suffix('.tmp')
    with temp.open('w') as out:
        os.chmod(temp, 0o600)
        json.dump(data, out, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate(report, set_id):
    data = json.loads(report.read_text())
    required = json.loads((ROOT / 'schemas/approved-restore-required-cases.json').read_text())
    results = data['results']
    if (data['format'] != 'owr-wordpress-consistency-lab-v1' or data['all_passed'] is not True
            or data['resources_removed'] is not True or len(results) != len(required)
            or {r['case'] for r in results} != set(required) or any(r['passed'] is not True for r in results)):
        raise ValueError('incomplete restore report')
    signed = data['external_evidence']['queue_recovery']['signed_set']
    if signed['set_id'] != set_id or signed['isolated_restore_verified'] is not True:
        raise ValueError('wrong restore set')
    return hashlib.sha256(report.read_bytes()).hexdigest()


def execute(journal, set_id, report, worker, now=None):
    if not re.fullmatch(r'AWS-[0-9a-f]{16}', set_id):
        raise ValueError('dedicated AWS lab set required')
    if report.exists():
        raise ValueError('report must be a new path')
    journal.mkdir(parents=True, exist_ok=True, mode=0o700)
    attempt = uuid.uuid4().hex
    path = journal / (attempt + '.json')
    record = dict(format='owr-restore-attempt-v1', attempt_id=attempt, set_id=set_id,
                  started_at=(now or datetime.now(timezone.utc)).isoformat(), state='running')
    write(path, record)
    try:
        if worker() != 0:
            raise RuntimeError('restore worker exited unsuccessfully')
        record['report_sha256'] = validate(report, set_id)
        record['state'] = 'succeeded'
    except Exception as exc:
        record['state'] = 'failed'
        record['error_type'] = type(exc).__name__
        # A failure does not prove cleanup. Operator checks only this attempt's log.
        record['cleanup_verified'] = False
    record['finished_at'] = datetime.now(timezone.utc).isoformat()
    write(path, record)
    return record


def process(command, log, timeout=1800):
    with log.open('xb') as out:
        child = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return child.wait(timeout=timeout)
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--journal', type=Path, required=True)
    p.add_argument('--execute-lab', action='store_true', required=True)
    for name in ('approved-trust', 'approved-set-id', 'approved-document-sha256', 'approved-key-sha256', 'approved-read-receipts', 'output'):
        p.add_argument('--' + name, required=True)
    a = p.parse_args()
    report = Path(a.output)
    report.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-u', str(ROOT/'tools/run-wordpress-consistency-lab.py'), '--execute-lab', '--lab-image', 'owr-external-lab:local']
    for name in ('approved-trust', 'approved-set-id', 'approved-document-sha256', 'approved-key-sha256', 'approved-read-receipts', 'output'):
        command += ['--' + name, getattr(a, name.replace('-', '_'))]
    result = execute(a.journal, a.approved_set_id, report, lambda: process(command, report.with_suffix('.log')))
    print(json.dumps(result, indent=2))
    return 0 if result['state'] == 'succeeded' else 2


if __name__ == '__main__':
    raise SystemExit(main())
