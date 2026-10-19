import copy,datetime as dt,importlib.util,sqlite3,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
g=module('protected_queue','protected-queue-set.py');lab=module('protected_queue_lab','protected-queue-lab.py')
class ProtectedQueueTests(unittest.TestCase):
    def setUp(self):
        self.body=b'fixture';t=g.now()
        self.loc={'version_id':'v1','size_bytes':len(self.body),'sha256':g.sha(self.body)}
        self.response={'version_id':'v1','reader_identity':'reader','mode':'GOVERNANCE','last_modified':t.isoformat(),'retain_until':(t+dt.timedelta(days=35)).isoformat()}
    def observe(self):return g.observe('queue',self.body,self.loc,self.response,'reader')
    def test_valid_exact_version_observation(self):self.assertEqual(self.observe()['role'],'queue')
    def test_wrong_version(self):
        self.response['version_id']='v2'
        with self.assertRaises(ValueError):self.observe()
    def test_wrong_reader(self):
        self.response['reader_identity']='writer'
        with self.assertRaises(ValueError):self.observe()
    def test_same_size_changed_bytes(self):
        self.body=b'FIXTURE'
        with self.assertRaises(ValueError):self.observe()
    def test_missing_lock(self):
        self.response['mode']=None
        with self.assertRaises(ValueError):self.observe()
    def test_short_retention(self):
        self.response['retain_until']=(g.now()+dt.timedelta(days=34)).isoformat()
        with self.assertRaises(ValueError):self.observe()
    def test_future_modification(self):
        self.response['last_modified']=(g.now()+dt.timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):self.observe()
    def test_timezone_required(self):
        self.response['retain_until']='2099-01-01T00:00:00'
        with self.assertRaises(ValueError):self.observe()
    def test_shared_role_rejected_before_upload(self):
        def unexpected(*a):raise AssertionError('upload attempted')
        with self.assertRaises(ValueError):g.build({}, {},'site','set','bucket','region','same','same',unexpected,unexpected)
    def test_unpaired_capture_rejected_before_upload(self):
        def unexpected(*a):raise AssertionError('upload attempted')
        with self.assertRaises(ValueError):g.build({}, {'handler_sha256':'0'*64},'site','set','bucket','region','writer','reader',unexpected,unexpected)
    def test_signed_roundtrip_and_negative_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'queue.sqlite'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE control(id INTEGER,checkpoint TEXT)');db.execute('INSERT INTO control VALUES(1,?)',('a'*32,))
                db.execute('CREATE TABLE jobs(id TEXT,kind TEXT,state TEXT)');db.execute("INSERT INTO jobs VALUES('job','write','pending')")
            assets={'queue':p.read_bytes(),'database':b'sql','files':b'tar'}
            paired={'format':'owr-paired-queue-v1','site_id':'unit-lab','checkpoint':'a'*32,'handler_sha256':'b'*64,'assets':{k:g.sha(v) for k,v in assets.items()}}
            cases=[];restored,evidence=lab.exercise(assets,paired,lambda name:cases.append(name))
            self.assertEqual(restored,assets);self.assertEqual(len(cases),14);self.assertEqual(evidence['aws_calls'],0)
            self.assertFalse(evidence['verification']['production_recovery_approved'])
if __name__=='__main__':unittest.main()
