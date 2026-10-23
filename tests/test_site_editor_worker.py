import importlib.util,json,tempfile,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('editor_worker',root/'tools/site-editor-worker.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.b=Path(self.temp.name);(self.b/'bridge/requests').mkdir(parents=True);(self.b/'bridge/reports').mkdir();self.c={'work':str(self.b/'work'),'bridge':str(self.b/'bridge'),'prefix':'test/','transport':'filesystem-lab'}
        self.site={'schema':'owr-site-materials-v1','title':'Test','landing':'company','entries':[{'id':'company','kind':'page','title':'Company','slug':'company','parent':None,'nodes':[{'type':'paragraph','text':'Original'}]}]};self.q={'operation':'editor-'+'a'*32,'attempt':1,'parent':None,'site':self.site};self.q['request_sha256']=w.m.sha(w.m.canon({'parent':None,'site':self.site}));self.write()
    def write(self):(self.b/'bridge/requests'/('editor-'+'a'*32+'-'+str(self.q['attempt'])+'.json')).write_bytes(w.m.canon(self.q))
    def report(self):return json.loads((self.b/'bridge/reports'/('editor-'+'a'*32+'.json')).read_bytes())
    def tearDown(self):self.temp.cleanup()
    def test_save(self):
        w.process(self.c);self.assertEqual(self.report()['state'],'stored');self.assertEqual(self.report()['received']['site'],self.site)
    def test_pre_save_failure_retry_same_operation(self):
        def fail(stage):raise RuntimeError('Injected')
        w.process(self.c,fail);self.assertEqual(self.report()['state'],'failed');self.assertFalse((self.b/'work/journal/head.json').exists());self.q['attempt']=2;self.write();w.process(self.c);self.assertEqual(self.report()['state'],'stored')
    def test_process_stopped_after_store(self):
        def stop(stage):
            if stage=='after_save':raise SystemExit(77)
        with self.assertRaises(SystemExit):w.process(self.c,stop)
        count=len(list((self.b/'work/objects').glob('*.json')));head=(self.b/'work/journal/head.json').read_bytes();self.assertEqual(self.report()['state'],'working');w.process(self.c);self.assertEqual(self.report()['state'],'stored');self.assertEqual((self.b/'work/journal/head.json').read_bytes(),head);self.assertEqual(len(list((self.b/'work/objects').glob('*.json'))),count)
    def test_changed_request_identity_rejected(self):
        self.q['site']['title']='Changed';self.write()
        with self.assertRaises(ValueError):w.process(self.c)
        self.assertFalse((self.b/'work/journal/head.json').exists())
    def test_oversize_reports_failure_without_objects_or_head(self):
        self.q['site']['entries'][0]['nodes']=[{'type':'paragraph','text':'a'*20000} for _ in range(320)]
        self.q['request_sha256']=w.m.sha(w.m.canon({'parent':None,'site':self.q['site']}));self.write()
        w.process(self.c)
        self.assertEqual(self.report()['state'],'failed')
        self.assertEqual(self.report()['reason'],'validation-or-save-failed')
        self.assertEqual(list((self.b/'work/objects').glob('*.json')),[])
        self.assertFalse((self.b/'work/journal/head.json').exists())
        self.assertEqual(list((self.b/'work/journal').glob('*.json')),[])
if __name__=='__main__':unittest.main()
