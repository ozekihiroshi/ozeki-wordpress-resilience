import copy,hashlib,importlib.util,json,tempfile,unittest,time
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('generation',Path(__file__).resolve().parents[1]/'tools/rbr-generation-kit.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class RequestQ(unittest.TestCase):
 def setUp(self):
  self.objects={}
  self.q={'schema':'owr-rbr-expected-v1','actual_status':'draft','scope':{'roles':['company','services','contact'],'images':[],'business_expectations':{r:['Request '+r] for r in ['company','services','contact']}},'pages':{r:{'title':r,'slug':r,'role':r,'paragraphs':['Request '+r]} for r in ['company','services','contact']},'images':{},'relations':[]}
  assets=[]
  for role,p in self.q['pages'].items():
   raw=m.k.canonical({k:p[k] for k in ['title','slug','paragraphs']});ref=self.put(raw)
   assets.append({'id':role,'role':role,'kind':'page','sha256':ref['sha256'],'storage':ref})
  ref=self.put(b'{ "edges": [] }');assets.append({'id':'relations','kind':'relations','sha256':ref['sha256'],'storage':ref})
  self.intent={'schema':'owr-rbr-save-v1','site_id':'test','operation_id':'request-001','sequence':3,'parent':None,'deadline':int(time.time())+300,'expected_sha256':m.k.sha(m.k.canonical(self.q)),'assets':[{k:v for k,v in a.items() if k!='storage'} for a in assets]}
  self.manifest={k:self.intent[k] for k in ['site_id','operation_id','sequence','parent','deadline']};self.manifest.update(schema='owr-rbr-generation-v1',protect_until=self.intent['deadline']+35*86400,assets=assets,intent_sha256=m.k.sha(m.k.canonical(self.intent)))
  self.g=self.put(m.k.canonical(self.manifest));self.bound={'schema':'owr-rbr-bound-expected-v1','generation':self.g,'intent':self.intent,'expected':self.q}
 def put(self,raw):
  h=m.k.sha(raw);self.objects[h]=raw;return {'locator':{'kind':'s3','key':h,'version_id':'fixed'},'sha256':h,'size_bytes':len(raw)}
 def read(self,ref):return self.objects[ref['sha256']]
 def verify(self):return m.k.bound_expected(self.bound,self.g,self.manifest,self.read)
 def test_request_q_bound_to_selected_generation(self):self.assertEqual(self.verify(),self.q)
 def test_different_generation_rejected(self):
  self.bound['generation']=dict(self.g,sha256='0'*64)
  with self.assertRaisesRegex(ValueError,'another generation'):self.verify()
 def test_changed_q_rejected(self):
  self.q['pages']['company']['title']='Changed'
  with self.assertRaisesRegex(ValueError,'digest'):self.verify()
 def test_changed_intent_rejected(self):
  self.intent['operation_id']='changed'
  with self.assertRaisesRegex(ValueError,'digest'):self.verify()
 def test_inconsistent_page_rejected_even_with_rehashed_q(self):
  self.q['pages']['contact']['paragraphs']=['invented'];self.intent['expected_sha256']=m.k.sha(m.k.canonical(self.q));self.manifest['intent_sha256']=m.k.sha(m.k.canonical(self.intent))
  with self.assertRaisesRegex(ValueError,'save request'):self.verify()
 def test_noncanonical_original_relations_supported(self):self.verify()
 def test_root_rechecks_binding_against_definition(self):
  d={'assets_ref':self.g,'expected_ref':self.put(m.k.canonical(self.q)),'required_scope':self.q['scope']};root={'schema':'owr-rbr-s3-kit-v2','definition_ref':self.put(m.k.canonical(d)),'expected_binding_ref':self.put(m.k.canonical(self.bound))};m.k.verify_bound_root(root,self.read)
  changed=copy.deepcopy(self.q);changed['pages']['contact']['title']='wrong';d['expected_ref']=self.put(m.k.canonical(changed));root['definition_ref']=self.put(m.k.canonical(d))
  with self.assertRaisesRegex(ValueError,'Definition Q'):m.k.verify_bound_root(root,self.read)
 def test_v2_missing_binding_rejected(self):
  with self.assertRaisesRegex(ValueError,'required'):m.k.verify_bound_root({'schema':'owr-rbr-s3-kit-v2'},self.read)
 def test_v1_cannot_silently_carry_bound_q(self):
  with self.assertRaisesRegex(ValueError,'requires kit v2'):m.k.verify_bound_root({'schema':'owr-rbr-s3-kit-v1','expected_binding_ref':self.g},self.read)
 def test_binding_dependency_excludes_archival_intent(self):
  self.assertEqual([k for k,v in m.k.dependency_items(self.bound)],['generation','expected'])
 def test_manual_profile_rejected_for_bound_receipt(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);(b/'receipt').write_text(json.dumps({'state':'applied','sequence':3,'generation':self.g,'expected_ref':self.put(m.k.canonical(self.bound))}));(b/'profile').write_text(json.dumps({'schema':'owr-rbr-definition-profile-v1','expected_ref':self.g}))
   with patch.object(m.k.transport,'preflight') as net:
    with self.assertRaisesRegex(ValueError,'Request-Q profile'):m.main(b/'receipt',b/'profile',b/'work')
    net.assert_not_called()
 def build(self,short=False):
  owner=self;binding=self.put(m.k.canonical(self.bound));now=int(time.time())
  class Store:
   def __init__(self):self.puts=[]
   def get(self,ref):return owner.read(ref),(now if short and ref==binding else now+36*86400),now
   def put(self,raw,key):self.puts.append(key);return owner.put(raw)
  store=Store();profile={'schema':'owr-rbr-request-profile-v1','site_id':'test',**{k:self.put(b'{}') for k in ['rules_ref','environment_ref','comparison_ref']}}
  with tempfile.TemporaryDirectory() as td:
   work=Path(td)
   def planner(args,**kw):Path(next(x.split('=',1)[1] for x in args if x.startswith('--output='))).write_text('{"environment_mode":"pinned-runtime"}')
   with patch.object(m.subprocess,'run',side_effect=planner):
    if short:
     with self.assertRaisesRegex(ValueError,'retention'):m.Builder(store,work,'test/').prepare(self.g,profile,3,binding)
     self.assertFalse(store.puts);return
    result=m.Builder(store,work,'test/').prepare(self.g,profile,3,binding)
   root=json.loads(self.read(result['root_receipt']));self.assertEqual(root['expected_binding_ref'],binding);m.k.verify_bound_root(root,self.read)
   d=json.loads(self.read(root['definition_ref']));self.assertEqual(json.loads(self.read(d['expected_ref'])),self.q);self.assertEqual(d['required_scope'],self.q['scope']);self.assertEqual(result['state'],'stored_awaiting_independent_approval')
 def test_builder_uses_request_q_without_manual_q(self):self.build()
 def test_short_bound_q_retention_blocks_before_put(self):self.build(True)
if __name__=='__main__':unittest.main()
