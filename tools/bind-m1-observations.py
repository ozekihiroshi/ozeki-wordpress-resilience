#!/usr/bin/env python3
"""Bind version-specific retrieval observations to an E1 capture and a NEW RAM."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("metadata",ROOT/"tools/recovery-metadata.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def bind(base,capture,observations,new_id,scope=None):
    scope=scope or {"bucket":"owr-example-bucket","region":"ap-northeast-1","prefix":"wordpress-test/"}
    m.validate_ram(base)
    m.require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",new_id) and new_id!=base["set_id"],
              "new set ID required")
    m.require(capture["site_id"]==base["site_id"] and capture["result"]=="captured_locally",
              "capture site or result mismatch")
    expected={}
    for asset in capture["assets"]:
        role="runtime" if asset["role"]=="runtime_wordpress" else asset["role"]
        m.require(role not in expected,"duplicate capture role")
        expected[role]=asset
    ram=copy.deepcopy(base)
    ram["set_id"]=new_id
    ram["created_at"]=datetime.now(timezone.utc).isoformat()
    # Clear old references: incomplete bindings must not retain a previous set's assets.
    for asset in ram["assets"]:
        asset.update(locator={"kind":"pending","reason":"phase3_observation_required"},
                     sha256=None,size_bytes=None)
    seen=set()
    bindings=[]
    for observation in observations:
        m.require(observation.get("schema_version")==1
            and observation.get("kind")=="owr-versioned-download-observation"
            and observation.get("observation")=="download_integrity_checked",
            "download observation required")
        loc=observation["locator"]
        m.require(loc["bucket"]==scope["bucket"] and loc["region"]==scope["region"]
            and loc["kind"]=="s3" and loc["key"].startswith(scope["prefix"]),
            "storage scope mismatch")
        # Use explicit role in the binding wrapper; no filename-based guess.
        role=observation["asset_role"]
        m.require(role in expected and role not in seen,"unknown or duplicate role")
        source=expected[role]
        m.require(observation["sha256"]==source["sha256"]
                  and observation["size_bytes"]==source["size_bytes"],
                  "observation differs from E1 capture")
        matches=[a for a in ram["assets"] if a["role"]==role]
        m.require(len(matches)==1,"ambiguous RAM role")
        asset=matches[0]
        asset.update(locator={**loc,"credential_ref":"recovery-reader"},
                     sha256=source["sha256"],size_bytes=source["size_bytes"])
        seen.add(role)
        bindings.append({"role":role,"actor":observation.get("actor","unrecorded"),
                         "role_separation":"unverified"})
    m.validate_ram(ram)
    return ram,{"kind":"ram_binding_report","set_id":new_id,
                "capture_id":capture["evidence_id"],"bindings":bindings,
                "pending_roles":[a["role"] for a in ram["assets"] if a["locator"]["kind"]=="pending"],
                "authenticity":"unverified","role_separation":"unverified",
                "recovery_ready":False,
                "note":"Input observations are not signed; binding is not independent authentication."}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base",required=True)
    p.add_argument("--capture",required=True)
    p.add_argument("--observations",required=True,help="JSON array, each observation plus explicit asset_role")
    p.add_argument("--set-id",required=True)
    p.add_argument("--output",required=True,help="New directory; existing directory refused")
    a=p.parse_args()
    ram,report=bind(m.read(a.base)[0],m.read(a.capture)[0],m.read(a.observations)[0],a.set_id)
    output=Path(a.output)
    output.mkdir(parents=True,exist_ok=False)
    (output/"ram.json").write_text(json.dumps(ram,ensure_ascii=False,indent=2)+"\n")
    (output/"binding-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))