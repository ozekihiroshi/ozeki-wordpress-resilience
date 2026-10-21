import fcntl, importlib.util, json, unittest
from test_first_capture_readiness import Gate, ROOT
from test_first_site_capture import Backend
s=importlib.util.spec_from_file_location('entry',ROOT/'tools/first-capture-entry.py');e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
class Entry(Gate):
 def setUp(self):
  # Reuse generated evidence fixture, not a saved eligibility decision.
  super().setUp()
  self.paths={}
  for name,value in [('profile',self.c),('inventory',self.v),('report',self.report),('health',self.health),('review',self.review)]:
   p=self.root/(name+'.json');p.write_text(json.dumps(value));self.paths[name]=p
  self.paths['workspace']=self.work
 def invoke(self,b=None):return e.capture_from_files(**self.paths,backend=b or Backend())
 def change(self,name,value):self.paths[name].write_text(json.dumps(value))
 def test_success_real_capture_core(self):
  b=Backend();work,r=self.invoke(b);self.assertTrue(r['capture_started']);self.assertTrue(r['eligible_for_consistency_acceptance']);self.assertTrue(b.released);self.assertEqual(set(r['assets']),{'database','files'})
 def test_initial_invalid_no_backend_or_attempt(self):
  b=Backend();b.preflight=lambda c:self.fail('backend should not run')
  self.health['state']='transfer_failed';self.change('health',self.health)
  with self.assertRaisesRegex(e.api.Rejected,'admission_blocked'):self.invoke(b)
  self.assertIsNone(b.token);self.assertFalse(b.released);self.assertEqual([p.name for p in self.work.iterdir()],[self.c['site_id']+'.lock'])
 def test_change_after_first_check_stops_before_fence(self):
  for kind in ('profile','health','review','missing','stale'):
   with self.subTest(kind=kind):
    originals={n:p.read_bytes() for n,p in self.paths.items() if n!='workspace'}
    b=Backend()
    def prepare(c):
     if kind=='missing':self.paths['report'].unlink()
     elif kind=='profile':v=dict(self.c);v['revision']+=1;self.change('profile',v)
     elif kind=='health':v=dict(self.health);v['state']='acquisition_failed';self.change('health',v)
     elif kind=='stale':v=dict(self.report);v['attempted_at']='2020-01-01T00:00:00+00:00';self.change('report',v)
     else:self.change('review',{})
    b.preflight=prepare
    work,r=self.invoke(b)
    self.assertFalse(r['capture_started']);self.assertFalse(r['eligible_for_consistency_acceptance']);self.assertIsNone(b.token);self.assertFalse(b.released);self.assertEqual(r['assets'],{});self.assertEqual(list(work.iterdir()),[work/'result.json']);self.assertNotIn('fence',r['phases'])
    for n,data in originals.items():self.paths[n].write_bytes(data)
 def test_site_lock_precedes_gate(self):
  with (self.work/(self.c['site_id']+'.lock')).open('w') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaisesRegex(e.api.Rejected,'site_busy'):self.invoke()
 def test_prior_attempt_preserved(self):
  p=self.work/(self.c['site_id']+'.active.json');p.write_text('unresolved')
  with self.assertRaisesRegex(e.api.Rejected,'prior_attempt'):self.invoke()
  self.assertEqual(p.read_text(),'unresolved')
 def test_release_failure_preserves_active(self):
  b=Backend();b.fail='release';_,r=self.invoke(b);self.assertFalse(r['eligible_for_consistency_acceptance']);self.assertTrue((self.work/(self.c['site_id']+'.active.json')).exists())
 def test_lock_held_at_final_gate(self):
  b=Backend()
  def check(c):
   with (self.work/(self.c['site_id']+'.lock')).open() as f:
    with self.assertRaises(BlockingIOError):fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  b.preflight=check;self.assertTrue(self.invoke(b)[1]['eligible_for_consistency_acceptance'])
# Fixtures only, exclude their unittest classes from discovery.
for name in Gate.__dict__:
 if name.startswith('test_'):setattr(Entry,name,None)
del Gate
if __name__=='__main__':unittest.main()
