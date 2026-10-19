import copy,importlib.util,sqlite3,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('queue_pair',ROOT/'tools/queue-recovery.py')
pair=importlib.util.module_from_spec(spec);spec.loader.exec_module(pair)
class PairTests(unittest.TestCase):
    def setUp(self):
        self.token='a'*32
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'q'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE control(id INTEGER,checkpoint TEXT)');db.execute('INSERT INTO control VALUES(1,?)',(self.token,))
                db.execute('CREATE TABLE jobs(id TEXT,kind TEXT,state TEXT)');db.execute("INSERT INTO jobs VALUES('job1','write','pending')")
            self.assets={'queue':p.read_bytes(),'database':b'db','files':b'files'}
        self.manifest={'format':pair.FORMAT,'site_id':'lab','checkpoint':self.token,'handler_sha256':'b'*64,'assets':{k:pair.digest(v) for k,v in self.assets.items()}}
    def validate(self,m=None,a=None,site='lab',handler='b'*64):return pair.validate(m or self.manifest,a or self.assets,site,handler)
    def test_valid(self):self.assertEqual(self.validate(),self.token)
    def test_done_without_db_effect_rejected(self):
        with self.assertRaises(ValueError):pair.reconcile_done([{'id':'x','kind':'write','state':'done'}],{}, {})
    def test_done_without_file_effect_rejected(self):
        with self.assertRaises(ValueError):pair.reconcile_done([{'id':'x','kind':'write','state':'done'}],{'x':{'kind':'write','path':'x.txt','sha256':'a'*64}}, {})
    def test_matching_done_effect_accepted(self):
        pair.reconcile_done([{'id':'x','kind':'write','state':'done'}],{'x':{'kind':'write','path':'x.txt','sha256':'a'*64}}, {'x.txt':'a'*64})
    def test_asset_corruption(self):
        for key in self.assets:
            with self.subTest(key=key):
                a=dict(self.assets);a[key]+=b'wrong'
                with self.assertRaises(ValueError):self.validate(a=a)
    def test_missing_asset(self):
        a=dict(self.assets);del a['queue']
        with self.assertRaises(ValueError):self.validate(a=a)
    def test_mixed_checkpoint(self):
        m=copy.deepcopy(self.manifest);m['checkpoint']='c'*32
        with self.assertRaises(ValueError):self.validate(m=m)
    def test_wrong_site(self):
        with self.assertRaises(ValueError):self.validate(site='different')
    def test_wrong_handler(self):
        with self.assertRaises(ValueError):self.validate(handler='c'*64)
    def test_unknown_format(self):
        m=copy.deepcopy(self.manifest);m['format']='v999'
        with self.assertRaises(ValueError):self.validate(m=m)
    def test_sqlite_corruption_even_with_matching_hash(self):
        a=dict(self.assets);a['queue']=b'not sqlite';m=copy.deepcopy(self.manifest);m['assets']['queue']=pair.digest(a['queue'])
        with self.assertRaises(ValueError):self.validate(m=m,a=a)
    def test_unknown_job_quarantined_before_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'q';p.write_bytes(self.assets['queue'])
            with sqlite3.connect(p) as db:db.execute("UPDATE jobs SET kind='send_payment'")
            a=dict(self.assets);a['queue']=p.read_bytes();m=copy.deepcopy(self.manifest);m['assets']['queue']=pair.digest(a['queue'])
        with self.assertRaises(ValueError):self.validate(m=m,a=a)
if __name__=='__main__':unittest.main()
