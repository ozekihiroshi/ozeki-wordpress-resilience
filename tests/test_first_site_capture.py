import copy, importlib.util, io, json, os, tarfile, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('first_site',ROOT/'tools/first-site-capture.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
CONFIG=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
class Backend:
    def __init__(self):
        self.released=False;self.token=None;self.fail=None;self.changed=False
        b=io.BytesIO()
        with tarfile.open(fileobj=b,mode='w:gz') as t:
            m=tarfile.TarInfo('wp-content/uploads/example.png');m.size=3;t.addfile(m,io.BytesIO(b'png'))
        self.archive=b.getvalue()
    def preflight(self,c):pass
    def fence(self,token,wait,lease):self.token=token
    def held(self,token):return self.fail!='lost' and token==self.token
    def release(self,token):self.released=True;return self.fail!='release'
    def inventory(self,limit):return {'wp-content/uploads/example.png':a.hashlib.sha256(b'png').hexdigest()}
    def schema(self):return [['wp_posts','MyISAM' if self.fail=='schema' else 'InnoDB']]
    def references(self):return ['absent.png'] if self.fail=='reference' else ['example.png']
    def stream(self,asset,deadline):
        yield b'SELECT 1;' if asset=='database' else self.archive
        if self.fail=='stream':raise a.Rejected('stream_process_failed')
class Tests(unittest.TestCase):
    def run_capture(self,b,c=None):
        with tempfile.TemporaryDirectory() as d:
            c=c or copy.deepcopy(CONFIG);return a.capture(c,a.digest(c),b,Path(d))[1]
    def test_backend_rejects_other_database_before_docker(self):
        spec=importlib.util.spec_from_file_location('first_backend',ROOT/'tools/first-site-docker-lab.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        c=copy.deepcopy(CONFIG);c['database']['name']='other'
        b=m.DockerBackend(a,c,'owr-first-site-db','owr-first-site-web',None,None,None,None,None,lambda *args:self.fail('Docker must not run'))
        with self.assertRaisesRegex(a.Rejected,'runtime_scope_mismatch'):b.preflight(c)
    def test_wall_clock_jump_cannot_pass_after_suspend(self):
        from unittest.mock import patch
        jumped=[False];b=Backend();old=b.stream
        def stream(asset,deadline):
            jumped[0]=True
            yield from old(asset,deadline)
        b.stream=stream
        with patch.object(a.time,'time',side_effect=lambda:2000 if jumped[0] else 1000):
            v=self.run_capture(b)
        self.assertEqual(v['state'],'unverified');self.assertTrue(b.released)
    def test_slow_fence_probe_does_not_starve_stream(self):
        from unittest.mock import patch
        clock=[1000.0];calls=[];b=Backend();old=b.stream
        def held(token):
            calls.append(clock[0]);clock[0]+=.6
            return token==b.token
        def stream(asset,deadline):
            for chunk in old(asset,deadline):
                for i in range(0,len(chunk),8):
                    clock[0]+=.01
                    yield chunk[i:i+8]
        b.held=held;b.stream=stream
        with patch.object(a.time,'monotonic',side_effect=lambda:clock[0]),patch.object(a.time,'time',side_effect=lambda:clock[0]):
            v=self.run_capture(b)
        self.assertEqual(v['state'],'consistent')
        self.assertLessEqual(len(calls),6,'slow probes must leave a collection interval after completing')
    def test_timeout_records_operation_without_command_secrets(self):
        import subprocess
        for operation in ['held','stream.files.read']:
            with self.subTest(operation=operation):
                b=Backend();old=b.stream
                def fail(*args):raise subprocess.TimeoutExpired(['secret-password'],60,output=b'secret-output',stderr=b'secret-stderr')
                if operation=='held':b.held=fail
                else:
                    def stream(asset,deadline):
                        if asset=='files':fail()
                        yield from old(asset,deadline)
                    b.stream=stream
                v=self.run_capture(b)
                self.assertEqual(v['state'],'capture_failed');self.assertTrue(v['release_confirmed'])
                self.assertEqual(v['timeout']['operation'],operation);self.assertEqual(v['timeout']['limit_seconds'],60)
                self.assertNotIn('secret',json.dumps(v));self.assertGreaterEqual(v['timeout']['elapsed_seconds'],0)
    def test_external_spool_space_reserved_before_fence(self):
        from unittest.mock import patch
        b=Backend();b.staging_copies=2
        free=CONFIG['operations']['max_bytes']+CONFIG['operations']['reserve_bytes']
        with patch.object(a.shutil,'disk_usage',return_value=type('Usage',(),{'free':free})()):v=self.run_capture(b)
        self.assertEqual(v['reason'],'insufficient_space');self.assertIsNone(b.token)
    def test_valid(self):self.assertTrue(a.validate(CONFIG)['valid'])
    def test_rejected_configs(self):
        mutations=[lambda c:c.update(password='secret'),lambda c:c['writers'].pop('cli'),lambda c:c['queue'].update(state='present'),lambda c:c.update(dependencies=['redis']),lambda c:c['files'].update(exclusions=['cache']),lambda c:c['wordpress'].update(multisite=True),lambda c:c['database'].update(engines=['MyISAM']),lambda c:c['operations'].update(max_stop_seconds=True),lambda c:c['operations'].update(alternate=''),lambda c:c['storage'].update(reader_ref='lab-writer'),lambda c:c['database'].update(name='lab;DROP'),lambda c:c['operations'].update(max_bytes=-1)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                c=copy.deepcopy(CONFIG);mutation(c)
                with self.assertRaises(a.Rejected):a.validate(c)
    def test_success_two_assets(self):
        b=Backend();v=self.run_capture(b);self.assertEqual(v['state'],'consistent');self.assertTrue(b.released);self.assertEqual(set(v['assets']),{'database','files'});self.assertFalse(v['signed'])
    def test_failures_release(self):
        for fault,state in [('lost','unverified'),('schema','unverified'),('reference','inconsistent'),('stream','capture_failed'),('release','capture_failed')]:
            with self.subTest(fault=fault):
                b=Backend();b.fail=fault;v=self.run_capture(b);self.assertEqual(v['state'],state);self.assertTrue(b.released);self.assertFalse(v['eligible_for_consistency_acceptance'])
    def test_size_limit(self):
        c=copy.deepcopy(CONFIG);c['operations']['max_bytes']=2;b=Backend();v=self.run_capture(b,c);self.assertEqual(v['reason'],'capture_size_limit');self.assertTrue(b.released)
    def test_low_space_preflight(self):
        c=copy.deepcopy(CONFIG);c['operations']['reserve_bytes']=2**63;b=Backend();v=self.run_capture(b,c);self.assertEqual(v['reason'],'insufficient_space');self.assertIsNone(b.token)
    def test_pin_before_touch(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(a.Rejected):a.capture(CONFIG,'0'*64,Backend(),Path(d))
            self.assertEqual(list(Path(d).iterdir()),[])
    def test_release_failure_blocks_retry(self):
        with tempfile.TemporaryDirectory() as d:
            b=Backend();b.fail='release';a.capture(CONFIG,a.digest(CONFIG),b,Path(d))
            with self.assertRaisesRegex(a.Rejected,'reconciliation'):a.capture(CONFIG,a.digest(CONFIG),Backend(),Path(d))
    def test_lock_and_stale_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);f=(root/(CONFIG['site_id']+'.lock')).open('w');a.fcntl.flock(f,a.fcntl.LOCK_EX)
            with self.assertRaisesRegex(a.Rejected,'site_busy'):a.capture(CONFIG,a.digest(CONFIG),Backend(),root)
            f.close();(root/(CONFIG['site_id']+'.active.json')).write_text('{}')
            with self.assertRaisesRegex(a.Rejected,'reconciliation'):a.capture(CONFIG,a.digest(CONFIG),Backend(),root)
    def test_tar_traversal_and_link(self):
        for name,kind in [('../outside',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'bad.tgz'
                with tarfile.open(p,'w:gz') as t:
                    m=tarfile.TarInfo(name);m.type=kind;t.addfile(m)
                with self.assertRaises(a.Rejected):a.archive_inventory(p,1024)
    def test_archive_mismatch(self):
        b=Backend();b.inventory=lambda limit:{'other':a.hashlib.sha256(b'x').hexdigest()};self.assertEqual(self.run_capture(b)['state'],'inconsistent')
    def test_private_root(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d).chmod(0o755)
            with self.assertRaisesRegex(a.Rejected,'private'):a.capture(CONFIG,a.digest(CONFIG),Backend(),Path(d))
if __name__=='__main__':unittest.main()
