import importlib.util,tempfile,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('preview',ROOT/'tools/portable-preview.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Anchors(unittest.TestCase):
 def build(self,body,legacy=False):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);r=Path(t.name)
  source=dict(format='owr-portable-source-v1',selected=[1],records=[dict(id=1,type='page',status='publish',title='Test',body=body,url='https://example.invalid/',parent=0,featured=None)],media=[],observation={'records_unchanged':True,'atomic_snapshot':False})
  m.p.extract(source,r/'source')
  if legacy:
   f=r/'source/content/1.json';d=m.p.load(f);d['nodes']=[n for n in d['nodes'] if n['kind']!='anchor'];m.p.write(f,d)
   f=r/'source/manifest.json';d=m.p.load(f);d['hashes']['content/1.json']=m.p.digest((r/'source/content/1.json').read_bytes());m.p.write(f,d)
  result=m.build(r/'source',r/'out');return (r/'out/page-1.html').read_text(),result
 def test_position_unicode(self):
  text,result=self.build('<p>Before</p><h2 id="会社">Company</h2><p><a href="#%E4%BC%9A%E7%A4%BE">Jump</a></p>')
  ident='anchor-'+hashlib.sha256('会社'.encode()).hexdigest()
  self.assertIn('<p>Before</p><span id="'+ident+'"></span><h2>',text)
  self.assertIn('href="page-1.html#'+ident+'"',text)
  self.assertNotIn('anchor_position_not_preserved',[x['code'] for x in result['issues']])
 def test_duplicate_falls_back(self):
  text,result=self.build('<h2 id="x">One</h2><h2 id="x">Two</h2><a href="#x">Jump</a>')
  self.assertNotIn('href="page-1.html#',text);self.assertIn('anchor_position_not_preserved',[x['code'] for x in result['issues']])
 def test_legacy_falls_back(self):
  text,result=self.build('<h2 id="x">One</h2><a href="#x">Jump</a>',True)
  self.assertIn('anchor_position_not_preserved',[x['code'] for x in result['issues']])
 def test_suppressed_target_not_recreated(self):
  text,result=self.build('<script id="x">bad()</script><a href="#x">Jump</a>')
  self.assertNotIn('href="page-1.html#',text);self.assertNotIn('<script',text)
if __name__=='__main__':unittest.main()
