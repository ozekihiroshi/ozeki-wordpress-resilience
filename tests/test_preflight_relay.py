import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('relay',ROOT/'tools/preflight-relay.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RelayTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  p=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());pre=m.wire.load('deployment-preflight')
  self.c=dict(site_id=p['site_id'],config_sha256=pre.capture.digest(p),workspace=str(self.root))
  for k,v in [('profile_file',p),('inventory_file',{}),('connection_file',{})]:
   f=self.root/k;f.write_text(json.dumps(v));self.c[k]=str(f)
  for k in ['report_file','health_file','lock_file']:self.c[k]=str(self.root/k)
 def tearDown(self):self.tmp.cleanup()
 def test_paths(self):
  m.validate(self.c)
  with self.assertRaises(ValueError):m.validate(dict(self.c,report_file=self.c['profile_file']))
 def test_profile_change(self):
  with self.assertRaises(ValueError):m.tick(dict(self.c,config_sha256='0'*64))
 def test_transfer_failure(self):
  Path(self.c['report_file']).mkdir()
  with patch.object(m.wire,'inspect',return_value={'host_observation':{'state':'validated_report'}}):r=m.tick(self.c)
  self.assertEqual(r['state'],'transfer_failed');self.assertIsNone(r['report_at'])
 def test_acquisition_failure(self):
  with patch.object(m.wire,'inspect',side_effect=TimeoutError):r=m.tick(self.c)
  self.assertEqual(r['state'],'acquisition_failed')
  self.assertEqual(json.loads(Path(self.c['report_file']).read_text())['result']['host_observation']['state'],'unavailable')
 def test_health_failure_propagates(self):
  Path(self.c['health_file']).mkdir()
  with patch.object(m.wire,'inspect',side_effect=OSError):
   with self.assertRaises(OSError):m.tick(self.c)

 def test_optional_review_missing_published(self):
  self.c['review_file']=str(self.root/'missing-review.json')
  with patch.object(m.wire,'inspect',return_value={'production_ready':False,'state':'needs_configuration','issues':[],'host_observation':{'state':'validated_report'}}):m.tick(self.c)
  v=json.loads(Path(self.c['report_file']).read_text())['result']['operator_review']
  self.assertEqual(v['state'],'missing');self.assertFalse(v['automatic_checks_passed'])
 def test_review_path_cannot_overwrite_input(self):
  with self.assertRaises(ValueError):m.validate(dict(self.c,review_file=self.c['report_file']))

if __name__=='__main__':unittest.main()
