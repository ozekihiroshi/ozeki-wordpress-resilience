import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("pair",ROOT/"tools/same-host-runtime.py")
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Pair(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name);p.chmod(0o700)
        self.c=dict(format=m.FORMAT,workspace=str(p),production_paths=[],token="a"*32,
                    db_id="b"*64,web_id="c"*64,db_image="sha256:"+"d"*64,web_image="sha256:"+"e"*64)
        self.ds={}
        for role in ("db","web"):
            self.ds[self.c[role+"_id"]]=dict(Id=self.c[role+"_id"],Image=self.c[role+"_image"],
              State={"Status":"created"},Mounts=[],
              Config={"User":"0:0","Labels":{"owr.daily-restore":"generated",
                "owr.recovery-token":self.c["token"],"owr.runtime-role":role},"Healthcheck":{"Test":["NONE"]}},
              HostConfig=dict(ReadonlyRootfs=True,CapDrop=["ALL"],CapAdd=list(m.CAPS),
                SecurityOpt=["no-new-privileges"],LogConfig={"Type":"local","Config":{"max-size":"1m","max-file":"2"}},Tmpfs=m.mounts(role),IpcMode="private",CgroupnsMode="private",
                NetworkMode="none" if role=="db" else "container:"+self.c["db_id"],
                Memory=m.MEMORY,MemorySwap=m.MEMORY,NanoCpus=500000000,PidsLimit=128,RestartPolicy={"Name":"no"}),
              NetworkSettings={"Networks":{"none":{}} if role=="db" else {}})
    def tearDown(self):self.tmp.cleanup()
    def assess(self,phase="prepared"):
        with patch.object(m.base,"memory_available",return_value=10**11):
            return m.assess(self.c,inspector=lambda i:self.ds[i],phase=phase)
    def test_docker_canonical_capability_names(self):
        for d in self.ds.values():
            d["HostConfig"]["CapAdd"]=["CAP_"+x for x in m.CAPS]
        self.assertFalse(self.assess()["issues"])
    def test_stages(self):
        self.assertFalse(self.assess()["issues"])
        self.ds[self.c["db_id"]]["State"]["Status"]="running"
        self.assertTrue(self.assess()["issues"])
        self.assertFalse(self.assess("db_started")["issues"])
        self.ds[self.c["web_id"]]["State"]["Status"]="running"
        self.assertFalse(self.assess("running")["issues"])
    def test_dangerous_settings_rejected(self):
        cases=[("Privileged",True),("CapAdd",["SYS_ADMIN"]),("ReadonlyRootfs",False),
          ("Binds",["/production:/var/www/html"]),("NetworkMode","host"),
          ("PortBindings",{"80/tcp":[{"HostPort":"8000"}]}),("Memory",0),("PidsLimit",0),
          ("NanoCpus",0),("MemorySwap",-1),("Tmpfs",{}),("PidMode","host"),
          ("SecurityOpt",["seccomp=unconfined"]),("Devices",[{"PathOnHost":"/dev/sda"}])]
        for role in ("db","web"):
            for key,value in cases:
                with self.subTest(role=role,key=key):
                    saved=copy.deepcopy(self.ds)
                    self.ds[self.c[role+"_id"]]["HostConfig"][key]=value
                    self.assertTrue(self.assess()["issues"])
                    self.ds=saved
    def test_membership_and_namespace_target(self):
        self.ds[self.c["db_id"]]["NetworkSettings"]["Networks"]["bridge"]={}
        self.assertIn("network_mismatch",self.assess()["issues"])
        del self.ds[self.c["db_id"]]["NetworkSettings"]["Networks"]["bridge"]
        self.ds[self.c["web_id"]]["HostConfig"]["NetworkMode"]="container:"+"f"*64
        self.assertIn("network_mismatch",self.assess()["issues"])
    def test_owner_and_image(self):
        self.ds[self.c["web_id"]]["Config"]["Labels"]["owr.recovery-token"]="bad"
        self.assertIn("ownership_mismatch",self.assess()["issues"])
        self.ds[self.c["db_id"]]["Image"]="sha256:"+"f"*64
        self.assertIn("image_or_id_mismatch",self.assess()["issues"])
    def test_persistent_volume(self):
        self.ds[self.c["db_id"]]["Mounts"]=[{"Type":"volume","Name":"existing"}]
        self.assertIn("persistent_mounts_forbidden",self.assess()["issues"])
    def test_source_path_overlap(self):
        self.c["production_paths"]=[self.c["workspace"]]
        self.assertIn("production_overlap",self.assess()["issues"])
    def test_capacity_and_inspection_failure(self):
        with patch.object(m.base,"memory_available",return_value=0):
            self.assertIn("memory_headroom_insufficient",m.assess(self.c,inspector=lambda i:self.ds[i])["issues"])
        def fail(_):raise OSError()
        self.assertTrue(m.assess(self.c,inspector=fail)["issues"])
    def test_generated_plan_has_no_start(self):
        args=m.create_args("web","fixture",self.c["web_image"],self.c["token"],"/private/env",self.c["db_id"])
        self.assertEqual(args[:2],["docker","create"])
        self.assertNotIn("--privileged",args)
        self.assertNotIn("--volume",args)
        self.assertIn("--read-only",args)
        self.assertIn("container:"+self.c["db_id"],args)
if __name__=="__main__":unittest.main()
