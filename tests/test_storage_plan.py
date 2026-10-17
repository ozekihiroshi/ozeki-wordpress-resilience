import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("storage",Path(__file__).resolve().parents[1]/"tools/plan-m1-storage.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class StoragePlanTests(unittest.TestCase):
    def test_scoped_resources(self):
        p=m.plan("example-only","ap-northeast-1","m1/set/")
        for role in ("writer_policy","recovery_reader_policy"):
            for statement in p[role]["Statement"]:
                self.assertEqual(statement["Resource"],"arn:aws:s3:::example-only/m1/set/*")
    def test_reader_version_only(self):
        p=m.plan("example-only","ap-northeast-1","m1/set/")
        allow=p["recovery_reader_policy"]["Statement"][0]
        self.assertEqual(allow["Action"],["s3:GetObjectVersion"])
    def test_no_root_or_wildcard_prefix(self):
        for prefix in ("","/","*","m1/*/","../","m1/../","m1"):
            with self.assertRaises(ValueError):
                m.plan("example-only","ap-northeast-1",prefix)
    def test_writer_no_delete(self):
        p=m.plan("example-only","ap-northeast-1","m1/set/")
        self.assertEqual(p["writer_policy"]["Statement"][0]["Action"],["s3:PutObject"])
        self.assertIn("s3:DeleteObjectVersion",p["writer_policy"]["Statement"][1]["Action"])
    def test_invalid_bucket(self):
        with self.assertRaises(ValueError):
            m.plan("*","ap-northeast-1","m1/set/")