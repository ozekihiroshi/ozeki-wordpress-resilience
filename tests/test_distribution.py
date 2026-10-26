import contextlib,hashlib,importlib.util,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('distribution',Path(__file__).resolve().parents[1]/'tools/build-release.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
class DistributionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'source';self.root.mkdir()
  for name in set(b.PLUGIN+b.TOP):
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('Version: '+b.VERSION if name=='ozeki-wordpress-resilience.php' else 'fixture')
 def build(self,name):
  out=Path(self.tmp.name)/name
  with patch.object(b,'ROOT',self.root),contextlib.redirect_stdout(io.StringIO()):b.build(out)
  return out,json.loads((out/'manifest.json').read_text())
 def test_plugin_allowlist_and_hashes(self):
  out,m=self.build('one');item=m['artifacts'][0]
  with zipfile.ZipFile(out/item['file']) as z:self.assertEqual(set(z.namelist()),{'ozeki-resilience/'+x for x in b.PLUGIN})
  self.assertEqual(item['sha256'],hashlib.sha256((out/item['file']).read_bytes()).hexdigest())
 def test_editor_asset_shipped_in_development_kit_only(self):
  asset=self.root/'assets/rbr-editor.js';asset.parent.mkdir(exist_ok=True);asset.write_text('/* editor asset */')
  out,m=self.build('editor');plugin,kit=m['artifacts']
  self.assertNotIn('assets/rbr-editor.js',plugin['files'])
  self.assertIn('assets/rbr-editor.js',kit['files'])
 def test_reproducible_bytes(self):
  a,x=self.build('one');c,y=self.build('two');self.assertEqual(x,y)
  for item in x['artifacts']:self.assertEqual((a/item['file']).read_bytes(),(c/item['file']).read_bytes())
 def test_private_work_and_cache_excluded(self):
  for name in ['.local/secret.json','vendor/secret.php','evidence/raw.json','tools/__pycache__/secret.py','tools/.local/secret.json']:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('DO NOT SHIP')
  _,m=self.build('one');self.assertFalse(any('secret' in f for item in m['artifacts'] for f in item['files']))
 def test_secret_rejected(self):
  (self.root/'src/NotificationAdmin.php').write_text('-----BEGIN '+'PRIVATE KEY-----')
  with self.assertRaises(ValueError):self.build('one')
 def test_version_mismatch_rejected(self):
  (self.root/'ozeki-wordpress-resilience.php').write_text('Version: wrong')
  with self.assertRaises(ValueError):self.build('one')
 def test_symlink_rejected(self):
  p=self.root/'src/NotificationAdmin.php';p.unlink();outside=Path(self.tmp.name)/'external';outside.write_text('external');p.symlink_to(outside)
  with self.assertRaises(ValueError):self.build('one')
 def test_existing_output_not_overwritten(self):
  out,_=self.build('one');before=(out/'manifest.json').read_bytes()
  with self.assertRaises(FileExistsError):self.build('one')
  self.assertEqual(before,(out/'manifest.json').read_bytes())
if __name__=='__main__':unittest.main()
