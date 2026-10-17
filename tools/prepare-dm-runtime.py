#!/usr/bin/env python3
"""Install a signature-verified AWS CLI into an isolated user-owned M1 directory."""
import hashlib,html,json,os,re,subprocess,urllib.request
from pathlib import Path
os.umask(0o077)
root=Path.home()/".local/owr-m1-runtime"
root.mkdir(parents=True,exist_ok=True)
binary=root/"bin/aws"
if not binary.exists():
    page=urllib.request.urlopen("https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",timeout=30).read().decode()
    block=re.search(r"-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----",page,re.S).group()
    key=html.unescape(re.sub("<[^>]+>","",block))
    key="\n".join(line.strip() for line in key.splitlines())+"\n"
    (root/"aws-cli-key.asc").write_text(key)
    for suffix in (".zip",".zip.sig"):
        url="https://awscli.amazonaws.com/awscli-exe-linux-x86_64"+suffix
        with urllib.request.urlopen(url,timeout=60) as source,(root/("installer"+suffix)).open("wb") as target:
            while True:
                chunk=source.read(1024*1024)
                if not chunk:break
                target.write(chunk)
    home=root/"gnupg";home.mkdir(mode=0o700,exist_ok=True)
    gpg=["gpg","--homedir",str(home),"--batch"]
    subprocess.run(gpg+["--import",str(root/"aws-cli-key.asc")],check=True,capture_output=True)
    verified=subprocess.run(gpg+["--status-fd","1","--verify",str(root/"installer.zip.sig"),str(root/"installer.zip")],
                            check=True,capture_output=True,text=True)
    assert "VALIDSIG FB5DB77FD5C118B80511ADA8A6310ACC4672475C" in verified.stdout
    subprocess.run(["unzip","-q",str(root/"installer.zip"),"-d",str(root/"unpacked")],check=True)
    subprocess.run([str(root/"unpacked/aws/install"),"-i",str(root/"cli"),"-b",str(root/"bin")],check=True,capture_output=True)
    report={"installer_sha256":hashlib.sha256((root/"installer.zip").read_bytes()).hexdigest(),
            "signing_fingerprint":"FB5DB77FD5C118B80511ADA8A6310ACC4672475C",
            "scope":"isolated user directory; system CLI unchanged"}
    (root/"installation.json").write_text(json.dumps(report,indent=2)+"\n")
print(subprocess.run([str(binary),"--version"],check=True,capture_output=True,text=True).stdout.strip())
env={k:v for k,v in os.environ.items() if not k.startswith("AWS_")}
env.update(AWS_CONFIG_FILE="/dev/null",AWS_SHARED_CREDENTIALS_FILE="/dev/null",AWS_DEFAULT_REGION="ap-northeast-1",AWS_PAGER="")
result=subprocess.run([str(binary),"sts","get-caller-identity","--output","json"],env=env,check=True,capture_output=True,text=True)
print(result.stdout)
print(json.dumps({"binary":str(binary)}))