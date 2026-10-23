import copy,json,unittest
from test_site_materials import Store,site,m
import tempfile

class NativeMaterials(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store();self.repo=m.Repository(self.store,self.tmp.name,'native/')
 def tearDown(self):self.tmp.cleanup()
 def material(self):
  s=site();s['entries'][0].update(status='publish',nodes=[{'type':'block','name':'core/paragraph','html':'<p>Body <strong>bold</strong> <a href="https://example.invalid/">link</a></p>'}]);return s
 def test_published_intent_and_q_roundtrip(self):
  s=self.material();ref=self.repo.save('first',None,s);received=m.receive(self.store,ref)
  self.assertEqual(received['expected'],m.expected(s));self.assertEqual(received['site'],s)
  self.assertEqual(json.loads(self.store.get(ref)[0])['rules'],'portable-nodes-v2')
 def test_legacy_rule_still_readable(self):
  ref=self.repo.save('legacy',None,site());self.assertEqual(m.receive(self.store,ref)['site'],site())
  self.assertEqual(json.loads(self.store.get(ref)[0])['rules'],'portable-nodes-v1')
 def test_unsafe_or_dependent_blocks_rejected_before_storage(self):
  for html in ['<p onclick="run()">x</p>','<script>run()</script>','<img src="https://source.invalid/x.png">','<a href="javascript:run()">x</a>','<a href="java&#115;cript:run()">x</a>','<p>x','<!DOCTYPE html><p>x</p>','<img src="asset:missing">']:
   with self.subTest(html=html):
    s=self.material();s['entries'][0]['nodes'][0]['html']=html
    with self.assertRaises(ValueError):self.repo.save('bad',None,s)
    self.assertEqual(self.store.writes,0)
 def test_unsupported_status_rejected(self):
  s=self.material();s['entries'][0]['status']='future'
  with self.assertRaises(ValueError):self.repo.save('bad',None,s)
  self.assertEqual(self.store.writes,0)
 def test_image_reference_kind_checked(self):
  s=self.material();s['entries'][0]['nodes'][0]['html']='<img src="asset:company">'
  with self.assertRaises(ValueError):self.repo.save('bad',None,s)
  self.assertEqual(self.store.writes,0)
 def test_inline_page_relation(self):
  s=self.material();s['entries'][0]['nodes'][0]['html']='<p><a href="asset:company">home</a></p>'
  ref=self.repo.save('inline',None,s);self.assertEqual(m.receive(self.store,ref)['expected'],m.expected(s))
if __name__=='__main__':unittest.main()
