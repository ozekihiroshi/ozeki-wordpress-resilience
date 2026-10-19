import datetime as dt,importlib.util,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('adapter',ROOT/'tools/queue-s3-adapter.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Response(io.BytesIO):
    def __init__(self,body=b'',**headers):super().__init__(body);self.headers=headers
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.adapter=a.S3Adapter(Path(self.tmp.name)/'receipts')
    def test_wrong_bucket_rejected_before_network(self):
        with self.assertRaises(ValueError):self.adapter.put('wrong','key',b'data')
        self.assertEqual(self.adapter.operations,[])
    def test_fixed_version_get_required(self):
        with self.assertRaises(ValueError):self.adapter.get({'bucket':a.BUCKET,'region':a.REGION,'version_id':'null'})
    def test_acknowledged_put_receipt(self):
        with patch.object(self.adapter,'request',return_value=Response(**{'x-amz-version-id':'fixed','x-amz-server-side-encryption':'AES256'})):
            self.assertEqual(self.adapter.put(a.BUCKET,'key',b'data'),'fixed')
        self.assertEqual(json.loads((self.adapter.work/'operations.json').read_text())[0]['version_id'],'fixed')
    def test_uncertain_put_not_blindly_retried(self):
        with patch.object(self.adapter,'request',side_effect=RuntimeError('timeout')):
            with self.assertRaises(RuntimeError):self.adapter.put(a.BUCKET,'key',b'data')
        with patch.object(self.adapter,'request') as request:
            with self.assertRaises(ValueError):self.adapter.put(a.BUCKET,'key',b'data')
            request.assert_not_called()
    def test_put_without_version_fails(self):
        with patch.object(self.adapter,'request',return_value=Response(**{'x-amz-server-side-encryption':'AES256'})):
            with self.assertRaises(ValueError):self.adapter.put(a.BUCKET,'key',b'data')
    def test_no_redirect(self):
        with self.assertRaises(RuntimeError):a.NoRedirect().redirect_request()
    def test_remote_authorizer_cannot_redirect_upload(self):
        with patch.object(a,'authorize',return_value={'role':'my-ssm-role','url':'https://example.invalid/steal','headers':{}}),patch.object(self.adapter.client,'open') as opened:
            with self.assertRaises(ValueError):self.adapter.request('writer','PUT','key',body=b'data')
            opened.assert_not_called()
    def test_authorizer_is_narrowly_scoped(self):
        source=(ROOT/'tools/lab-s3-request.py').read_text()
        self.assertIn("bucket='ceri-link-resilience-lock-lab-121426368082'",source)
        self.assertIn("'x-amz-object-lock-mode':'GOVERNANCE'",source)
        self.assertIn("'content-md5'",source)
        self.assertIn("if q['method']=='DELETE':assert q['key'].endswith('/permission-probe.txt')",source)
        self.assertIn("AWS_SHARED_CREDENTIALS_FILE='/dev/null'",source)
    def test_small_clock_difference_waits_before_observation(self):
        start=dt.datetime.now(dt.timezone.utc);current=[start];waits=[]
        def sleep(n):waits.append(n);current[0]+=dt.timedelta(seconds=n)
        a.wait_for_observation_time(start+dt.timedelta(seconds=1),lambda:current[0],sleep)
        self.assertGreaterEqual(waits[0],1)
    def test_large_clock_difference_rejected(self):
        start=dt.datetime.now(dt.timezone.utc)
        with self.assertRaises(ValueError):a.wait_for_observation_time(start+dt.timedelta(seconds=6),lambda:start,lambda n:None)
    def test_nonadvancing_clock_rejected(self):
        start=dt.datetime.now(dt.timezone.utc)
        with self.assertRaises(ValueError):a.wait_for_observation_time(start+dt.timedelta(seconds=1),lambda:start,lambda n:None)
if __name__=='__main__':unittest.main()
