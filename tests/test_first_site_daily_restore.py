import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('recovery',ROOT/'tools/first-site-daily-restore.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)


class Recovery(unittest.TestCase):
    def setUp(self):
        # Legacy signature/transport contracts isolate the new authority; separate root-owned tests cover it.
        if type(self) is Recovery:
            for method in ("current", "unchanged"):
                stub=patch.object(r.current_trust,method,return_value={"revision":1})
                stub.start();self.addCleanup(stub.stop)
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as tar:
            item=tarfile.TarInfo('one.txt'); item.size=3
            tar.addfile(item,io.BytesIO(b'one'))
        self.assets={'database':b'sql','files':buf.getvalue()}
        self.capture=dict(format='owr-first-site-capture-v1',attempt_id='a'*32,site_id='generated-first-site',
            config_sha256='b'*64,state='consistent',eligible_for_consistency_acceptance=True,
            release_confirmed=True,production_recovery_approved=False,queue=dict(state='absent',evidence='fixture'),
            inventory_sha256=r.c.digest({'one.txt':r.g.sha(b'one')}),
            assets={k:dict(attempt_id='a'*32,bytes=len(v),sha256=r.g.sha(v)) for k,v in self.assets.items()})
        self.store={}; self.gets=0; self.constructed=0; self.restores=0; self.mode=None
        self.modified=r.g.now().isoformat();self.until=(r.g.now()+dt.timedelta(days=36)).isoformat()
        def put(bucket,key,body):
            self.store[key]=body;return 'version-one'
        def get(loc):
            self.gets+=1
            body=self.store[loc['key']]
            return dict(body=(b'bad' if self.mode=='bytes' or
                             (self.mode=='second_bytes' and loc['key'].endswith('.tar.gz')) else body),
                version_id=('wrong' if self.mode=='version' else 'version-one'),
                reader_identity='OwrM1RecoveryReader',mode='GOVERNANCE',
                last_modified=self.modified,retain_until=self.until)
        self.get=get
        m=r.g.build(self.assets,self.capture,r.d.SITE,'AWS-'+'1'*16,r.d.transport.BUCKET,r.d.transport.REGION,
                    'my-ssm-role','OwrM1RecoveryReader',put,get)
        self.gets=0
        pub=self.root/'publisher';pub.mkdir();doc=pub/'candidate.json';doc.write_bytes(r.g.encode(m))
        self.trust=self.root/'operator'
        subprocess.run(['python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(doc),
                        '--operator',str(self.trust)],check=True,capture_output=True)
        self.doc_hash=r.g.sha(doc.read_bytes());self.key_hash=r.g.sha((self.trust/'public.pem').read_bytes())
        # Remove publisher contents: the restore entry must not depend on them.
        doc.unlink();pub.rmdir()
    def tearDown(self):
        self.tmp.cleanup()
    def factory(self,path):
        self.constructed+=1
        class Reader: pass
        a=Reader();a.get=self.get;return a
    def restore(self,target,inventory,workspace):
        self.restores+=1
        self.assertEqual((target/'database.sql').read_bytes(),b'sql')
        self.assertEqual(inventory,{'one.txt':r.g.sha(b'one')})
        return dict(passed=True,resources_removed=True)
    def recover(self,**kwargs):
        args=dict(trust=self.trust,destination=self.root/'restore',set_id='AWS-'+'1'*16,
                  config_hash='b'*64,document_hash=self.doc_hash,key_hash=self.key_hash,
                  adapter_factory=self.factory,restore=self.restore)
        args.update(kwargs);return r.recover(**args)
    def test_success_without_publisher(self):
        result=self.recover()
        self.assertTrue(result['passed']);self.assertEqual(self.gets,2);self.assertEqual(self.restores,1)
    def test_invalid_signature_before_network(self):
        (self.trust/'approved.sig').write_bytes(b'bad')
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.constructed,0);self.assertEqual(self.restores,0)
    def test_operator_hash_before_network(self):
        with self.assertRaises(ValueError):self.recover(key_hash='c'*64)
        self.assertEqual(self.constructed,0)
    def test_config_before_network(self):
        with self.assertRaises(ValueError):self.recover(config_hash='c'*64)
        self.assertEqual(self.constructed,0)
    def test_document_pin_before_network(self):
        with self.assertRaises(ValueError):self.recover(document_hash='c'*64)
        self.assertEqual(self.constructed,0)
    def test_wrong_version_no_restore(self):
        self.mode='version'
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.restores,0)
    def test_wrong_bytes_no_restore(self):
        self.mode='bytes'
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.restores,0)
    def test_second_asset_invalid_never_restores_first(self):
        self.mode='second_bytes'
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.gets,2);self.assertEqual(self.restores,0)
    def test_existing_destination_refuses(self):
        target=self.root/'restore';target.mkdir()
        with self.assertRaises(FileExistsError):self.recover()
        self.assertEqual(self.constructed,0)
    def test_restore_failure_retained_not_passed(self):
        def fail(*args):raise RuntimeError('fixture restore failed')
        with self.assertRaises(RuntimeError):self.recover(restore=fail)
        result=json.loads((self.root/'restore/result.json').read_bytes())
        self.assertFalse(result['passed']);self.assertTrue(result['assets_verified'])
        self.assertEqual(result['error_type'],'RuntimeError')


if __name__=='__main__':unittest.main()
