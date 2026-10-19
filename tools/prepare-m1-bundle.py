import datetime,hashlib,json,shutil,tarfile,subprocess
from pathlib import Path
import argparse
p=argparse.ArgumentParser()
p.add_argument("--capture",required=True)
p.add_argument("--baseline",required=True)
p.add_argument("--set-id",required=True)
p.add_argument("--output",required=True)
p.add_argument("--images",default="lab/m1/images.env")
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
work=(root/a.output).resolve()
if not work.is_relative_to(root/".local"):raise ValueError("Output must be under .local")
work.mkdir(parents=True,exist_ok=False)
boot=work/"bootstrap";boot.mkdir(exist_ok=True)
for source,target in [
 ("tools/run-independent-recovery.py","run-independent-recovery.py"),
 ("tools/verify-recovered-http.py","verify-http.py"),
 ("lab/m1/fixture/verify.php","verify.php"),
 ("lab/m1/preview.conf","preview.conf"),
 (a.baseline,"baseline.json")]:
 shutil.copy2(root/source,boot/target)
(boot/"reset-admin.php").write_text("""<?php
if (getenv('OWR_FIXTURE') !== '1') { throw new RuntimeException('Fixture only'); }
require '/var/www/html/wp-load.php';
$user=get_user_by('login','owradmin');
if (!$user || !getenv('OWR_ADMIN_PASSWORD')) { throw new RuntimeException('Missing fixture admin'); }
wp_set_password(getenv('OWR_ADMIN_PASSWORD'), $user->ID);
""")
images={}
for line in (root/a.images).read_text().splitlines():
 if "=" in line:
  k,v=line.split("=",1)
  images[{"OWR_WP_IMAGE":"wordpress","OWR_DB_IMAGE":"database","OWR_PROXY_IMAGE":"proxy"}[k]]=v
(boot/"images.json").write_text(json.dumps(images,indent=2)+"\n")
(boot/"README.txt").write_text("M1 synthetic recovery bundle. No source-server access is needed.\nUse the separately stored anchor to fetch and hash the Recovery Set, RAM and assets by VersionId.\nDo not execute this archived runner. Use independently installed tools/run-independent-recovery.py with --trust-dir --approval --signature --site-id --set-id plus --bundle --output --run.\nRequires Linux, Python3 and Docker Compose. Roles remain shared in this experiment.\n")
with tarfile.open(work/"bootstrap.tar.gz","w:gz") as t:
 t.add(boot,arcname="bootstrap")
capture=json.loads((root/a.capture).read_text())
def artifact(role,path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return {"role":role,"path":str(path.relative_to(root)),"size_bytes":path.stat().st_size,"sha256":h.hexdigest()}
assets=[a for a in capture["assets"] if a["role"]!="runtime_wordpress"]
with (work/"runtime-images.tar.gz").open("xb") as raw:
 import gzip
 with gzip.GzipFile(fileobj=raw,mode="wb",mtime=0,compresslevel=1) as compressed:
  process=subprocess.Popen(["docker","save",*images.values()],stdout=subprocess.PIPE)
  shutil.copyfileobj(process.stdout,compressed)
  if process.wait()!=0:raise RuntimeError("Docker image export failed")
assets.append(artifact("runtime",work/"runtime-images.tar.gz"))
manifest={"format":"owr-capture-manifest","schema_version":1,
 "capture_id":capture["evidence_id"],"site_id":"owr-m1-synthetic",
 "capture_started_at":capture["started_at"],"capture_finished_at":capture["finished_at"],
 "consistency":"uncoordinated","source":"shared backup core PHP dumper plus explicit file capture",
 "backup_core_version":"0.1.0",
 "plugin_commit":capture["plugin_commit"],"assets":assets,
 "note":"This is an OWR capture index, not odbfs3-recovery-set or a claim of prior S3 verification."}
(work/"capture-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
assets.append(artifact("recovery_manifest",work/"capture-manifest.json"))
assets.append(artifact("bootstrap",work/"bootstrap.tar.gz"))
plan={"set_id":a.set_id,"assets":assets,
      "total_bytes":sum(x["size_bytes"] for x in assets),
      "roles_shared":True,"user_accepted_role_separation_unmet":True}
assert plan["total_bytes"]<1024**3
(work/"upload-plan.json").write_text(json.dumps(plan,indent=2)+"\n")
print(json.dumps({"total_bytes":plan["total_bytes"],"assets":len(assets)}))
subprocess.run(["python3","-m","py_compile",str(boot/"run-independent-recovery.py"),str(boot/"verify-http.py")],check=True)
with tarfile.open(work/"transport-code.tar.gz","w:gz") as archive:
 for name in ["src","tools/versioned-s3-transfer.php","tools/temporary-role-auth.php","tools/aws-autoload.php","tools/live-target.php"]:
  archive.add(root/name,arcname=name)
 dependency=root/"vendor"
 if not dependency.exists():dependency=root/".local/backup-plugin/vendor"
 archive.add(dependency,arcname="vendor")
