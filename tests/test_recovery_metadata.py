import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from jsonschema.exceptions import ValidationError
ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("metadata",ROOT/"tools/recovery-metadata.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.ram_path=self.root/"input.json"
        m.generate(ROOT/"tests/fixtures/source-baseline.json",
                   ROOT/"examples/m1/asset-declarations.json",self.ram_path)
        self.ram,_=m.read(self.ram_path)
    def save(self, ram=None):
        self.ram_path.write_text(json.dumps(ram or self.ram))
    def reject(self, change):
        change(self.ram)
        with self.assertRaises((ValueError,ValidationError)):
            m.validate_ram(self.ram)
    def freeze(self):
        self.save()
        result=m.publish(self.ram_path,self.root/"sets")
        path=Path(result["directory"])
        return path,result["set_sha256"]
    def test_generate_allowlist(self):
        self.assertEqual(self.ram["environment"]["wordpress"],"7.0.2")
        self.assertNotIn("database_baseline",self.ram)
    def test_generate_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            m.generate(ROOT/"tests/fixtures/source-baseline.json",
                       ROOT/"examples/m1/asset-declarations.json",self.ram_path)
    def test_independent_inspect(self):
        path,sha=self.freeze()
        result=m.inspect(path/"ram.json",path/"recovery-set.json",sha)
        self.assertEqual(result["anchor"],"operator_supplied_digest_matched")
        self.assertFalse(result["recovery_ready"])
        self.assertEqual(result["authenticity"],"unverified")
        self.assertEqual(sum(x["status"]=="pending" for x in result["assets"]),7)
    def test_missing_anchor_stays_unverified(self):
        path,_=self.freeze()
        self.assertEqual(m.inspect(path/"ram.json",path/"recovery-set.json")["anchor"],
                         "not_supplied")
    def test_duplicate_set_refused(self):
        self.freeze()
        with self.assertRaises(FileExistsError):
            m.publish(self.ram_path,self.root/"sets")
    def test_ram_tampering(self):
        path,_=self.freeze()
        with (path/"ram.json").open("ab") as f: f.write(b" ")
        with self.assertRaises(ValueError):
            m.inspect(path/"ram.json",path/"recovery-set.json")
    def test_anchor_tampering(self):
        path,_=self.freeze()
        with self.assertRaises(ValueError):
            m.inspect(path/"ram.json",path/"recovery-set.json","0"*64)
    def test_set_site_mismatch(self):
        path,_=self.freeze()
        record,_=m.read(path/"recovery-set.json")
        record["site_id"]="different"
        (path/"recovery-set.json").write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            m.inspect(path/"ram.json",path/"recovery-set.json")
    def test_set_asset_omission(self):
        path,_=self.freeze()
        record,_=m.read(path/"recovery-set.json")
        record["asset_ids"].pop()
        with self.assertRaises((ValueError,ValidationError)):
            m.validate_set(record,self.ram,self.ram_path.read_bytes())
    def test_duplicate_json(self):
        self.ram_path.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError): m.read(self.ram_path)
    def test_oversize_metadata(self):
        self.ram_path.write_bytes(b" "*(m.LIMIT+1))
        with self.assertRaises(ValueError): m.read(self.ram_path)
    def test_missing_role(self):
        self.reject(lambda r:r["assets"].pop())
    def test_duplicate_asset(self):
        self.reject(lambda r:r["assets"].append(copy.deepcopy(r["assets"][0])))
    def test_unknown_dependency(self):
        self.reject(lambda r:r["assets"][0]["depends_on"].append("absent"))
    def test_cycle(self):
        def change(r):
            r["assets"][0]["depends_on"]=["uploads"]
            r["assets"][1]["depends_on"]=["database"]
        self.reject(change)
    def test_secret_field(self):
        self.reject(lambda r:r.update(aws_secret_access_key="synthetic-secret"))
    def test_embedded_credentials(self):
        self.reject(lambda r:r["assets"][0]["locator"].update(password="synthetic"))
    def test_invalid_date(self):
        self.reject(lambda r:r.update(created_at="yesterday"))
    def test_version_unsupported(self):
        self.reject(lambda r:r.update(schema_version=2))
    def test_authenticity_claim_rejected(self):
        self.reject(lambda r:r.update(authenticity="verified"))
    def test_traversal_set_id(self):
        self.reject(lambda r:r.update(set_id="../outside"))
    def test_local_traversal(self):
        self.reject(lambda r:r["assets"][6]["locator"].update(path="../outside"))
    def test_pending_cannot_claim_hash(self):
        self.reject(lambda r:r["assets"][0].update(sha256="0"*64))
    def s3_asset(self):
        self.ram["assets"][0].update(
            locator={"kind":"s3","bucket":"owr-example-only","region":"ap-northeast-1",
                     "key":"database/dump.sql.gz","version_id":"synthetic-version",
                     "credential_ref":"recovery-reader"},
            sha256="0"*64,size_bytes=123)
    def test_s3_declaration_not_observation(self):
        self.s3_asset()
        path,_=self.freeze()
        result=m.inspect(path/"ram.json",path/"recovery-set.json")
        self.assertEqual(result["assets"][0]["status"],"not_observed")
        self.assertFalse(result["recovery_ready"])
    def test_s3_missing_version(self):
        self.s3_asset()
        self.reject(lambda r:r["assets"][0]["locator"].pop("version_id"))
    def test_s3_null_version(self):
        self.s3_asset()
        self.reject(lambda r:r["assets"][0]["locator"].update(version_id="null"))
    def test_local_integrity(self):
        data=b"synthetic artifact"
        (self.root/"artifact").write_bytes(data)
        self.ram["assets"][6].update(locator={"kind":"local","path":"artifact"},
                                  sha256=m.digest(data),size_bytes=len(data))
        path,_=self.freeze()
        self.assertEqual(m.inspect(path/"ram.json",path/"recovery-set.json",
                                  asset_root=self.root)["assets"][6]["status"],
                         "local_integrity_checked")
        (self.root/"artifact").write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            m.inspect(path/"ram.json",path/"recovery-set.json",asset_root=self.root)
    def test_symlink_escape(self):
        outside=self.root/"outside"
        outside.write_bytes(b"data")
        inside=self.root/"inside"
        inside.mkdir()
        (inside/"artifact").symlink_to(outside)
        self.ram["assets"][6].update(locator={"kind":"local","path":"artifact"},
                                  sha256=m.digest(b"data"),size_bytes=4)
        path,_=self.freeze()
        with self.assertRaises(ValueError):
            m.inspect(path/"ram.json",path/"recovery-set.json",asset_root=inside)

if __name__=="__main__":
    unittest.main(verbosity=2)