"""Explicit operator issuance of a bounded recurring capture review; never auto-renews."""
import argparse, importlib.util, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
s=importlib.util.spec_from_file_location('readiness',Path(__file__).with_name('first-capture-readiness.py'));gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)

def issue(profile,inventory,workspace,report,health,confirmations,reviewed_by,valid_hours=168,now=None):
    now=now or datetime.now(timezone.utc)
    if type(valid_hours) is not int or not 1<=valid_hours<=168:raise ValueError('invalid_validity')
    d=gate.pre.capture.digest
    review=dict(format='owr-first-capture-review-v1',site_id=profile['site_id'],config_sha256=d(profile),workspace=str(Path(workspace).absolute()),reviewed_at=now.isoformat(),reviewed_by=reviewed_by,scope='dedicated_trial_only',confirmations=confirmations,report_sha256=d(report),health_sha256=d(health),inventory_sha256=d(inventory))
    if gate.evaluate(profile,inventory,workspace,report,health,review,now)['state']!='eligible_for_dedicated_capture_review':raise ValueError('current_evidence_or_confirmation_rejected')
    for key in ('report_sha256','health_sha256','inventory_sha256'):review.pop(key)
    review.update(format='owr-recurring-capture-review-v1',status='active',expires_at=(now+timedelta(hours=valid_hours)).isoformat(),inventory_scope_sha256=d(gate.inventory_scope(inventory)),host_scope_sha256=d(report['result']['host_observation'].get('review_scope')))
    if gate.evaluate(profile,inventory,workspace,report,health,review,now)['state']!='eligible_for_dedicated_capture_review':raise ValueError('recurring_scope_rejected')
    return review

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('profile','inventory','workspace','report','health','confirmations','reviewed-by','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--valid-hours',type=int,default=168);a=p.parse_args()
    try:
        v=issue(gate.pre.read_json(a.profile),gate.pre.read_json(a.inventory),a.workspace,gate.pre.read_json(a.report),gate.pre.read_json(a.health),gate.pre.read_json(a.confirmations),a.reviewed_by,a.valid_hours)
        # Fresh file only; keep prior confirmations for audit. Protected parent is operator-managed.
        parent=Path(a.output).absolute().parent
        if not parent.is_dir() or parent.is_symlink() or parent.stat().st_uid!=os.getuid() or parent.stat().st_mode & 0o077:raise ValueError('private_output_parent_required')
        fd=os.open(a.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(v,f,indent=2);f.flush();os.fsync(f.fileno())
        print(json.dumps(dict(created=True,expires_at=v['expires_at'],automatic_renewal=False)));return 0
    except (ValueError,OSError,TypeError,KeyError,RecursionError):
        print(json.dumps(dict(created=False,reason='issuance_rejected',automatic_renewal=False)));return 2
if __name__=='__main__':raise SystemExit(main())
