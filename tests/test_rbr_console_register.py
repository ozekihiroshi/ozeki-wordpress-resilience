import importlib.util,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('register',Path(__file__).resolve().parents[1]/'tools/rbr-console-register.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class BindingTests(unittest.TestCase):
 def setUp(self):
  self.save={'state':'applied','sequence':1,'generation':{'sha256':'g'},'expected_ref':{'sha256':'bound'}}
  self.d={'assets_ref':{'sha256':'g'},'expected_ref':{'sha256':'Q'}};self.root={'schema':'owr-rbr-s3-kit-v2','expected_binding_ref':{'sha256':'bound'}}
 def test_exact(self):self.assertEqual(m.bind(self.save,self.d,self.root),'Q')
 def test_other_generation(self):
  self.d['assets_ref']={'sha256':'other'}
  with self.assertRaises(ValueError):m.bind(self.save,self.d,self.root)
 def test_other_q_binding(self):
  self.root['expected_binding_ref']={'sha256':'other'}
  with self.assertRaises(ValueError):m.bind(self.save,self.d,self.root)
 def test_pending(self):
  self.save['state']='stored'
  with self.assertRaises(ValueError):m.bind(self.save,self.d,self.root)
if __name__=='__main__':unittest.main()
