#!/usr/bin/env python3
"""Reproducible Phase 2 checks and an isolated metadata bootstrap smoke test."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
def run(args, **kw):
    return subprocess.run(args,check=True,text=True,capture_output=True,**kw)
result=run([sys.executable,"-m","unittest","discover","-s",str(ROOT/"tests"),"-v"],cwd=ROOT)
with tempfile.TemporaryDirectory(prefix="owr-phase2-") as tmp:
    box=Path(tmp)
    (box/"tools").mkdir()
    shutil.copy2(ROOT/"tools/recovery-metadata.py",box/"tools/recovery-metadata.py")
    shutil.copytree(ROOT/"schemas",box/"schemas")
    shutil.copytree(ROOT/"examples/m1/RS-M1-P2-001",box/"set")
    # No project, WP, Docker, credentials, AWS SDK or database access from CLI.
    inspected=run([sys.executable,"-I",str(box/"tools/recovery-metadata.py"),
                   "inspect","--ram",str(box/"set/ram.json"),
                   "--set",str(box/"set/recovery-set.json")],cwd=box,
                  env={"PATH":"/usr/bin:/bin","HOME":str(box)})
    inspection=json.loads(inspected.stdout)
    assert inspection["metadata_valid"] and not inspection["recovery_ready"]
    (ROOT/"evidence/m1/phase2/independent-inspection.json").write_text(
        json.dumps(inspection,indent=2)+"\n")
report={"kind":"phase2_validation","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python":sys.version,"tests_passed":True,"unit_test_output":result.stderr,
        "isolated_directory_inspection":"passed",
        "isolation_limit":"Separate directory and clean process environment; same WSL host, no network namespace isolation.",
        "authenticity":"unverified","external_availability":"unverified","restore":"untested",
        "files":{}}
for folder in ("tools","schemas","tests"):
    for path in sorted((ROOT/folder).glob("*")):
        if path.is_file() and (path.suffix in (".py",".json")):
            report["files"][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT/"evidence/m1/phase2/validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(result.stderr)
print("Independent metadata inspection: passed; E2/E3 not claimed.")