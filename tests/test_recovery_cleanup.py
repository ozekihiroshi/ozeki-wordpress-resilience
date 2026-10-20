import copy
import importlib.util
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
fixture=load('fixture',ROOT/'tests/test_first_site_recovery_worker.py')
c=load('cleanup',ROOT/'tools/recovery-cleanup.py')
w=fixture.w

class Docker:
    def __init__(self,token,names):
        self.objects=[dict(Id=str(i),Name='/'+n,Config={'Labels':{'owr.recovery-token':token,'owr.daily-restore':'generated'}},
                           HostConfig={'Binds':None,'PortBindings':{},'NetworkMode':'none' if i==0 else 'container:0'},
                           Mounts=[{'Type':'volume','Name':str(i)*64}]) for i,n in enumerate(names)]
        self.removed=[];self.fail=False
    def inventory(self):return copy.deepcopy(self.objects)
    def remove(self,ident):
        if self.fail and self.removed:raise OSError('injected remove failure')
        self.objects=[o for o in self.objects if o['Id']!=ident];self.removed.append(ident)
    def volume_exists(self,name):return any(name==m['Name'] for o in self.objects for m in o['Mounts'])

class Cleanup(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Worker();self.f.setUp();self.worker=self.f.worker
        self.names=['owr-daily-restore-123456789abc-db','owr-daily-restore-123456789abc-web']
        self.token='a'*32
        def stop(**kw):
            p=kw['destination'];p.mkdir(parents=True)
            w.d.io.write_json(p/'ownership.json',dict(token=self.token,containers=self.names))
            w.d.io.write_json(p/'result.json',dict(passed=False,restore_started=True))
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.f.run_worker(recover=stop)
        self.worker.retry_registration('trial')
        self.docker=Docker(self.token,self.names)
    def tearDown(self):self.f.tearDown()
    def review(self):return c.review(self.worker,'trial',w.d,self.docker)
    def clean(self,review=None):return c.clean(self.worker,'trial',(review or self.review())['plan_sha256'],w.d,self.docker)
    def test_release_preserves_result_and_allows_new_id(self):
        p=self.worker.root/'recovery-attempts/trial/result.json';before=p.read_bytes()
        self.clean();self.assertEqual(self.docker.removed,['1','0'])
        self.assertEqual(p.read_bytes(),before)
        self.assertEqual(self.worker.row('trial')['outcome'],'unknown')
        self.assertEqual(self.f.f.c.status(self.f.f.now)['runs'][0]['phase'],'recovery_reviewed_closed')
        self.assertEqual(self.f.run_worker()['state'],'reviewed_closed')
        row=self.worker.run('new',self.f.day,self.f.trust,recover=self.f.recover,registrar=self.f.registrar)
        self.assertEqual(row['registration'],'recorded')
    def test_changed_result_refused(self):
        review=self.review()
        (self.worker.root/'recovery-attempts/trial/result.json').write_text('{}')
        with self.assertRaises(ValueError):self.clean(review)
        self.assertFalse(self.docker.removed)
    def test_owner_mismatch(self):
        self.docker.objects[0]['Config']['Labels']['owr.recovery-token']='b'*32
        with self.assertRaises(ValueError):self.review()
    def test_shared_volume(self):
        extra=copy.deepcopy(self.docker.objects[0]);extra.update(Id='other',Name='/unrelated')
        extra['Config']['Labels']={}
        self.docker.objects.append(extra)
        with self.assertRaises(ValueError):self.review()
    def test_replacement_refused(self):
        review=self.review();self.docker.objects[1]['Id']='replacement'
        with self.assertRaises(ValueError):self.clean(review)
    def test_partial_cleanup_requires_new_review(self):
        review=self.review();self.docker.fail=True
        with self.assertRaises(OSError):self.clean(review)
        self.assertEqual(self.worker.row('trial')['state'],'interrupted')
        with self.assertRaises(ValueError):self.clean(review)
        self.docker.fail=False;self.clean()
        self.assertEqual(self.docker.removed,['1','0'])
    def test_pending_registration_not_abandoned(self):
        self.worker.update('trial',registration='pending')
        with self.assertRaises(ValueError):self.clean()
        self.assertFalse(self.docker.removed)
    def test_final_failed_report_requires_registration(self):
        w.d.io.write_json(self.worker.root/'recovery-attempts/trial/result.json',
                         dict(passed=False,error_type='RestoreFailed'))
        with self.assertRaises(ValueError):self.clean()
        self.assertFalse(self.docker.removed)
    def test_orphan_volume_blocks_release(self):
        self.docker.volume_exists=lambda name:True
        with self.assertRaises(ValueError):self.clean()
        self.assertEqual(self.worker.row('trial')['state'],'interrupted')
    def test_active_worker_blocks(self):
        with self.worker.lock():
            with self.assertRaises(BlockingIOError):self.review()
    def test_daemon_failure_not_absence(self):
        def failed():raise OSError('daemon unavailable')
        self.docker.inventory=failed
        with self.assertRaises(OSError):self.clean()
        self.assertEqual(self.worker.row('trial')['state'],'interrupted')

if __name__=='__main__':unittest.main()
