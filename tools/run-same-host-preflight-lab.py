#!/usr/bin/env python3
"""Generated-data Docker lab only; no production, network, S3 or credentials."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("same",ROOT/"tools/same-host-preflight.py")
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def docker(*args):
    return subprocess.check_output(["/usr/bin/docker","--host","unix:///var/run/docker.sock",*args],
                                   timeout=30,text=True).strip()

def run():
    image=docker("image","inspect","ubuntu:24.04","--format","{{.Id}}")
    ids=[]
    cases=[]
    with tempfile.TemporaryDirectory(prefix="owr-same-host-priority1-") as tmp:
        root=Path(tmp);work=root/"work";work.mkdir(mode=0o700)
        prod=root/"production";prod.mkdir();marker=prod/"sentinel";marker.write_text("unchanged")
        c=dict(format="owr-same-host-verification-v1",workspace=str(work),production_paths=[str(prod)],
               container_id="a"*64,image_id=image,memory_bytes=268435456,nano_cpus=500000000,
               pids_limit=32,tmpfs_bytes=33554432,required_workspace_bytes=1048576,
               reserve_disk_bytes=1048576,reserve_memory_bytes=1048576)
        base=["--network=none","--read-only","--user=65534:65534","--cap-drop=ALL",
              "--security-opt=no-new-privileges","--ipc=private","--cgroupns=private",
              "--memory=268435456","--memory-swap=268435456","--cpus=0.5","--pids-limit=32"]
        for target in ("/work","/tmp"):
            base+=["--tmpfs",target+":rw,nosuid,nodev,noexec,size=33554432,mode=1777"]
        try:
            probe='set -eu; test "$(id -u)" = 65534; if touch /etc/owr-must-not-write 2>/dev/null; then exit 11; fi; test ! -S /var/run/docker.sock; test "$(awk \'NR>2 {print $1}\' /proc/net/dev | tr -d " :")" = lo; printf generated > /work/probe; test "$(cat /work/probe)" = generated; echo isolation-probe-passed'
            cid=docker("create",*base,image,"sh","-c",probe);ids.append(cid);c["container_id"]=cid
            config=work/"config.json";config.write_text(json.dumps(c))
            before=config.read_bytes()
            cli=subprocess.run(["python3",str(ROOT/"tools/same-host-preflight.py"),"--config",str(config)],
                               capture_output=True,text=True,timeout=30)
            result=json.loads(cli.stdout)
            assert cli.returncode==0,result
            assert docker("inspect",cid,"--format","{{.State.Status}}")=="created"
            assert config.read_bytes()==before
            cases.append({"case":"read_only_cli_valid_stopped_container","passed":True})
            # Lab-only explicit start: preflight itself never starts.
            assert docker("start","-a",cid)=="isolation-probe-passed"
            assert docker("inspect",cid,"--format","{{.State.ExitCode}}")=="0"
            cases.append({"case":"actual_nonroot_readonly_root_loopback_only_tmpfs","passed":True})
            for name,extra in [
                ("production_mount",["--mount",f"type=bind,source={prod},target=/source"]),
                ("docker_socket_mount",["--mount","type=bind,source=/var/run/docker.sock,target=/socket"]),
                ("external_network",["--network=bridge"]),
                ("unbounded_memory",["--memory=0","--memory-swap=0"]),
                ("root_user",["--user=0"]),
            ]:
                bad=docker("create",*base,*extra,image,"true");ids.append(bad)
                c["container_id"]=bad
                r=m.assess(c)
                assert r["state"]=="blocked",(name,r)
                assert docker("inspect",bad,"--format","{{.State.Status}}")=="created"
                cases.append({"case":name,"passed":True,"issues":r["issues"]})
            c["container_id"]=cid
            r=m.assess(c,memory_probe=lambda:0)
            assert "memory_headroom_insufficient" in r["issues"]
            cases.append({"case":"low_memory_injected_observation","passed":True})
            c["required_workspace_bytes"]=10**30
            r=m.assess(c)
            assert "disk_headroom_insufficient" in r["issues"]
            cases.append({"case":"disk_requirement_above_real_free_capacity","passed":True})
            assert marker.read_text()=="unchanged"
            cases.append({"case":"production_fixture_unchanged","passed":True})
        finally:
            for cid in ids:
                docker("rm","-f",cid)
        return {"format":"owr-same-host-priority1-lab-v1","image_id":image,
                "cases":cases,"cleanup_complete":True,"production_accessed":False,
                "scope":"generated fixture only; no WordPress restore, approval change or host-compromise assurance",
                "resource_evidence":"Docker hard-limit configuration; low memory injected; no exhaustion stress test"}
if __name__=="__main__":
    print(json.dumps(run(),indent=2))
