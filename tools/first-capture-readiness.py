#!/usr/bin/env python3
"""Read-only first-capture review gate. Never starts capture or grants production approval."""
import argparse,importlib.util,json,re
from datetime import datetime,timezone
from pathlib import Path
s=importlib.util.spec_from_file_location('preflight',Path(__file__).with_name('deployment-preflight.py'));pre=importlib.util.module_from_spec(s);s.loader.exec_module(pre)
SCOPES=['writers','queue','dependencies','runtime_image_binding','multisite_config','storage','trust','operational_ledgers','file_snapshot_consistency','stop_and_release_plan']
MAX_AGE=300
MAX_REVIEW_SECONDS=7*86400

def inventory_scope(value):
 return {k:v for k,v in value.items() if k != "observed_at"}


def evaluate(profile,inventory,workspace,report,health,review,now=None):
 now=now or datetime.now(timezone.utc);blocked=[]
 def fail(code):
  if code not in blocked:blocked.append(code)
 def fresh(value,label):
  try:
   t=datetime.fromisoformat(value)
   if t.tzinfo is None or not -5 <= (now-t).total_seconds() < MAX_AGE:raise ValueError()
  except (ValueError,TypeError,OverflowError):fail(label+'_stale_or_invalid')
 def finish():return dict(format='owr-first-capture-readiness-v1',assessed_at=now.isoformat(),state='blocked' if blocked else 'eligible_for_dedicated_capture_review',production_ready=False,capture_started=False,execution_authorized=False,blockers=blocked,required_confirmations=SCOPES,scope='dedicated_trial_only',not_verified=['malware_absence','live_fence_and_drain','actual_capture_consistency','production_recovery'])
 try:
  base=pre.assess(profile,inventory,workspace,now)
  if base['state']!='eligible_for_dedicated_trial':
   for x in base['issues']:fail('preflight_'+x['code'])
  digest=pre.capture.digest(profile)
  if not isinstance(report,dict) or set(report)!={'format','site_id','config_sha256','attempted_at','result'}:raise ValueError()
  if report['format']!='owr-preflight-admin-v1' or report['site_id']!=profile['site_id'] or report['config_sha256']!=digest:fail('report_binding_mismatch')
  fresh(report['attempted_at'],'report')
  result=report['result'];host=result['host_observation']
  if result.get('config_sha256')!=digest:fail('assessment_binding_mismatch')
  if result.get('production_ready') is not False or result.get('capture_started') is not False:fail('assessment_scope_invalid')
  fresh(result.get('assessed_at'),'assessment')
  if result.get('state')!='needs_configuration' or host.get('state')!='validated_report':fail('acquisition_not_verified')
  if host.get('unverified')!=SCOPES[:-1]:fail('unverified_scope_invalid')
  issues=result['issues']
  if not isinstance(issues,list) or len(issues)!=1 or issues[0].get('code')!='host_unverified_scope_remaining' or issues[0].get('category')!='configuration':fail('preflight_report_blockers')
  if not isinstance(health,dict) or set(health)!={'format','site_id','config_sha256','attempted_at','state','report_at'}:raise ValueError()
  if health['format']!='owr-preflight-transfer-v1' or health['site_id']!=profile['site_id'] or health['config_sha256']!=digest:fail('health_binding_mismatch')
  if health['state']!='ok':fail('acquisition_or_transfer_failed')
  if health['report_at']!=report['attempted_at']:fail('report_health_inconsistent')
  fresh(health['attempted_at'],'health')
  if datetime.fromisoformat(health['attempted_at'])<datetime.fromisoformat(report['attempted_at']):fail('health_precedes_report')
  recurring=isinstance(review,dict) and review.get('format')=='owr-recurring-capture-review-v1'
  required={'format','site_id','config_sha256','workspace','reviewed_at','reviewed_by','scope','confirmations'}
  required |= {'expires_at','status','inventory_scope_sha256','host_scope_sha256'} if recurring else {'report_sha256','health_sha256','inventory_sha256'}
  if not isinstance(review,dict) or set(review)!=required:fail('operator_review_missing_or_invalid');return finish()
  if review['scope']!='dedicated_trial_only' or review['format'] not in ('owr-first-capture-review-v1','owr-recurring-capture-review-v1'):fail('review_scope_invalid')
  if review['site_id']!=profile['site_id'] or review['config_sha256']!=digest or review['workspace']!=str(Path(workspace).absolute()):fail('review_binding_mismatch')
  if review['reviewed_by'] not in (profile['operations']['owner'],profile['operations']['alternate']):fail('reviewer_not_declared')
  if recurring:
   fresh(inventory.get('observed_at'),'inventory')
   if review['status']!='active':fail('review_revoked_or_inactive')
   start=datetime.fromisoformat(review['reviewed_at']);end=datetime.fromisoformat(review['expires_at'])
   if not start.tzinfo or not end.tzinfo or not 0<(end-start).total_seconds()<=MAX_REVIEW_SECONDS or start>now or now>=end:fail('review_expired_or_invalid')
   scope=host.get('review_scope')
   if not isinstance(scope,dict) or set(scope)!={'database','files_root','wordpress','runtime'} or not all(isinstance(v,str) and re.fullmatch('[a-f0-9]{64}',v) for v in scope.values()):fail('host_review_scope_missing')
   if review['inventory_scope_sha256']!=pre.capture.digest(inventory_scope(inventory)) or review['host_scope_sha256']!=pre.capture.digest(scope):fail('review_scope_changed')
  else:
   if review['report_sha256']!=pre.capture.digest(report) or review['health_sha256']!=pre.capture.digest(health) or review['inventory_sha256']!=pre.capture.digest(inventory):fail('review_binding_mismatch')
   fresh(review['reviewed_at'],'review')
   if datetime.fromisoformat(review['reviewed_at'])<max(datetime.fromisoformat(report['attempted_at']),datetime.fromisoformat(health['attempted_at'])):fail('review_precedes_evidence')
  c=review['confirmations']
  if not isinstance(c,dict) or set(c)!=set(SCOPES):fail('confirmations_incomplete')
  else:
   for k,v in c.items():
    if not isinstance(v,dict) or set(v)!={'confirmed','evidence_ref'} or v['confirmed'] is not True or not isinstance(v['evidence_ref'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{2,255}',v['evidence_ref']) or v['evidence_ref'].lower() in ('unknown','todo','unset','not-connected'):fail('confirmation_'+k+'_missing')
 except (ValueError,TypeError,KeyError,AttributeError,OverflowError):fail('input_invalid')
 return finish()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('profile','inventory','workspace','report','health','review'):p.add_argument('--'+name,required=True)
 a=p.parse_args()
 try:r=evaluate(pre.read_json(a.profile),pre.read_json(a.inventory),a.workspace,pre.read_json(a.report),pre.read_json(a.health),pre.read_json(a.review))
 except (OSError,ValueError,RecursionError):r=dict(format='owr-first-capture-readiness-v1',state='blocked',production_ready=False,capture_started=False,execution_authorized=False,blockers=['input_unreadable_or_invalid'])
 print(json.dumps(r,ensure_ascii=False,allow_nan=False));return 0 if r['state']=='eligible_for_dedicated_capture_review' else 2
if __name__=='__main__':raise SystemExit(main())
