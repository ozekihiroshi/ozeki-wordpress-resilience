#!/usr/bin/env python3
"""Fetch trusted-locator bytes from dm/S3, never from the original WordPress."""
import datetime,importlib.util,json,os,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("storage",ROOT/"tools/m1-live-storage.py")
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
os.umask(0o077)
bundle=ROOT/".local/independent-download"
bundle.mkdir(exist_ok=False)
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
s.run(["scp","-q",s.READER+":"+s.DM+"/anchor.json",str(bundle/"anchor.json")])
anchor=json.loads((bundle/"anchor.json").read_text())
assert anchor["set_id"]==s.RUN
def fetch(receipt,name):
    s.download_dm(receipt,name)
    s.run(["scp","-q",s.READER+":"+s.DM+"/"+name,str(bundle/name)])
    assert (bundle/name).stat().st_size==receipt["size_bytes"]
    assert s.hash_file(bundle/name)==receipt["sha256"]
for kind,name in [("set","recovery-set.json"),("ram","ram.json"),("bootstrap","bootstrap.tar.gz")]:
    fetch(anchor[kind],name)
record=json.loads((bundle/"recovery-set.json").read_text())
ram=json.loads((bundle/"ram.json").read_text())
assert s.hash_file(bundle/"ram.json")==record["ram_sha256"]
assert record["set_id"]==ram["set_id"]==anchor["set_id"]
assert record["asset_ids"]==sorted(a["id"] for a in ram["assets"])
mapping={}
for asset in ram["assets"]:
    assert asset["locator"]["kind"]=="s3"
    name=asset["id"]+".bin"
    assert "/" not in name and ".." not in name
    fetch(asset,name)
    mapping[asset["id"]]=name
    print("Fresh independent download:",asset["id"],flush=True)
(bundle/"downloads.json").write_text(json.dumps(mapping,indent=2)+"\n")
with tarfile.open(bundle/"bootstrap.tar.gz") as t:
    for member in t:
        assert not(member.issym() or member.islnk() or member.isdev()
                   or member.name.startswith("/") or ".." in Path(member.name).parts)
    t.extractall(bundle,filter="data")
report={"kind":"independent_bootstrap_fetch","started_at":started,
        "finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "set_id":s.RUN,"assets":len(mapping),"source_access":"none",
        "retrieval_path":"dm IAM role -> exact S3 VersionId -> SHA256 -> new WSL directory",
        "roles_shared":True,"authenticity":"unverified"}
(root:=ROOT/"evidence/m1/e3").mkdir(parents=True,exist_ok=True)
(root/"independent-fetch.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report))