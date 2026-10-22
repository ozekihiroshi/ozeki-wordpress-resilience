import base64
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('portable',ROOT/'tools/portable-content.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Extraction(unittest.TestCase):
    def fixture(self):
        return dict(format='owr-portable-source-v1',selected=[1],records=[dict(id=1,type='page',status='publish',title='Company',body='<h2 id="a">Hello</h2><p>Text</p>',url='https://example.invalid/?page_id=1',parent=0,featured=None)],media=[],observation={'records_unchanged':True,'atomic_snapshot':False})
    def extract(self,d):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name)/'package'
        return m.extract(d,p),p
    def test_basic(self):
        v,p=self.extract(self.fixture());self.assertEqual(v['counts']['pages'],1);self.assertFalse(v['static_site_generated']);self.assertIn('Hello',(p/'readable/1.txt').read_text())
    def test_outside_scope(self):
        for field,value in [('status','draft'),('type','secret'),('id',2)]:
            d=self.fixture();d['records'][0][field]=value
            with self.assertRaises(ValueError):self.extract(d)
    def test_duplicate_ids(self):
        d=self.fixture();d['records']*=2
        with self.assertRaises(ValueError):self.extract(d)
    def test_active_content(self):
        d=self.fixture();d['records'][0]['body']='<script>evil</script><p onclick="bad()">Good</p><a href="javascript:bad()">link</a>'
        v,p=self.extract(d);self.assertNotIn('evil',(p/'readable/1.txt').read_text());self.assertIn('scheme_or_credentials_requires_review',(p/'relations.json').read_text());self.assertIn('attribute_not_converted',(p/'issues.json').read_text())
    def test_missing_anchors_and_relative_links(self):
        d=self.fixture();d['records'][0]['body']='<p id="ok"><a href="#ok">OK</a><a href="#absent">Missing</a></p>'
        _,p=self.extract(d);self.assertIn('missing_anchor',(p/'relations.json').read_text());self.assertIn('"target": 1',(p/'relations.json').read_text())
    def test_bad_image_hash_retains_incomplete(self):
        d=self.fixture();d['media']=[dict(id=10,state='copied',base64=base64.b64encode(b'x').decode(),sha256='bad',url='https://example.invalid/x',name='../../x')]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'p'
            with self.assertRaises(ValueError):m.extract(d,p)
            self.assertIn('incomplete',(p/'manifest.json').read_text())
    def test_safe_output_names(self):
        d=self.fixture();b=b'\x89PNG\r\n\x1a\nnot_decoded'
        d['media']=[dict(id=10,state='copied',base64=base64.b64encode(b).decode(),sha256=m.digest(b),url='https://example.invalid/x',name='../../escape')]
        _,p=self.extract(d);self.assertTrue((p/'media/10.png').exists());self.assertIn('not_decoded',(p/'media-index.json').read_text())
    def test_source_changes_visible(self):
        d=self.fixture();d['observation']['records_unchanged']=False
        _,p=self.extract(d);self.assertIn('source_changed_or_unconfirmed',(p/'issues.json').read_text())
    def test_malformed_unsupported(self):
        d=self.fixture();d['records'][0]['body']='<table><tr><td>X</table>[form id="1"]'
        _,p=self.extract(d)
        for code in ('unsupported_html','malformed_html','shortcode_or_bracket_syntax'):self.assertIn(code,(p/'issues.json').read_text())
    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError):m.json.loads('{"x":1,"x":2}',object_pairs_hook=m.unique)

if __name__=='__main__':unittest.main()
