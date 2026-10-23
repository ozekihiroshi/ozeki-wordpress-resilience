import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('recovery_worker',Path(__file__).resolve().parents[1]/'tools/site-reconstruction-worker.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
class Recovery(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
        self.c={'transport':'filesystem-lab','work':str(self.p/'store'),'prefix':'test/','bridge':str(self.p/'bridge'),'recovery_work':str(self.p/'recovery'),'target_label':'Private test','wordpress_image':'sha256:'+'a'*64,'database_image':'sha256:'+'b'*64}
        site={'schema':'owr-site-materials-v1','title':'Source','landing':'company','entries':[{'id':'company','kind':'page','title':'Company','slug':'company','parent':None,'nodes':[{'type':'paragraph','text':'Original'}]}]}
        self.store=w.w.store(self.c);self.ref=w.m.Repository(self.store,self.p/'store/journal','test/').save('edit',None,site);self.calls=0
        self.state=w.cycle(self.c,self.run_target);self.item=self.state['items'][0]
    def run_target(self,c,bundle,target):
        self.calls+=1;v=json.loads((bundle/'received.json').read_bytes())
        return {'state':'verified-private','logical_sha256':w.m.sha(w.m.canon(v['expected'])),'side_effect_attempts':0,'public_activation':False}
    def request(self,**changes):
        q={'generation':self.item['id'],'q':self.item['q'],'profile':self.state['profile']};q.update(changes);q['job']=w.m.sha(w.m.canon(q));w.m.atomic(self.p/'bridge/reconstruction/requests'/ (q['job']+'.json'),q);return q
    def test_catalog_and_read_only(self):
        files={p.name:p.read_bytes() for p in (self.p/'store/objects').glob('*')};w.cycle(self.c,self.run_target)
        self.assertEqual(files,{p.name:p.read_bytes() for p in (self.p/'store/objects').glob('*')});self.assertEqual(self.calls,0);self.assertEqual(self.item['assets'],1)
    def test_request_reconstructs_exact_Q_once(self):
        self.request();a=w.cycle(self.c,self.run_target);w.cycle(self.c,self.run_target);self.assertEqual(self.calls,1);self.assertEqual(a['jobs'][0]['state'],'verified')
    def test_wrong_Q_rejected_before_target(self):
        self.request(q='0'*64);a=w.cycle(self.c,self.run_target);self.assertEqual(self.calls,0);self.assertEqual(a['jobs'][0]['state'],'failed')
    def test_profile_change_rejected(self):
        self.request();self.c['target_label']='Other';w.cycle(self.c,self.run_target);self.assertEqual(self.calls,0)
    def test_corrupt_fixed_object_blocks_target(self):
        self.request();p=next((self.p/'store/objects').glob('*'));v=json.loads(p.read_bytes());v['raw']='AAAA';p.write_text(json.dumps(v));w.cycle(self.c,self.run_target);self.assertEqual(self.calls,0)
    def test_interrupted_job_not_reexecuted(self):
        q=self.request();w.m.atomic(self.p/'recovery/jobs'/(q['job']+'.json'),{'job':q['job'],'generation':q['generation'],'state':'running'})
        a=w.cycle(self.c,self.run_target);self.assertEqual(self.calls,0);self.assertEqual(a['jobs'][0]['state'],'interrupted')
    def test_failure_not_reexecuted(self):
        def fail(*args):self.calls+=1;raise RuntimeError('injected')
        self.request();w.cycle(self.c,fail);w.cycle(self.c,fail);self.assertEqual(self.calls,1)
    def test_wrong_result_not_verified(self):
        def bad(*args):return {'state':'verified-private','logical_sha256':'0'*64,'side_effect_attempts':0,'public_activation':False}
        self.request();a=w.cycle(self.c,bad);self.assertEqual(a['jobs'][0]['state'],'failed')
    def test_live_reader_does_not_share_writer_transport_journal(self):
        self.c['transport']='experimental-s3'
        with patch.object(w.w,'store',return_value=self.store) as factory:
            w.cycle(self.c,self.run_target)
            self.assertEqual(factory.call_args.args[0]['work'],str(self.p/'recovery/reader'))
            self.assertEqual(self.c['work'],str(self.p/'store'))
    def test_unchanged_catalog_does_not_read_storage(self):
        with patch.object(w.m,'receive',side_effect=AssertionError('unexpected storage read')):
            a=w.cycle(self.c,self.run_target)
        self.assertTrue(a['items'][0]['catalog_cached'])
    def test_cache_expiry_rechecks(self):
        for p in (self.p/'recovery/catalog').glob('*.json'):
            v=json.loads(p.read_bytes());v['checked_at']-=3601;p.write_text(json.dumps(v))
        with patch.object(w.m,'receive',wraps=w.m.receive) as receive:
            w.cycle(self.c,self.run_target);self.assertEqual(receive.call_count,1)
    def test_retention_loss_after_catalog_blocks_execution(self):
        self.request()
        for p in (self.p/'store/objects').glob('*'):
            v=json.loads(p.read_bytes());v['until']=0;p.write_text(json.dumps(v))
        a=w.cycle(self.c,self.run_target)
        self.assertEqual(self.calls,0);self.assertEqual(a['jobs'][0]['state'],'failed')
    def test_request_always_refetches_once(self):
        self.request()
        with patch.object(w.m,'receive',wraps=w.m.receive) as receive:
            w.cycle(self.c,self.run_target);self.assertEqual(receive.call_count,1)
if __name__=='__main__':unittest.main()
