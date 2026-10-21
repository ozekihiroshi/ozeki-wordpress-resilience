import copy, importlib.util, json, subprocess, unittest
from datetime import timedelta
from pathlib import Path
from test_deployment_preflight import Preflight, ROOT
s=importlib.util.spec_from_file_location('gate',ROOT/'tools/first-capture-readiness.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class Gate(Preflight):
 def setUp(self):
  super().setUp();d=g.pre.capture.digest
  result=g.pre.assess(self.c,self.v,self.work,self.now)
  result.update(state='needs_configuration',host_observation={'state':'validated_report','unverified':g.SCOPES[:-1]},issues=[{'code':'host_unverified_scope_remaining','category':'configuration'}])
  self.report=dict(format='owr-preflight-admin-v1',site_id=self.c['site_id'],config_sha256=d(self.c),attempted_at=self.now.isoformat(),result=result)
  self.health=dict(format='owr-preflight-transfer-v1',site_id=self.c['site_id'],config_sha256=d(self.c),attempted_at=self.now.isoformat(),state='ok',report_at=self.now.isoformat())
  self.review=dict(format='owr-first-capture-review-v1',site_id=self.c['site_id'],config_sha256=d(self.c),report_sha256=d(self.report),health_sha256=d(self.health),inventory_sha256=d(self.v),workspace=str(self.work),reviewed_at=self.now.isoformat(),reviewed_by=self.c['operations']['owner'],scope='dedicated_trial_only',confirmations={k:dict(confirmed=True,evidence_ref='lab-record/'+k) for k in g.SCOPES})
 def run_gate(self,now=None):return g.evaluate(self.c,self.v,self.work,self.report,self.health,self.review,now or self.now)
 def test_gate_valid_readonly(self):
  before=copy.deepcopy([self.c,self.v,self.report,self.health,self.review]);r=self.run_gate();self.assertEqual(r['blockers'],[]);self.assertEqual(r['state'],'eligible_for_dedicated_capture_review');self.assertFalse(r['execution_authorized']);self.assertEqual(before,[self.c,self.v,self.report,self.health,self.review]);self.assertEqual(list(self.work.iterdir()),[])
 def test_gate_stale_boundary(self):
  self.assertEqual(self.run_gate(self.now+timedelta(seconds=299))['blockers'],[])
  self.assertIn('report_stale_or_invalid',self.run_gate(self.now+timedelta(seconds=300))['blockers'])
 def test_gate_failed_health(self):
  for state in ('transfer_failed','acquisition_failed','unknown'):
   self.health['state']=state;self.assertIn('acquisition_or_transfer_failed',self.run_gate()['blockers'])
 def test_gate_mismatch(self):
  self.health['report_at']='different';self.assertIn('report_health_inconsistent',self.run_gate()['blockers'])
 def test_gate_review_bindings(self):
  for k in ('config_sha256','report_sha256','health_sha256','inventory_sha256','workspace'):
   old=self.review[k];self.review[k]='changed';self.assertIn('review_binding_mismatch',self.run_gate()['blockers']);self.review[k]=old
 def test_gate_confirmations(self):
  for k in g.SCOPES:
   old=self.review['confirmations'][k];self.review['confirmations'][k]={'confirmed':False,'evidence_ref':'todo'};self.assertIn('confirmation_'+k+'_missing',self.run_gate()['blockers']);self.review['confirmations'][k]=old
 def test_gate_missing_review(self):
  self.review={};self.assertIn('operator_review_missing_or_invalid',self.run_gate()['blockers'])
 def test_gate_unsupported_cannot_override(self):
  self.c['wordpress']['multisite']=True;self.assertEqual(self.run_gate()['state'],'blocked')
 def test_gate_uncertain_cannot_override(self):
  self.v['uncertain_puts']=1;self.assertIn('preflight_uncertain_puts_present',self.run_gate()['blockers'])
 def test_gate_cached_success_failure(self):
  self.report['result']['host_observation']['state']='probe_failed';self.assertIn('acquisition_not_verified',self.run_gate()['blockers'])
 def test_gate_reviewer(self):
  self.review['reviewed_by']='undeclared';self.assertIn('reviewer_not_declared',self.run_gate()['blockers'])
 def test_gate_future(self):
  self.report['attempted_at']=(self.now+timedelta(seconds=6)).isoformat();self.assertIn('report_stale_or_invalid',self.run_gate()['blockers'])
 def test_gate_extra_blocker(self):
  self.report['result']['issues'].append({'code':'failed','category':'environment'});self.assertIn('preflight_report_blockers',self.run_gate()['blockers'])
 def test_gate_cli(self):
  args=['python3','-B',str(ROOT/'tools/first-capture-readiness.py'),'--workspace',str(self.work)]
  for name,value in [('profile',self.c),('inventory',self.v),('report',self.report),('health',self.health),('review',self.review)]:
   p=self.root/(name+'.json');p.write_text(json.dumps(value));args+=['--'+name,str(p)]
  before={p.name:p.read_bytes() for p in self.root.glob('*.json')}
  r=subprocess.run(args,capture_output=True,text=True,timeout=10);self.assertEqual(r.returncode,0,r.stdout+r.stderr);self.assertFalse(json.loads(r.stdout)['execution_authorized']);self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.glob('*.json')});self.assertEqual(list(self.work.iterdir()),[])
# Base tests have their own suite; do not repeat inherited tests here.
for name in list(Preflight.__dict__):
 if name.startswith('test_'):setattr(Gate,name,None)
del Preflight
if __name__=='__main__':unittest.main()
