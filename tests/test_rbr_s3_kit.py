"""Offline guard tests for the real-S3 kit adapter; no credential/network use."""
import datetime as dt, importlib.util, unittest, tempfile
from pathlib import Path
r=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('rbr_s3_kit',r/'tools/rbr-s3-kit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Adapter:
    def __init__(self):
        self.operations=[];self.puts=0;now=dt.datetime.now(dt.timezone.utc)
        self.response={'body':b'fixture','version_id':'fixed-version','mode':'GOVERNANCE','retain_until':(now+dt.timedelta(days=35,minutes=10)).isoformat(),'last_modified':now.isoformat()}
    def get(self,locator):return self.response
    def put(self,*args):self.puts+=1;raise AssertionError('Must not retry')
class Kit(unittest.TestCase):
    def setUp(self):
        self.a=Adapter();self.store=m.Store.__new__(m.Store);self.store.adapter=self.a
        self.key='sites/isolated-queue-lab/sets/AWS-0123456789abcdef/rbr-'+m.sha(b'fixture')+'.blob'
        self.ref={'locator':{'kind':'s3','bucket':m.transport.BUCKET,'region':m.transport.REGION,'key':self.key,'version_id':'fixed-version'},'size_bytes':7,'sha256':m.sha(b'fixture')}
    def test_new_empty_store_can_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'s3'
            m.Store(path)
            self.assertEqual(m.Store(path).adapter.operations,[])
    def test_existing_missing_journal_is_not_reset(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):m.Store(Path(root))
            self.assertFalse((Path(root)/'operations.json').exists())
    def test_fixed_bytes_and_retention(self):self.assertEqual(self.store.get(self.ref),b'fixture')
    def test_bad_hash(self):
        self.a.response['body']=b'changed'
        with self.assertRaises(ValueError):self.store.get(self.ref)
    def test_wrong_version(self):
        self.a.response['version_id']='other'
        with self.assertRaises(ValueError):self.store.get(self.ref)
    def test_short_retention(self):
        self.a.response['retain_until']=self.a.response['last_modified']
        with self.assertRaises(ValueError):self.store.get(self.ref)
    def test_uncertain_put_never_resent(self):
        self.a.operations=[{'method':'PUT','key':self.key,'state':'started'}]
        with self.assertRaises(RuntimeError):self.store.put(b'fixture',self.key)
        self.assertEqual(self.a.puts,0)
    def test_acknowledged_put_reused(self):
        self.a.operations=[{'method':'PUT','key':self.key,'state':'acknowledged','sha256':m.sha(b'fixture'),'bytes':7,'version_id':'fixed-version'}]
        self.assertEqual(self.store.put(b'fixture',self.key),self.ref);self.assertEqual(self.a.puts,0)
    def test_foreign_key(self):
        self.ref['locator']['key']='sites/production/data'
        with self.assertRaises(ValueError):self.store.get(self.ref)
if __name__=='__main__':unittest.main()
