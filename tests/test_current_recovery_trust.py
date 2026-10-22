"""Run in a dedicated privileged lab; real root-owned registry, synthetic S3 and restore."""
import copy, datetime as dt, json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import test_first_site_daily_restore as fixture

@unittest.skipUnless(hasattr(os,'geteuid') and os.geteuid()==0,'requires dedicated root-owned registry lab')
class CurrentTrust(fixture.Recovery):
    def setUp(self):
        # Parent fixture has real signatures and mock transport; do not bypass authority here.
        super().setUp()
        self.registry_tmp=tempfile.TemporaryDirectory(prefix='owr-current-trust-',dir='/run')
        self.addCleanup(self.registry_tmp.cleanup)
        self.path=Path(self.registry_tmp.name)/'current.json'
        self.authority=fixture.r.current_trust
        self.path_patch=patch.object(self.authority,'AUTHORITY',self.path);self.path_patch.start();self.addCleanup(self.path_patch.stop)
        now=dt.datetime.now(dt.timezone.utc)
        self.record={'format':'owr-current-recovery-trust-v1','revision':2,'issued_at':(now-dt.timedelta(seconds=1)).isoformat(),'expires_at':(now+dt.timedelta(hours=1)).isoformat(),'revoked_key_sha256':[], 'sets':[{'site_id':fixture.r.d.SITE,'set_id':'AWS-'+'1'*16,'status':'active','minimum_sequence':1,'public_key_sha256':self.key_hash,'approved_document_sha256':self.doc_hash}]}
        self.write()
    def write(self):
        self.path.write_text(json.dumps(self.record));self.path.chmod(0o644)
    def blocked(self):
        with self.assertRaises((ValueError,OSError)):self.recover()
        self.assertEqual((self.constructed,self.gets,self.restores),(0,0,0))
        self.assertFalse((self.root/'restore').exists())
    def test_writable_parent(self):self.path.parent.chmod(0o777);self.blocked()
    def test_excessive_validity(self):
        self.record['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=2)).isoformat();self.write();self.blocked()
    def test_missing_authority(self):self.path.unlink();self.blocked()
    def test_old_bundle_current_key_changed(self):self.record['sets'][0]['public_key_sha256']='a'*64;self.write();self.blocked()
    def test_old_bundle_current_document_changed(self):self.record['sets'][0]['approved_document_sha256']='a'*64;self.write();self.blocked()
    def test_old_bundle_generation_changed(self):self.record['sets'][0]['minimum_sequence']=2;self.write();self.blocked()
    def test_revoked_set(self):self.record['sets'][0]['status']='revoked';self.write();self.blocked()
    def test_revoked_key(self):self.record['revoked_key_sha256']=[self.key_hash];self.write();self.blocked()
    def test_expired_authority(self):self.record['expires_at']=self.record['issued_at'];self.write();self.blocked()
    def test_future_authority(self):self.record['issued_at']=self.record['expires_at'];self.write();self.blocked()
    def test_unknown_set(self):self.record['sets']=[];self.write();self.blocked()
    def test_duplicate_set(self):self.record['sets']*=2;self.write();self.blocked()
    def test_writable_authority(self):self.path.chmod(0o666);self.blocked()
    def test_unprivileged_authority_owner(self):os.chown(self.path,65534,65534);self.blocked()
    def test_symlink_authority(self):
        target=self.path.with_suffix('.original');self.path.rename(target);self.path.symlink_to(target);self.blocked()
    def test_partial_authority(self):self.path.write_text('{');self.blocked()
    def test_authority_changed_during_reads(self):
        original=self.get
        def changed(loc):
            value=original(loc);self.record['sets'][0]['status']='revoked';self.write();return value
        self.get=changed
        with self.assertRaises(ValueError):self.recover()
        self.assertEqual(self.restores,0)
        result=json.loads((self.root/'restore/result.json').read_text());self.assertFalse(result['restore_started'])
    def test_reader_cannot_overwrite_authority(self):
        self.path.parent.chmod(0o755)
        read=subprocess.run(['runuser','-u','nobody','--','cat',str(self.path)],capture_output=True)
        self.assertEqual(read.returncode,0)
        self.assertEqual(json.loads(read.stdout),self.record)
        p=subprocess.run(['runuser','-u','nobody','--','python3','-c','from pathlib import Path; import sys; Path(sys.argv[1]).write_text("{}")',str(self.path)],capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads(self.path.read_text()),self.record)

if __name__=='__main__':
    if os.geteuid()!=0:raise SystemExit('Dedicated root-owned registry lab requires root; no production paths are used')
    unittest.main()
