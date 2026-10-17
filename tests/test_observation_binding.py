import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("binding",ROOT/"tools/bind-m1-observations.py")
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class BindingTests(unittest.TestCase):
    def setUp(self):
        self.base=b.m.read(ROOT/"examples/m1/RS-M1-P2-001/ram.json")[0]
        self.capture={"site_id":self.base["site_id"],"result":"captured_locally",
            "evidence_id":"SYNTHETIC","assets":[{"role":"database","sha256":"a"*64,"size_bytes":3}]}
        self.obs={"schema_version":1,"kind":"owr-versioned-download-observation",
            "observation":"download_integrity_checked","asset_role":"database",
            "sha256":"a"*64,"size_bytes":3,
            "locator":{"kind":"s3","bucket":"owr-example-bucket","region":"ap-northeast-1",
                       "key":"wordpress-test/SYNTHETIC/database","version_id":"v-1"}}
    def bind(self):
        return b.bind(self.base,self.capture,[self.obs],"RS-NEW")
    def test_binding_retains_unverified(self):
        ram,report=self.bind()
        self.assertEqual(ram["assets"][0]["locator"]["version_id"],"v-1")
        self.assertFalse(report["recovery_ready"])
        self.assertEqual(report["role_separation"],"unverified")
        self.assertEqual(len(report["pending_roles"]),7)
    def test_hash_mismatch(self):
        self.obs["sha256"]="b"*64
        with self.assertRaises(ValueError):self.bind()
    def test_site_mismatch(self):
        self.capture["site_id"]="other"
        with self.assertRaises(ValueError):self.bind()
    def test_wrong_bucket(self):
        self.obs["locator"]["bucket"]="other"
        with self.assertRaises(ValueError):self.bind()
    def test_put_receipt_not_download(self):
        self.obs["kind"]="owr-versioned-upload-receipt"
        with self.assertRaises(ValueError):self.bind()
    def test_duplicate_role(self):
        with self.assertRaises(ValueError):
            b.bind(self.base,self.capture,[self.obs,self.obs],"RS-NEW")
    def test_same_set_refused(self):
        with self.assertRaises(ValueError):
            b.bind(self.base,self.capture,[self.obs],self.base["set_id"])
    def test_null_version_refused(self):
        self.obs["locator"]["version_id"]="null"
        from jsonschema.exceptions import ValidationError
        with self.assertRaises(ValidationError):self.bind()