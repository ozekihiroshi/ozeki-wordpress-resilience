"""Real daily publication deliberately stops at unsigned pending approval."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise(db, web, php, sql, hold, ready, release, run, check, results, output, state):
    Path(output).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    daily = load('daily_first_site', 'first-site-daily.py')
    cases = load('capture_first_daily', 'first-site-s3-capture.py')
    coordinator = daily.Coordinator(state)
    def worker(work):
        # Existing real capture adapter includes update drain, release, DB/media validation.
        capture_output = work / 'capture.json'
        cases.exercise(db, web, php, sql, hold, ready, release, run, check, results, capture_output)
        accepted = [p for p in (work / 'capture-private').glob('*/result.json')
                    if json.loads(p.read_text())['state'] == 'consistent']
        check(len(accepted) == 1, 'ambiguous capture')
        capture = json.loads(accepted[0].read_bytes())
        assets = {k: (accepted[0].parent / v['path']).read_bytes() for k, v in capture['assets'].items()}
        return capture, assets
    now = daily.gate.now()
    row = coordinator.tick(now, worker)
    check(row['state'] in ('awaiting_approval', 'approved'), 'daily publication not complete; inspect retained ledger')
    status = coordinator.status(now)
    expected_approval = 'approved' if row['state'] == 'approved' else 'pending'
    check(status['runs'][-1]['storage_complete'] and status['runs'][-1]['approval_state'] == expected_approval
          and not status['runs'][-1]['restore_allowed'], 'storage state confused with recovery authorization')
    def forbidden(work):
        raise RuntimeError('duplicate capture must not start')
    before = (coordinator.root / row['id'] / 'transfer-receipts/operations.json').read_bytes()
    check(coordinator.tick(now, forbidden) == row, 'duplicate changed daily run')
    check(before == (coordinator.root / row['id'] / 'transfer-receipts/operations.json').read_bytes(),
          'duplicate wrote storage')
    for case in (('daily_two_assets_stored_unsigned_pending' if expected_approval == 'pending'
                  else 'approved_daily_slot_preserved'), 'same_daily_slot_no_capture_or_put',
                 'storage_status_not_recovery_authorization'):
        results.append(dict(case=case, passed=True))
    daily.io.write_json(Path(output).with_suffix('.daily.json'), status)
