"""Redacted operator review summary for the existing preflight admin report."""
import importlib.util
from datetime import datetime,timezone
from pathlib import Path
s=importlib.util.spec_from_file_location('review_gate',Path(__file__).with_name('first-capture-readiness.py'));gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)

def summarize(profile,inventory,workspace,report,health,review,now=None):
    now=now or datetime.now(timezone.utc)
    result=dict(format='owr-operator-review-status-v1',state='invalid',reviewed_at=None,expires_at=None,reasons=['review_invalid'],automatic_checks_passed=False)
    if review is None:result.update(state='missing',reasons=['review_missing']);return result
    if not isinstance(review,dict) or review.get('format')!='owr-recurring-capture-review-v1':return result
    try:
        start=datetime.fromisoformat(review['reviewed_at']);end=datetime.fromisoformat(review['expires_at'])
        if not start.tzinfo or not end.tzinfo or start>now or not 0<(end-start).total_seconds()<=gate.MAX_REVIEW_SECONDS:return result
        result.update(reviewed_at=start.isoformat(),expires_at=end.isoformat())
        decision=gate.evaluate(profile,inventory,workspace,report,health,review,now)
        codes=decision['blockers'];reasons=[]
        if review.get('status')!='active':state='revoked';reasons.append('review_revoked')
        elif now>=end:state='expired';reasons.append('review_expired')
        elif any(c in ('review_binding_mismatch','review_scope_changed','reviewer_not_declared') for c in codes):state='reconfirmation_required';reasons.append('scope_changed')
        elif any(c.startswith('confirmation') or c.startswith('operator_review') or c.startswith('review_') for c in codes):state='reconfirmation_required';reasons.append('confirmation_incomplete')
        else:state='valid'
        if any(c not in ('review_expired_or_invalid','review_revoked_or_inactive','review_binding_mismatch','review_scope_changed','reviewer_not_declared') and not c.startswith(('confirmation','operator_review','review_')) for c in codes):reasons.append('automatic_checks_failed')
        result.update(state=state,reasons=reasons,automatic_checks_passed=not codes)
        return result
    except (ValueError,TypeError,KeyError,OverflowError):return result
