"""Offline regression replay of two actual generated WordPress observations, not fabricated P outputs."""
import base64, copy, importlib.util, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rbr_compare',ROOT/'tools/rbr-compare.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Comparison(unittest.TestCase):
    def setUp(self):self.fixture=json.loads((ROOT/'tests/fixtures/rbr-observed-sites.json').read_text());self.q=self.fixture['expected'];self.run=self.fixture['runs'][0]
    def compare(self,r=None):
        r=r or self.run
        return c.compare(r['observation'],r['html'],{k:base64.b64decode(v) for k,v in r['media'].items()},self.q,r['origin'])
    def rejected(self):
        with self.assertRaises((AssertionError,KeyError,ValueError)):self.compare()
    def test_two_actual_origins_and_id_allocations_match(self):
        self.assertNotEqual(self.run['origin'],self.fixture['runs'][1]['origin']);self.assertNotEqual(self.run['observation']['map'],self.fixture['runs'][1]['observation']['map'])
        self.assertEqual(self.compare(),self.compare(self.fixture['runs'][1]))
    def test_contact_change_in_db_and_response(self):
        row=next(x for x in self.run['observation']['rows'] if x['asset_id']=='contact');row['body']=row['body'].replace('TEST-0001','TEST-0002');self.run['html']['contact']=self.run['html']['contact'].replace('TEST-0001','TEST-0002');self.rejected()
    def test_duplicate_mapping(self):
        self.run['observation']['map']['company']=self.run['observation']['map']['services'];self.rejected()
    def test_served_image_corruption(self):self.run['media']['logo']=base64.b64encode(b'wrong').decode();self.rejected()
    def test_missing_served_image(self):self.run['media']={};self.rejected()
    def test_wrong_expected_result(self):self.q['pages']['company']['title']='WRONG EXPECTATION';self.rejected()
    def test_unexpected_page(self):self.run['observation']['rows'].append(copy.deepcopy(self.run['observation']['rows'][0]));self.rejected()
    def test_published_draft(self):
        next(x for x in self.run['observation']['rows'] if x['type']=='page')['status']='publish';self.rejected()
    def test_external_effect_attempt(self):self.run['observation']['side_effect_attempts']=1;self.rejected()
if __name__=='__main__':unittest.main()
