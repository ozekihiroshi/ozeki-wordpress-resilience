import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location("same_host", ROOT / "tools/same-host-preflight.py")
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)


class SameHostPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.work = root / "work"
        self.prod = root / "production"
        self.work.mkdir(mode=0o700)
        self.prod.mkdir()
        self.marker = self.prod / "untouched"
        self.marker.write_text("production fixture")
        self.c = dict(format="owr-same-host-verification-v1", workspace=str(self.work),
                      production_paths=[str(self.prod)], container_id="a"*64, image_id="sha256:"+"b"*64,
                      memory_bytes=268435456, nano_cpus=500000000, pids_limit=32,
                      tmpfs_bytes=33554432, required_workspace_bytes=1048576,
                      reserve_disk_bytes=1048576, reserve_memory_bytes=1048576)
        self.d = dict(Id=self.c["container_id"], Image=self.c["image_id"], Mounts=[],
                      Config=dict(User="65534:65534"), NetworkSettings={"Networks":{"none":{}}},
                      State=dict(Status="created", Running=False),
                      HostConfig=dict(ReadonlyRootfs=True, NetworkMode="none", CapDrop=["ALL"],
                                      SecurityOpt=["no-new-privileges"], IpcMode="private", CgroupnsMode="private",
                                      RestartPolicy={"Name":"no"}, Memory=268435456,
                                      MemorySwap=268435456, NanoCpus=500000000, PidsLimit=32,
                                      Tmpfs={p:"rw,nosuid,nodev,noexec,size=33554432,mode=1777"
                                             for p in ("/tmp","/work")}))
    def tearDown(self):
        self.assertEqual(self.marker.read_text(), "production fixture")
        self.tmp.cleanup()
    def assess(self):
        return m.assess(self.c, lambda _: self.d, lambda: 10**10, lambda _: SimpleNamespace(free=10**10))
    def test_valid_is_not_restore_or_approval(self):
        r=self.assess()
        self.assertEqual(r["state"],"eligible_for_dedicated_trial")
        self.assertFalse(r["restore_started"])
        self.assertFalse(r["approval_changed"])
        self.assertFalse(r["independent_verification"])
    def test_unsafe_runtime_matrix(self):
        cases=[("NetworkMode","bridge"),("PortBindings",{"80/tcp":[{"HostPort":"8080"}]}),
               ("ReadonlyRootfs",False),("Privileged",True),("CapAdd",["SYS_ADMIN"]),
               ("SecurityOpt",["seccomp=unconfined"]),("PidMode","host"),("IpcMode","host"),
               ("UsernsMode","host"),("CgroupnsMode","host"),("Devices",[{"PathOnHost":"/dev/sda"}]),
               ("Binds",["/var/run/docker.sock:/socket"]),("VolumesFrom",["production"]),
               ("Memory",0),("MemorySwap",-1),("NanoCpus",0),("PidsLimit",0),
               ("Tmpfs",{"/work":"rw"}),("RestartPolicy",{"Name":"always"})]
        for key,value in cases:
            with self.subTest(key=key):
                old=copy.deepcopy(self.d)
                self.d["HostConfig"][key]=value
                self.assertEqual(self.assess()["state"],"blocked")
                self.d=old
    def test_configured_mount_even_if_not_bind(self):
        self.d["Mounts"]=[{"Type":"volume","Destination":"/db"}]
        self.assertIn("mounts_forbidden",self.assess()["issues"])
    def test_extra_network_even_with_none_mode(self):
        self.d["NetworkSettings"]["Networks"]["bridge"]={}
        self.assertIn("network_isolation_required",self.assess()["issues"])
    def test_root_and_image_change_and_running(self):
        for group,key,value in [("Config","User","0"),("State","Status","running"),
                                ("Config","Volumes",{"/data":{}}),
                                ("Config","Healthcheck",{"Test":["CMD","curl"]})]:
            old=copy.deepcopy(self.d)
            self.d[group][key]=value
            self.assertEqual(self.assess()["state"],"blocked")
            self.d=old
        self.d["Image"]="sha256:"+"c"*64
        self.assertIn("container_binding_mismatch",self.assess()["issues"])
    def test_production_overlap_both_directions(self):
        for p in (self.work,self.work.parent):
            self.c["production_paths"]=[str(p)]
            self.assertEqual(self.assess()["state"],"blocked")
        child=self.work/"child";child.mkdir()
        self.c["production_paths"]=[str(child)]
        self.assertEqual(self.assess()["state"],"blocked")
    def test_symlink_ancestor(self):
        link=self.work.parent/"alias";link.symlink_to(self.work.parent,target_is_directory=True)
        self.c["workspace"]=str(link/"work")
        self.assertEqual(self.assess()["state"],"blocked")
    def test_permissions_and_missing_paths(self):
        self.work.chmod(0o755)
        self.assertEqual(self.assess()["state"],"blocked")
        self.work.chmod(0o700)
        self.c["production_paths"]=[str(self.prod/"absent")]
        self.assertEqual(self.assess()["state"],"blocked")
    def test_invalid_limits_and_unknown_keys(self):
        for value in (True,0,-1,1.2,"100",None):
            self.c["memory_bytes"]=value
            self.assertEqual(self.assess()["state"],"blocked")
        self.c["memory_bytes"]=268435456
        self.c["database_host"]="production"
        self.assertEqual(self.assess()["state"],"blocked")
    def test_capacity_blocks_without_start(self):
        r=m.assess(self.c,lambda _:self.d,lambda:0,lambda _:SimpleNamespace(free=0))
        self.assertEqual(set(r["issues"]),{"memory_headroom_insufficient","disk_headroom_insufficient"})
        self.assertFalse(r["restore_started"])
    def test_inspection_failure_blocks(self):
        def fail(_):raise TimeoutError()
        self.assertEqual(m.assess(self.c,fail)["state"],"blocked")
    def test_no_output_or_workspace_writes(self):
        before=list(self.work.iterdir())
        self.assess()
        self.assertEqual(list(self.work.iterdir()),before)
    def test_existing_reader_duplicate_keys(self):
        f=self.work/"bad.json";f.write_text('{"format":1,"format":2}')
        with self.assertRaises(ValueError):m.preflight.read_json(f)


if __name__=="__main__":
    unittest.main()
