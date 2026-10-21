import copy, importlib.util, json, subprocess
from datetime import timedelta
from test_first_site_daily_admission import AdmittedDaily
from test_first_capture_readiness import g, ROOT
s=importlib.util.spec_from_file_location('review_issue',ROOT/'tools/recurring-capture-review.py');issuer=importlib.util.module_from_spec(s);s.loader.exec_module(issuer)
class Recurring(AdmittedDaily):
 def setUp(self):
  super().setUp()
  self.report['result']['host_observation']['review_scope']={'database':self.c['database'],'files_root':self.c['files']['root'],'wordpress':self.c['wordpress'],'runtime':{'php_version':'8.3.0','os_family':'Linux'}}
  self.report['result']['host_observation']['review_scope']={k:g.pre.capture.digest(v) for k,v in self.report['result']['host_observation']['review_scope'].items()}
  self.review=issuer.issue(self.c,self.v,self.work,self.report,self.health,self.review['confirmations'],self.c['operations']['owner'],now=self.now)
  self.change('report',self.report);self.change('review',self.review)
 def check_gate(self,now=None):return g.evaluate(self.c,self.v,self.work,self.report,self.health,self.review,now or self.now)
 def freshen(self,now):
  stamp=now.isoformat();self.v['observed_at']=stamp;self.report['attempted_at']=stamp;self.report['result']['assessed_at']=stamp;self.health['attempted_at']=stamp;self.health['report_at']=stamp
 def test_next_day_auto_recheck_no_operator_renewal(self):
  before=copy.deepcopy(self.review);tomorrow=self.now+timedelta(days=1);self.freshen(tomorrow)
  self.assertEqual(self.check_gate(tomorrow)['blockers'],[]);self.assertEqual(self.review,before)
 def test_expiry_exact_boundary_and_no_extension(self):
  end=self.now+timedelta(days=7);self.freshen(end)
  self.assertIn('review_expired_or_invalid',self.check_gate(end)['blockers']);self.assertEqual(self.review['expires_at'],end.isoformat())
 def test_stale_report_still_blocked(self):
  self.assertIn('report_stale_or_invalid',self.check_gate(self.now+timedelta(minutes=5))['blockers'])
 def test_revoked(self):
  self.review['status']='revoked';self.assertIn('review_revoked_or_inactive',self.check_gate()['blockers'])
 def test_runtime_change_requires_review(self):
  self.report['result']['host_observation']['review_scope']['runtime']=g.pre.capture.digest({'php_version':'8.3.1','os_family':'Linux'})
  self.assertIn('review_scope_changed',self.check_gate()['blockers'])
 def test_profile_change_requires_review(self):
  self.c['operations']['owner']='new-owner';self.assertIn('review_binding_mismatch',self.check_gate()['blockers'])
 def test_overlong_or_future_review_refused(self):
  self.review['expires_at']=(self.now+timedelta(days=8)).isoformat();self.assertIn('review_expired_or_invalid',self.check_gate()['blockers'])
  self.review['reviewed_at']=(self.now+timedelta(hours=1)).isoformat();self.assertIn('review_expired_or_invalid',self.check_gate()['blockers'])
 def test_missing_confirmations(self):
  self.review['confirmations'].pop('writers');self.assertIn('confirmations_incomplete',self.check_gate()['blockers'])
 def test_failed_then_fresh_same_scope(self):
  self.health['state']='acquisition_failed';self.assertIn('acquisition_or_transfer_failed',self.check_gate()['blockers']);self.health['state']='ok';self.assertEqual(self.check_gate()['blockers'],[])
 def test_daily_old_confirmation_fresh_evidence_success(self):
  self.review['reviewed_at']=(self.now-timedelta(days=2)).isoformat();self.review['expires_at']=(self.now+timedelta(days=5)).isoformat();self.change('review',self.review)
  self.assertEqual(self.tick_daily()['state'],'awaiting_approval');self.assertEqual(self.remote.puts,2)
 def test_daily_expired_zero_put(self):
  self.review['reviewed_at']=(self.now-timedelta(days=8)).isoformat();self.review['expires_at']=(self.now-timedelta(days=1)).isoformat();self.change('review',self.review)
  self.assertEqual(self.tick_daily()['state'],'unknown');self.assertEqual(self.remote.puts,0)
 def test_renewal_requires_current_evidence_and_new_confirmation(self):
  self.health['state']='transfer_failed'
  with self.assertRaises(ValueError):issuer.issue(self.c,self.v,self.work,self.report,self.health,self.review['confirmations'],self.c['operations']['owner'],now=self.now)
  self.health['state']='ok';new=issuer.issue(self.c,self.v,self.work,self.report,self.health,self.review['confirmations'],self.c['operations']['owner'],24,self.now)
  self.assertEqual(new['expires_at'],(self.now+timedelta(days=1)).isoformat())
 def test_inventory_freshness_and_binding(self):
  self.v['observed_at']=(self.now-timedelta(seconds=300)).isoformat();self.assertIn('inventory_stale_or_invalid',self.check_gate()['blockers'])
  self.v['observed_at']=self.now.isoformat();self.v['runtime']['wordpress_ref']='changed';self.assertIn('review_scope_changed',self.check_gate()['blockers'])
 def test_missing_host_scope(self):
  self.report['result']['host_observation'].pop('review_scope');self.assertIn('host_review_scope_missing',self.check_gate()['blockers'])
 def test_daily_revoked_zero_capture(self):
  from test_first_capture_entry import Backend
  b=Backend();b.preflight=lambda c:self.fail('revoked review started backend')
  self.review['status']='revoked';self.change('review',self.review)
  self.assertEqual(self.tick_daily(b)['state'],'unknown');self.assertEqual(self.remote.puts,0)
 def test_issue_cli_no_overwrite(self):
  confirms=self.root/'confirms.json';confirms.write_text(json.dumps(self.review['confirmations']));output=self.root/'new-review.json'
  args=['python3','-B',str(ROOT/'tools/recurring-capture-review.py'),'--confirmations',str(confirms),'--reviewed-by',self.c['operations']['owner'],'--output',str(output)]
  for key,path in self.paths.items():
   if key!='review':args+=['--'+key,str(path)]
  r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stdout+r.stderr);before=output.read_bytes()
  self.assertEqual(subprocess.run(args,capture_output=True).returncode,2);self.assertEqual(output.read_bytes(),before)
for name in AdmittedDaily.__dict__:
 if name.startswith('test_'):setattr(Recurring,name,None)
del AdmittedDaily
