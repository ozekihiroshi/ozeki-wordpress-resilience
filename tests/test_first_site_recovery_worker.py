import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
w=load('worker',ROOT/'tools/first-site-daily-recovery-worker.py')
fixture=load('daily_fixture',ROOT/'tests/test_first_site_daily.py')


class Worker(unittest.TestCase):
    def setUp(self):
        self.f=fixture.Daily();self.f.setUp()
        r=self.f.tick();self.day=r['day'];work=self.f.c.root/r['id']
        self.trust=self.f.root/'trust'
        subprocess.run(['python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',
                        str(work/'candidate.json'),'--operator',str(self.trust)],check=True,capture_output=True)
        self.f.c.approve(self.day,self.trust,w.d.gate.sha((self.trust/'approved.json').read_bytes()),
                        w.d.gate.sha((self.trust/'public.pem').read_bytes()),self.f.adapter)
        self.worker=w.Worker(self.f.c.root);self.executions=0;self.deliveries=0
    def tearDown(self):self.f.tearDown()
    def recover(self,**kw):
        self.executions+=1;p=kw['destination'];p.mkdir(parents=True)
        report=dict(passed=True,completed_at=w.d.gate.now().isoformat(),set_id=kw['set_id'])
        w.d.io.write_json(p/'result.json',report);return report
    def registrar(self,*args):
        self.deliveries+=1
    def run_worker(self,**kw):
        return self.worker.run('trial',self.day,self.trust,
                               recover=kw.get('recover',self.recover),
                               registrar=kw.get('registrar',self.registrar))
    def test_current_trust_denial_is_not_an_interrupted_attempt(self):
        original=w.load
        class Denied:
            def current(self,*args):raise ValueError('revoked')
        def loader(name,path):
            return Denied() if path=='current-recovery-trust.py' else original(name,path)
        with patch.object(w,'load',side_effect=loader),self.assertRaises(ValueError):
            self.worker.run('denied',self.day,self.trust)
        self.assertIsNone(self.worker.row('denied'))
        self.assertFalse((self.worker.root/'recovery-attempts'/'denied').exists())

    def test_success_and_duplicate_no_rerestore(self):
        self.assertEqual(self.run_worker()['registration'],'recorded')
        self.assertEqual(self.run_worker()['registration'],'recorded')
        self.assertEqual(self.executions,1);self.assertEqual(self.deliveries,1)
    def test_registration_failure_retries_only_delivery(self):
        def fail(*args):raise OSError('registration unavailable')
        row=self.run_worker(registrar=fail)
        self.assertEqual(row['outcome'],'succeeded');self.assertEqual(row['registration'],'pending')
        self.assertEqual(self.f.c.status(self.f.now)['runs'][0]['phase'],'registration_pending')
        row=self.worker.retry_registration('trial',self.registrar)
        self.assertEqual(row['registration'],'recorded');self.assertEqual(self.executions,1)
    def test_fail_report_is_delivered(self):
        def failed(**kw):
            self.executions+=1;p=kw['destination'];p.mkdir(parents=True)
            w.d.io.write_json(p/'result.json',dict(passed=False,error_type='RestoreFailed'))
            raise RuntimeError('restore failed')
        row=self.run_worker(recover=failed)
        self.assertEqual(row['outcome'],'failed');self.assertEqual(row['registration'],'recorded')
        self.assertEqual(self.f.c.status(self.f.now)['runs'][0]['phase'],'restore_failed')
        self.assertEqual(self.run_worker()['outcome'],'failed');self.assertEqual(self.executions,1)
    def test_interrupted_partial_not_success_or_retried(self):
        def interrupt(**kw):
            self.executions+=1;p=kw['destination'];p.mkdir(parents=True)
            w.d.io.write_json(p/'result.json',dict(passed=False,restore_started=True))
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.run_worker(recover=interrupt)
        self.assertEqual(self.f.c.status(self.f.now)['runs'][0]['phase'],'recovery_running')
        row=self.worker.retry_registration('trial',self.registrar)
        self.assertEqual(row['state'],'interrupted');self.assertEqual(self.deliveries,0)
        self.assertEqual(self.run_worker()['state'],'interrupted');self.assertEqual(self.executions,1)
        self.assertEqual(self.f.c.status(self.f.now)['runs'][0]['phase'],'recovery_interrupted')
    def test_interrupted_after_final_report_reconciles(self):
        def interrupt(**kw):
            self.recover(**kw);raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.run_worker(recover=interrupt)
        row=self.worker.retry_registration('trial',self.registrar)
        self.assertEqual(row['outcome'],'succeeded');self.assertEqual(row['registration'],'recorded')
        self.assertEqual(self.executions,1)
    def test_lock_blocks_parallel(self):
        with self.worker.lock():
            with self.assertRaises(BlockingIOError):self.run_worker()
        self.assertEqual(self.executions,0)
    def test_same_request_different_binding_refused(self):
        self.run_worker()
        with self.assertRaises(ValueError):self.worker.run('trial','2099-01-01',self.trust,recover=self.recover)
        self.assertEqual(self.executions,1)
    def test_undelivered_blocks_new_request(self):
        def fail(*args):raise OSError()
        self.run_worker(registrar=fail)
        with self.assertRaises(ValueError):
            self.worker.run('other',self.day,self.trust,recover=self.recover,registrar=self.registrar)
        self.assertEqual(self.executions,1)
    def test_mutated_report_does_not_change_pinned_delivery(self):
        def fail(*args):raise OSError()
        row=self.run_worker(registrar=fail)
        p=self.worker.root/'recovery-attempts/trial/result.json';p.write_text('{}')
        got=[]
        def verify(day,path,expected):
            got.append(expected)
            if w.d.gate.sha((path/'result.json').read_bytes())!=expected:raise ValueError()
        self.assertEqual(self.worker.retry_registration('trial',verify)['registration'],'pending')
        self.assertEqual(got,[row['report_hash']]);self.assertEqual(self.executions,1)


if __name__=='__main__':unittest.main()
