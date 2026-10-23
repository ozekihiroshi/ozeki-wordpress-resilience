import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('console',Path(__file__).resolve().parents[1]/'tools/rbr-console-worker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Executor:
    def __init__(self):self.calls=0;self.blocked=False;self.fail=False
    def verify(self,*a):
        if self.blocked:raise ValueError('revoked')
    def verify_received(self,*a):pass
    def execute(self,*a,**kw):
        self.calls+=1
        if self.fail:raise ValueError('failed')
class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
        for n in ('inbox','state','work/bundle'): (self.p/n).mkdir(parents=True)
        m.atomic(self.p/'approval',{'expires_at':'test'});m.atomic(self.p/'receipt',{'sha256':'root'})
        m.atomic(self.p/'work/bundle/definition.json',{'assets_ref':{'sha256':'generation'},'expected_ref':{'sha256':'request-Q'}})
        self.item={'item_id':'test','origin':'generated','generation':{'sha256':'generation'},'site_id':'site','set_id':'set',**{n:str(self.p/n) for n in ('trust','approval','signature','receipt','work')}}
        self.config={'items':[self.item],**{n:str(self.p/n) for n in ('inbox','state','report')}};self.e=Executor()
    def request(self):
        t=m.token(self.item);rid=m.digest(('test:'+t).encode());m.atomic(self.p/'inbox'/(rid+'.json'),{'item_id':'test','token':t});return rid
    def test_success_and_duplicate(self):
        self.request();r=m.cycle(self.config,self.e);self.assertEqual(r['items'][0]['result']['state'],'verified');m.cycle(self.config,self.e);self.assertEqual(self.e.calls,1)
    def test_revoked(self):
        self.request();self.e.blocked=True;r=m.cycle(self.config,self.e);self.assertEqual(self.e.calls,0);self.assertEqual(r['items'][0]['approval'],'blocked')
    def test_wrong_generation(self):
        self.request();self.item['generation']={'sha256':'other'};r=m.cycle(self.config,self.e);self.assertEqual(r['items'][0]['approval'],'blocked');self.assertEqual(self.e.calls,0)
    def test_interrupted(self):
        rid=self.request();m.atomic(self.p/'state'/(rid+'.json'),{'state':'running'});r=m.cycle(self.config,self.e);self.assertEqual(r['items'][0]['result']['state'],'interrupted');self.assertEqual(self.e.calls,0)
    def test_failure_not_retried(self):
        self.request();self.e.fail=True;m.cycle(self.config,self.e);m.cycle(self.config,self.e);self.assertEqual(self.e.calls,1)
    def test_symlink(self):
        rid=self.request();path=self.p/'inbox'/(rid+'.json');path.unlink();path.symlink_to(self.p/'approval');m.cycle(self.config,self.e);self.assertEqual(self.e.calls,0)
    def test_wrong_request_q(self):
        self.item['q_sha256']='different-Q';self.request();r=m.cycle(self.config,self.e);self.assertEqual(r['items'][0]['approval'],'blocked');self.assertEqual(self.e.calls,0)
    def test_matching_request_q(self):
        self.item['q_sha256']='request-Q';self.item['require_local_match']=True;self.request();r=m.cycle(self.config,self.e);self.assertEqual(r['items'][0]['result']['state'],'verified');self.assertTrue(r['items'][0]['require_local_match'])
    def test_tampered_request(self):
        rid=self.request();m.atomic(self.p/'inbox'/(rid+'.json'),{'item_id':'test','token':m.token(self.item),'command':'bad'});m.cycle(self.config,self.e);self.assertEqual(self.e.calls,0)
if __name__=='__main__':unittest.main()
