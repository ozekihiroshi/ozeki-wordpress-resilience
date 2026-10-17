import hashlib,json,tarfile,datetime,subprocess,sys,re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if len(sys.argv)!=2 or not re.fullmatch(r"CAP-M1-[A-Za-z0-9-]+",sys.argv[1]):
    raise SystemExit("Usage: python3 tools/verify-m1-capture.py CAP-M1-...")
cap=root/".local/captures"/sys.argv[1]
baseline=json.loads((root/"evidence/m1/phase1/source-baseline.json").read_text())
with tarfile.open(cap/"uploads.tar.gz") as t:
    actual={}
    for member in t:
        if member.isfile():
            actual[member.name.removeprefix("wp-content/uploads/")]=hashlib.sha256(t.extractfile(member).read()).hexdigest()
expected=baseline["upload_inventory"]
if isinstance(expected,list):
    exp={x["path"]:x["sha256"] for x in expected}
else:
    exp={k:v["sha256"] for k,v in expected.items()}
assert actual==exp,(list(actual),list(exp))
with tarfile.open(cap/"configuration.tar.gz") as t:
    assert len(t.getmembers())==5
    assert all("runtime.env" not in x.name and "wp-config.php" not in x.name for x in t)
run=subprocess.run(["python3","-m","unittest","discover","-s","tests","-v"],
                   cwd=root,capture_output=True,text=True)
report={"kind":"phase3_local_validation","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "capture_id":cap.name,"uploads_match_baseline":len(actual),
        "configuration_secret_files_excluded":True,"tests_passed":run.returncode==0,
        "unit_test_output":run.stderr,"E2":"not_performed","authenticity":"unverified"}
out=root/"evidence/m1/phase3"
out.mkdir(exist_ok=True)
(out/"local-validation.json").write_text(json.dumps(report,indent=2)+"\n")
assert run.returncode==0
print("Upload files match baseline:",len(actual))
print(run.stderr[-100:])