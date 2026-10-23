import base64, copy, importlib.util, tempfile, time, unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'tools/site-materials.py'
s=importlib.util.spec_from_file_location('materials',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Store:
    def __init__(self):self.objects={};self.writes=0;self.fail=False
    def put(self,raw,key):
        if self.fail:raise RuntimeError('Injected storage failure')
        if key not in self.objects:self.writes+=1;self.objects[key]=raw
        elif self.objects[key]!=raw:raise ValueError('Immutable conflict')
        return {'locator':{'key':key,'version_id':m.sha(raw)},'size_bytes':len(raw),'sha256':m.sha(raw)}
    def get(self,ref):
        raw=self.objects[ref['locator']['key']]
        if m.sha(raw)!=ref['sha256']:raise ValueError('Changed bytes')
        return raw,time.time()+36*86400,time.time()
def site():return {'schema':'owr-site-materials-v1','title':'試験会社','landing':'company','entries':[{'id':'company','kind':'page','title':'会社案内','slug':'company','parent':None,'nodes':[{'type':'paragraph','text':'独立した原本'}]}]}
class Tests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.store=Store();self.repo=m.Repository(self.store,self.tmp.name,'test/')
    def tearDown(self):self.tmp.cleanup()
    def test_roundtrip_and_dedup(self):
        a=site();one=self.repo.save('one',None,a);count=self.store.writes;two=self.repo.save('two',one,a)
        self.assertEqual(self.store.writes,count+1);self.assertEqual(m.receive(self.store,two)['expected'],m.expected(a));self.assertEqual(self.repo.save('two',one,a),two)
    def test_more_than_100_edits(self):
        a=site();head=None
        for i in range(105):a['entries'][0]['title']=str(i);head=self.repo.save('op'+str(i),head,a)
        self.assertEqual(m.receive(self.store,head)['site']['entries'][0]['title'],'104')
    def test_stale_before_write(self):
        self.repo.save('one',None,site());n=self.store.writes
        with self.assertRaises(ValueError):self.repo.save('two',None,site())
        self.assertEqual(n,self.store.writes)
    def test_failure_resume(self):
        self.store.fail=True
        with self.assertRaises(RuntimeError):self.repo.save('one',None,site())
        self.assertFalse((Path(self.tmp.name)/'head.json').exists());self.store.fail=False
        one=self.repo.save('one',None,site());self.assertEqual(m.receive(self.store,one)['site'],site())
    def test_old_replay(self):
        a=self.repo.save('one',None,site());self.repo.save('two',a,site())
        with self.assertRaises(ValueError):self.repo.save('one',None,site())
    def test_dangling(self):
        a=site();a['entries'][0]['nodes']=[{'type':'image','target':'missing'}]
        with self.assertRaises(ValueError):self.repo.save('one',None,a)
        self.assertEqual(self.store.writes,0)
    def test_signature_not_bypassed(self):
        one=self.repo.save('one',None,site(),'independent-signature',{'signature':'test'})
        with self.assertRaises(ValueError):m.receive(self.store,one)
    def test_parent_cycle(self):
        a=site();a['entries'][0]['parent']='company'
        with self.assertRaises(ValueError):m.normalize(a)
    def test_markdown(self):
        self.assertEqual(m.markdown('## 見出し\n本文')[0]['type'],'heading')
        with self.assertRaises(ValueError):m.markdown('<script>')
    def test_committed_receipt_head_recovery(self):
        a=self.repo.save('one',None,site());n=self.store.writes;(Path(self.tmp.name)/'head.json').unlink()
        self.assertEqual(self.repo.save('one',None,site()),a);self.assertEqual(self.store.writes,n)
    def test_changed_request_on_resume(self):
        self.store.fail=True
        with self.assertRaises(RuntimeError):self.repo.save('one',None,site())
        self.store.fail=False;a=site();a['title']='different'
        with self.assertRaises(ValueError):self.repo.save('one',None,a)
        self.assertEqual(self.store.writes,0)
    def test_two_concurrent_writers(self):
        import concurrent.futures,threading
        barrier=threading.Barrier(2)
        def save(op):
            barrier.wait()
            try:return self.repo.save(op,None,site())
            except ValueError:return None
        with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(save,['one','two']))
        self.assertEqual(sum(x is not None for x in results),1)
    def test_tampered_original(self):
        a=self.repo.save('one',None,site());manifest=__import__('json').loads(self.store.get(a)[0]);ref=manifest['objects'][0]['ref'];self.store.objects[ref['locator']['key']]=b'wrong'
        with self.assertRaises(ValueError):m.receive(self.store,a)
    def test_retention_copy_without_mutation(self):
        a=self.repo.save('one',None,site());old=dict(self.store.objects);original_get=self.store.get
        def get(ref):
            raw,until,stored=original_get(ref)
            if ref['locator']['key'] in old:until=time.time()+86400
            return raw,until,stored
        self.store.get=get;b=self.repo.save('two',a,site())
        self.assertTrue(all(self.store.objects[k]==v for k,v in old.items()));self.assertEqual(m.receive(self.store,b)['expected'],m.expected(site()))
    def test_new_retention_window(self):
        from unittest.mock import patch
        a=self.repo.save('one',None,site());count=self.store.writes;future=time.time()+40*86400
        with patch.object(m.time,'time',return_value=future):b=self.repo.save('two',a,site())
        self.assertEqual(self.store.writes,count+2)
if __name__=='__main__':unittest.main()
