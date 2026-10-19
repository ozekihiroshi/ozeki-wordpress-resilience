import importlib.util
from datetime import datetime,timedelta,timezone
import json
import multiprocessing
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('heartbeat',ROOT/'tools/heartbeat-ssh.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


def receive_parallel(directory,body):h.receive(body,Path(directory),'isolated-queue-lab')


class HeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        self.now=datetime.now(timezone.utc)
        self.value=dict(format='owr-monitor-heartbeat-v1',monitor_id='isolated-queue-lab',
                        completed_at=self.now.isoformat(),undelivered=0,open_incidents=1)
    def raw(self):return json.dumps(self.value).encode()
    def receive(self):return h.receive(self.raw(),self.path,'isolated-queue-lab',self.now)
    def test_preserved_time_and_readonly_group_mode(self):
        self.assertEqual(self.receive()['state'],'accepted')
        path=self.path/'heartbeat.json'
        self.assertEqual(json.loads(path.read_text())['completed_at'],self.value['completed_at'])
        self.assertEqual(path.stat().st_mode & 0o777,0o640)
    def test_idempotent_retry_does_not_touch_timestamp(self):
        first=self.receive();before=(self.path/'heartbeat.json').stat().st_mtime_ns
        second=self.receive()
        self.assertEqual(second['state'],'duplicate');self.assertEqual(first['sha256'],second['sha256'])
        self.assertEqual(before,(self.path/'heartbeat.json').stat().st_mtime_ns)
    def test_older_and_same_time_conflict_preserve_previous(self):
        self.receive();before=(self.path/'heartbeat.json').read_bytes()
        self.value['completed_at']=(self.now-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):self.receive()
        self.value['completed_at']=self.now.isoformat();self.value['undelivered']=1
        with self.assertRaises(ValueError):self.receive()
        self.assertEqual(before,(self.path/'heartbeat.json').read_bytes())
    def test_newer_updates(self):
        self.receive();self.value['completed_at']=(self.now+timedelta(seconds=1)).isoformat()
        self.assertEqual(self.receive()['state'],'accepted')
    def test_wrong_id_extra_fields_invalid_counters(self):
        for key,value in [('monitor_id','other'),('path','/etc/passwd'),('undelivered',True),('open_incidents',-1)]:
            bad=dict(self.value);bad[key]=value
            with self.assertRaises(ValueError):h.parse(json.dumps(bad).encode(),'isolated-queue-lab',self.now)
    def test_size_and_duplicate_json_keys(self):
        with self.assertRaises(ValueError):h.parse(b' '*4097,'isolated-queue-lab',self.now)
        with self.assertRaises(ValueError):h.parse(b'{"format":1,"format":2}','isolated-queue-lab',self.now)
    def test_future_and_naive_time(self):
        for stamp in [(self.now+timedelta(seconds=6)).isoformat(),self.now.replace(tzinfo=None).isoformat()]:
            self.value['completed_at']=stamp
            with self.assertRaises(ValueError):self.receive()
    def test_concurrent_identical_receipts(self):
        context=multiprocessing.get_context('fork')
        workers=[context.Process(target=receive_parallel,args=(str(self.path),self.raw())) for _ in range(4)]
        for p in workers:p.start()
        for p in workers:p.join(10);self.assertEqual(p.exitcode,0)
        self.assertEqual(json.loads((self.path/'heartbeat.json').read_text()),self.value)
    def config(self):return dict(host='dm.example.invalid',user='owr-heartbeat',port=10007,
                                identity_file=str(self.path/'key'),known_hosts=str(self.path/'known'),monitor_id='isolated-queue-lab')
    def test_sender_pins_host_and_private_identity(self):
        command=h.command(self.config())
        self.assertIn('StrictHostKeyChecking=yes',command);self.assertIn('IdentityAgent=none',command)
        self.assertEqual(command[-1],'heartbeat')
    def test_sender_rejects_wrong_ack_and_connection_failure(self):
        for code,body in [(255,b''),(0,b'{}')]:
            with self.assertRaises((ValueError,RuntimeError)):
                h.send(self.config(),self.raw(),runner=lambda *a,**kw:SimpleNamespace(returncode=code,stdout=body))
    def test_sender_accepts_only_matching_ack(self):
        _,_,body=h.parse(self.raw(),'isolated-queue-lab')
        ack=json.dumps(dict(format='owr-heartbeat-ack-v1',state='accepted',sha256=h.hashlib.sha256(body).hexdigest())).encode()
        self.assertEqual(h.send(self.config(),self.raw(),runner=lambda *a,**kw:SimpleNamespace(returncode=0,stdout=ack))['state'],'accepted')

if __name__=='__main__':unittest.main()
