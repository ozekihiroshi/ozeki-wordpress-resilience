#!/usr/bin/env python3
"""Live, bounded M1 storage runner. Uses existing SSH hosts, no IAM mutations."""
import datetime,hashlib,json,os,shlex,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
WORK=Path(os.environ.get("OWR_BUNDLE_DIR",ROOT/".local/phase45")).resolve()
CONFIG_PATH=Path(os.environ.get("OWR_LIVE_CONFIG",ROOT/".local/live-target.json"))
TARGET=json.loads(CONFIG_PATH.read_text())
RUN=TARGET["set_id"]
WRITER=TARGET["writer_host"];READER=TARGET["reader_host"]
assert __import__("re").fullmatch(r"[A-Za-z0-9_-]+", RUN)
assert TARGET["owner"]!="123456789012" and TARGET["bucket"]!="owr-example-bucket"
REMOTE="/tmp/owr-m1-"+RUN
DM=TARGET["reader_home"]+"/.local/owr-m1/"+RUN
ENV=["env","-u","AWS_ACCESS_KEY_ID","-u","AWS_SECRET_ACCESS_KEY","-u","AWS_SESSION_TOKEN",
     "-u","AWS_PROFILE","-u","AWS_ROLE_ARN","-u","AWS_WEB_IDENTITY_TOKEN_FILE",
     "AWS_CONFIG_FILE=/dev/null","AWS_SHARED_CREDENTIALS_FILE=/dev/null",
     "AWS_DEFAULT_REGION="+TARGET["region"],"AWS_PAGER="]
def run(args,**kw):
    return subprocess.run(args,check=True,cwd=ROOT,**kw)
def ssh(host,args,**kw):
    return run(["ssh","-o","BatchMode=yes","-o","ConnectTimeout=15",host,shlex.join(args)],**kw)
def hash_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()
def write(path,obj):
    with Path(path).open("x") as f:json.dump(obj,f,indent=2);f.write("\n")
def upload(path,name):
    receipts=WORK/"receipts";receipts.mkdir(exist_ok=True)
    receipt=receipts/(name+".json")
    if receipt.exists():
        existing=json.loads(receipt.read_text())
        assert existing.get("kind")=="owr-versioned-upload-receipt","Indeterminate receipt; inspect before retry"
        assert existing["sha256"]==hash_file(path) and existing["size_bytes"]==path.stat().st_size
        return existing
    size=path.stat().st_size;sha=hash_file(path)
    assert size<1024**3,"Single artifact budget exceeded"
    incoming=REMOTE+"/input-"+name
    run(["scp","-q",str(path),WRITER+":"+incoming])
    key=TARGET["prefix"]+RUN+"/"+name
    print("Uploading",name,size,"bytes",flush=True)
    try:
        ssh(WRITER,ENV+["php",REMOTE+"/tools/versioned-s3-transfer.php",
            "upload",incoming,key,str(size),sha,REMOTE+"/receipt-"+name+".json"])
    finally:
        # Our exact newly transferred temporary file only.
        ssh(WRITER,["rm","-f","--",incoming])
        subprocess.run(["scp","-q",WRITER+":"+REMOTE+"/receipt-"+name+".json",str(receipt)],cwd=ROOT,check=False)
    run(["scp","-q",WRITER+":"+REMOTE+"/receipt-"+name+".json",str(receipt)])
    result=json.loads(receipt.read_text())
    assert result["kind"]=="owr-versioned-upload-receipt"
    return result
def download_dm(receipt,name):
    target=DM+"/"+name
    meta=ssh(READER,ENV+[TARGET["aws_cli"],"s3api","get-object",
        "--bucket",TARGET["bucket"],"--expected-bucket-owner",TARGET["owner"],
        "--key",receipt["locator"]["key"],"--version-id",receipt["locator"]["version_id"],
        target,"--output","json"],capture_output=True,text=True)
    result=json.loads(meta.stdout)
    assert result["VersionId"]==receipt["locator"]["version_id"]
    script="import hashlib,json,sys; p=sys.argv[1]; h=hashlib.sha256(); f=open(p,'rb'); n=0\nwhile True:\n b=f.read(1048576)\n if not b: break\n n+=len(b);h.update(b)\nprint(json.dumps({'size_bytes':n,'sha256':h.hexdigest()}))"
    checked=json.loads(ssh(READER,["python3","-c",script,target],capture_output=True,text=True).stdout)
    assert checked["size_bytes"]==receipt["size_bytes"] and checked["sha256"]==receipt["sha256"]
    identity=json.loads(ssh(READER,ENV+[TARGET["aws_cli"],"sts","get-caller-identity","--output","json"],capture_output=True,text=True).stdout)
    return {"kind":"owr-versioned-download-observation","schema_version":1,
        "locator":receipt["locator"],**checked,"actor":identity["Arn"],
        "observation":"download_integrity_checked","role_separation":"unverified",
        "authenticity":"unverified","checked_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
def setup():
    ssh(WRITER,["mkdir","-p","-m","700",REMOTE,REMOTE+"/.local"])
    run(["scp","-q",str(WORK/"transport-code.tar.gz"),WRITER+":"+REMOTE+"/code.tar.gz"])
    ssh(WRITER,["tar","-xzf",REMOTE+"/code.tar.gz","-C",REMOTE])
    ssh(WRITER,["rm","--",REMOTE+"/code.tar.gz"])
    run(["scp","-q",str(CONFIG_PATH),WRITER+":"+REMOTE+"/.local/live-target.json"])
    ssh(READER,["mkdir","-p","-m","700",DM])
if __name__=="__main__":
    os.umask(0o077)
    if sys.argv[1]=="setup":setup()
    elif sys.argv[1]=="asset":
        receipt=upload(Path(sys.argv[2]).resolve(),sys.argv[3])
        obs=download_dm(receipt,sys.argv[3])
        out=WORK/"observations";out.mkdir(exist_ok=True)
        path=out/(sys.argv[3]+".json")
        if not path.exists():write(path,obs)
        print(json.dumps(obs))