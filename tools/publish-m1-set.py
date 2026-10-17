#!/usr/bin/env python3
import importlib.util,json,subprocess,datetime,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/"tools"/file)
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
storage=module("storage","m1-live-storage.py")
binding=module("binding","bind-m1-observations.py")
w=storage.WORK
plan=json.loads((w/"upload-plan.json").read_text())
observations=[]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
for asset in plan["assets"]:
 name=Path(asset["path"]).name
 receipt=storage.upload(ROOT/asset["path"],name)
 observed=storage.download_dm(receipt,name)
 observed["asset_role"]=asset["role"]
 if asset["role"]!="bootstrap":observations.append(observed)
 output=w/"observations";output.mkdir(exist_ok=True)
 if not (output/(name+".json")).exists():storage.write(output/(name+".json"),observed)
 print("Verified from dm:",asset["role"],flush=True)
manifest=json.loads((w/"capture-manifest.json").read_text())
capture={"site_id":manifest["site_id"],"evidence_id":manifest["capture_id"],
         "result":"captured_locally","assets":[a for a in plan["assets"] if a["role"]!="bootstrap"]}
base=binding.m.read(ROOT/"examples/m1/RS-M1-P2-001/ram.json")[0]
ram,report=binding.bind(base,capture,observations,storage.RUN,storage.TARGET)
assert not report["pending_roles"]
candidate=w/"ram-candidate.json"
storage.write(candidate,ram)
fixed=binding.m.publish(candidate,w/"sets")
setdir=Path(fixed["directory"])
r_ram=storage.upload(setdir/"ram.json","ram.json")
r_set=storage.upload(setdir/"recovery-set.json","recovery-set.json")
storage.download_dm(r_ram,"ram.json");storage.download_dm(r_set,"recovery-set.json")
bootstrap=json.loads((w/"receipts/bootstrap.tar.gz.json").read_text())
anchor={"kind":"owr-bootstrap-anchor","schema_version":1,"set_id":storage.RUN,
 "site_id":ram["site_id"],"set":r_set,"ram":r_ram,"bootstrap":bootstrap,
 "created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "trust":"operator-copied to separate dm host; same administrative operator; authenticity unverified",
 "role_separation":"unmet_user_accepted"}
storage.write(w/"anchor.json",anchor)
storage.run(["scp","-q",str(w/"anchor.json"),storage.READER+":"+storage.DM+"/anchor.json"])
storage.ssh(storage.READER,["chmod","600",storage.DM+"/anchor.json"])
evidence=ROOT/"evidence/m1/e2";evidence.mkdir(parents=True,exist_ok=True)
storage.write(evidence/(storage.RUN+".json"),{"kind":"E2","started_at":started,
 "finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"set_id":storage.RUN,
 "observations":observations,"binding":report,"all_required_assets_downloaded":True,
 "role_separation":"unmet_user_accepted","authenticity":"unverified","restore":"untested"})
storage.write(evidence/(storage.RUN+"-anchor.json"),anchor)
print("Published and independently downloaded all assets; separate IAM role NOT established",flush=True)