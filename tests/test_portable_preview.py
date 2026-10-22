import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('preview',ROOT/'tools/portable-preview.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Preview(unittest.TestCase):
 def setup_package(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);r=Path(tmp.name)
  source=dict(format='owr-portable-source-v1',selected=[1],records=[dict(id=1,type='page',status='publish',title='<script>title</script>',body='<p>Hello <a href="https://external.invalid/">outside</a></p><script>bad</script>',url='https://example.invalid/',parent=0,featured=None)],media=[],observation={'records_unchanged':True,'atomic_snapshot':False})
  m.p.extract(source,r/'source');return r
 def test_safe_html_and_no_originals(self):
  r=self.setup_package();v=m.build(r/'source',r/'preview');body=(r/'preview/page-1.html').read_text()
  self.assertNotIn('<script>',body);self.assertNotIn('href="https:',body);self.assertIn('&lt;script&gt;',body);self.assertIn('Content-Security-Policy',body);self.assertFalse((r/'preview/raw').exists());self.assertFalse(v['publication_authorized'])
 def test_tamper_blocks(self):
  r=self.setup_package();(r/'source/content/1.json').write_text('{}')
  with self.assertRaises(ValueError):m.build(r/'source',r/'out')
  self.assertFalse((r/'out').exists())
 def test_overlap_and_existing_refused(self):
  r=self.setup_package()
  with self.assertRaises(ValueError):m.build(r/'source',r/'source/out')
  m.build(r/'source',r/'out')
  with self.assertRaises(FileExistsError):m.build(r/'source',r/'out')
 def test_symlink_rejected(self):
  r=self.setup_package();f=r/'source/content/1.json';b=f.read_bytes();f.unlink();(r/'elsewhere').write_bytes(b);f.symlink_to(r/'elsewhere')
  with self.assertRaises(ValueError):m.build(r/'source',r/'out')
 def test_incomplete_refused(self):
  r=self.setup_package();f=r/'source/manifest.json';d=json.loads(f.read_text());d['state']='incomplete';f.write_text(json.dumps(d))
  with self.assertRaises(ValueError):m.build(r/'source',r/'out')
 def test_deterministic(self):
  r=self.setup_package();a=m.build(r/'source',r/'a');b=m.build(r/'source',r/'b');self.assertEqual(a['output_hashes'],b['output_hashes'])
 def test_unsafe_manifest_path(self):
  r=self.setup_package();f=r/'source/manifest.json';d=json.loads(f.read_text());d['hashes']['../elsewhere']='x';f.write_text(json.dumps(d))
  with self.assertRaises(ValueError):m.build(r/'source',r/'out')
if __name__=='__main__':unittest.main()
