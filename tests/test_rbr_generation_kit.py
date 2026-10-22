import datetime as dt, importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('inlet',Path(__file__).resolve().parents[1]/'tools/rbr-generation-kit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Store:
 def __init__(self):self.objects={};self.puts=[]
 def add(self,obj,until):
  raw=obj if isinstance(obj,bytes) else m.k.canonical(obj);ref={'locator':{'kind':'s3','bucket':'fixture','region':'ap-northeast-1','key':'rbr-'+m.k.sha(raw)+'.blob','version_id':'fixed'},'sha256':m.k.sha(raw),'size_bytes':len(raw)};self.objects[m.k.canonical(ref)]=(raw,until,self.now);return ref
 def get(self,ref):return self.objects[m.k.canonical(ref)]
 def put(self,raw,key):
  self.puts.append(key);ref=self.add(raw,self.now+36*86400);ref['locator']['key']=key;ref['locator']['version_id']='new';self.objects[m.k.canonical(ref)]=(raw,self.now+36*86400,self.now);return ref
class Inlet(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.w=Path(self.t.name);self.s=Store();self.s.now=int(dt.datetime.now(dt.timezone.utc).timestamp());self.h=self.s.now+35*86400+300
  self.asset=self.s.add(b'original',self.h+3600)
  self.a={'schema':'owr-rbr-generation-v1','site_id':'corporate-test','sequence':1,'deadline':self.s.now+300,'protect_until':self.h,'assets':[{'storage':self.asset}]};self.g=self.s.add(self.a,self.h+3600)
  ref=self.s.add({'value':'fixed-profile'},self.h+3600)
  self.p={'schema':'owr-rbr-definition-profile-v1','site_id':'corporate-test','rules_ref':ref,'environment_ref':ref,'comparison_ref':ref,'expected_ref':ref,'required_scope':{}}
  self.b=m.Builder(self.s,self.w,'test/')
 def planner(self,args,**kw):
  self.assertEqual(Path(args[1]).name,'rbr-plan.php')
  Path(next(x.split('=',1)[1] for x in args if x.startswith('--output='))).write_text('{"environment_mode":"pinned-runtime"}')
 def run_build(self):
  with patch.object(m.subprocess,'run',side_effect=self.planner):return self.b.prepare(self.g,self.p)
 def test_preserves_real_generation_and_awaits_approval(self):
  result=self.run_build();d=json.loads((self.w/'definition.json').read_bytes());self.assertEqual(d['assets_ref'],self.g);self.assertEqual(result['state'],'stored_awaiting_independent_approval');self.assertFalse(result['public_activation'])
 def test_short_original_blocks_without_put(self):
  raw,_,stored=self.s.objects[m.k.canonical(self.asset)];self.s.objects[m.k.canonical(self.asset)]=(raw,self.h-1,stored)
  with self.assertRaisesRegex(ValueError,'protection'):self.run_build()
  self.assertEqual(self.s.puts,[])
 def test_short_profile_copies_and_keeps_generation(self):
  ref=self.p['rules_ref'];raw,_,stored=self.s.objects[m.k.canonical(ref)];self.s.objects[m.k.canonical(ref)]=(raw,self.h-1,stored);self.run_build();self.assertGreater(len(self.s.puts),0);self.assertEqual(json.loads((self.w/'definition.json').read_bytes())['assets_ref'],self.g)
 def test_code_reuses_exact_verified_profile_reference(self):
  raw=(m.ROOT/m.CODE[0]).read_bytes();ref=self.s.add(raw,self.h+3600)
  self.b.read(ref);self.assertEqual(self.b.execution_ref(raw,self.h),ref);self.assertFalse(self.s.puts)
 def test_code_does_not_reuse_short_retention(self):
  raw=(m.ROOT/m.CODE[0]).read_bytes();ref=self.s.add(raw,self.h-1)
  self.b.read(ref);new=self.b.execution_ref(raw,self.h);self.assertNotEqual(new,ref);self.assertEqual(len(self.s.puts),1)
 def test_wrong_site_blocks(self):
  self.p['site_id']='other'
  with self.assertRaisesRegex(ValueError,'site'):self.run_build()
  self.assertFalse(self.s.puts)
 def test_injected_generation_in_profile_rejected(self):
  self.p['assets_ref']=self.asset
  with self.assertRaises(ValueError):self.run_build()
 def test_expired_generation_blocks(self):
  self.a['protect_until']=self.s.now-1;self.g=self.s.add(self.a,self.h)
  with self.assertRaises(ValueError):self.run_build()
 def test_short_new_copy_not_accepted(self):
  ref=self.p['rules_ref'];raw,_,stored=self.s.objects[m.k.canonical(ref)];self.s.objects[m.k.canonical(ref)]=(raw,self.h-1,stored);self.s.now-=2*86400
  with self.assertRaisesRegex(ValueError,'protection'):self.run_build()
 def test_planner_failure_never_commits_root(self):
  with patch.object(m.subprocess,'run',side_effect=RuntimeError('invalid plan')):
   with self.assertRaises(RuntimeError):self.b.prepare(self.g,self.p)
  self.assertFalse((self.w/'root-receipt.json').exists())
 def test_late_s3_commit_rejected(self):
  raw,until,_=self.s.objects[m.k.canonical(self.g)];self.s.objects[m.k.canonical(self.g)]=(raw,until,self.a['deadline']+1)
  with self.assertRaisesRegex(ValueError,'after deadline'):self.run_build()
  self.assertFalse(self.s.puts)
 def test_malformed_horizon_rejected(self):
  self.a['protect_until']+=1;self.g=self.s.add(self.a,self.h+3600)
  with self.assertRaises(ValueError):self.run_build()
 def test_resume_changes_rejected_before_network(self):
  generation=self.w/'gen.json';profile=self.w/'profile.json';work=self.w/'resume';work.mkdir()
  generation.write_bytes(m.k.canonical(self.g));profile.write_bytes(m.k.canonical(self.p));(work/'input.json').write_text('{}')
  with patch.object(m.k.transport,'preflight') as network:
   with self.assertRaisesRegex(ValueError,'Resume input changed'):m.main(generation,profile,work)
   network.assert_not_called()
 def test_same_workspace_lock_blocks(self):
  work=self.w/'locked';work.mkdir()
  with (work/'.lock').open('a') as lock:
   m.fcntl.flock(lock,m.fcntl.LOCK_EX|m.fcntl.LOCK_NB)
   with self.assertRaises(BlockingIOError):m.main(self.w/'absent',self.w/'absent',work)
 def test_explicit_retention_only_changes_new_put_template(self):
  from types import SimpleNamespace
  with patch.object(m.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'{}')) as call:
   m.k.authorize('writer',retention_days=36,operation='preflight')
   self.assertIn('days=36,minutes=10',call.call_args.args[0][-1])
   self.assertNotIn('days=35,minutes=10',call.call_args.args[0][-1])
 def test_legacy_retention_template_unchanged(self):
  from types import SimpleNamespace
  with patch.object(m.k.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'{}')) as call:
   m.k.authorize('writer',operation='preflight')
   self.assertIn('days=35,minutes=10',call.call_args.args[0][-1])
 def test_unsupported_retention_rejected_without_request(self):
  with patch.object(m.k.subprocess,'run') as call:
   with self.assertRaises(ValueError):m.k.authorize('writer',retention_days=100)
   call.assert_not_called()
if __name__=='__main__':unittest.main()

