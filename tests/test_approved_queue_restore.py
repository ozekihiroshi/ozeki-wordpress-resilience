import importlib.util
import io
import json
from pathlib import Path
import tarfile
import unittest
from unittest.mock import Mock, patch
from datetime import timedelta
import test_daily_s3_publication as fixture

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('approved_restore_tests',ROOT/'tools/approved-queue-restore.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)

def archive(entries):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tar:
        for name,kind in entries:
            m=tarfile.TarInfo(name);m.type=kind
            if kind==tarfile.REGTYPE:m.size=4;tar.addfile(m,io.BytesIO(b'test'))
            else:m.linkname='target';tar.addfile(m)
    return out.getvalue()

class ApprovedRestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.DailyS3Tests.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):cls.keys.cleanup()
    def setUp(self):
        # Authority boundary is exercised separately; retain existing transport/signature contracts.
        for method in ("current", "unchanged"):
            stub=patch.object(r.current_trust,method,return_value={"revision":1})
            stub.start();self.addCleanup(stub.stop)
        fixture.DailyS3Tests.setUp(self)
        self.assets['files']=archive([('./index.php',tarfile.REGTYPE)])
        self.paired['assets']['files']=r.gate.sha(self.assets['files'])
        self.summary=fixture.DailyS3Tests.publish(self)
        self.trust=self.root/'independent-trust'
        fixture.DailyS3Tests.approve(self,self.summary,operator_dir=self.trust)
        self.args=dict(trust=self.trust,set_id=self.summary['set_id'],document_hash=self.summary['manifest_sha256'],key_hash=r.gate.sha(self.public.read_bytes()),receipts=self.root/'restore-receipts',mark=lambda name:None,adapter_factory=self.store.factory)
    sign=fixture.DailyS3Tests.sign
    def reject_without_network(self):
        factory=Mock(side_effect=AssertionError('network before gate'))
        with self.assertRaises((ValueError,FileNotFoundError)):
            r.fetch(**{**self.args,'adapter_factory':factory})
        factory.assert_not_called()
    def test_approved_set_retrieved_without_daily_state(self):
        (self.dir/'candidate.json').unlink()
        puts=self.store.puts;reads=self.store.reads
        assets,evidence,paired=r.fetch(**self.args)
        self.assertEqual(assets,self.assets);self.assertEqual(paired,self.paired)
        self.assertEqual(self.store.puts,puts);self.assertEqual(self.store.reads,reads+3)
        self.assertEqual(evidence['file_count'],1)
    def test_wrong_document_hash_blocks_network(self):
        self.args['document_hash']='0'*64;self.reject_without_network()
    def test_wrong_public_key_blocks_network(self):
        self.args['key_hash']='0'*64;self.reject_without_network()
    def test_wrong_set_blocks_network(self):
        self.args['set_id']='AWS-'+'0'*16;self.reject_without_network()
    def test_bad_signature_blocks_network(self):
        (self.trust/'recovery-set.sig').write_bytes(b'invalid');self.reject_without_network()
    def test_revoked_trust_blocks_network(self):
        p=self.trust/'pin.json';v=json.loads(p.read_text());v['status']='revoked';fixture.p.write_json(p,v);self.reject_without_network()
    def test_pending_approval_blocks_network(self):
        p=self.trust/'approval.json';v=json.loads(p.read_text());v['state']='awaiting_approval';fixture.p.write_json(p,v);self.reject_without_network()
    def test_expired_approval_blocks_network(self):
        with patch.object(r.gate,'now',return_value=r.gate.now()+timedelta(days=8)):
            self.reject_without_network()
    def test_missing_approval_blocks_network(self):
        (self.trust/'approval.json').unlink();self.reject_without_network()
    def test_retention_loss_prevents_return_of_restore_assets(self):
        self.store.bad_retention=True
        with self.assertRaises(ValueError):r.fetch(**self.args)
        self.assertFalse(json.loads((self.args['receipts']/'retrieval.json').read_text())['passed'])
    def test_trust_receipt_overlap_rejected(self):
        self.args['receipts']=self.trust/'reads';self.reject_without_network()
    def test_unsafe_archive_entries_rejected(self):
        for entries in [[('../escape',tarfile.REGTYPE)],[('/absolute',tarfile.REGTYPE)],[('link',tarfile.SYMTYPE)],[('hard',tarfile.LNKTYPE)],[('device',tarfile.CHRTYPE)],[('same',tarfile.REGTYPE),('./same',tarfile.REGTYPE)],[('file',tarfile.REGTYPE),('file/child',tarfile.REGTYPE)]]:
            with self.subTest(entries=entries),self.assertRaises(ValueError):r.archive_inventory(archive(entries))
        out=io.BytesIO()
        with tarfile.open(fileobj=out,mode='w:gz') as tar:
            entry=tarfile.TarInfo('directory');entry.type=tarfile.DIRTYPE;entry.size=4;tar.addfile(entry,io.BytesIO(b'data'))
            entry=tarfile.TarInfo('index.php');entry.size=4;tar.addfile(entry,io.BytesIO(b'test'))
        with self.assertRaises(ValueError):r.archive_inventory(out.getvalue())
    def test_truncated_archive_rejected(self):
        with self.assertRaises((tarfile.TarError,EOFError,OSError)):r.archive_inventory(b'not gzip')

if __name__=='__main__':unittest.main()
