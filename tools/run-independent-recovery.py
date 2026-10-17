#!/usr/bin/env python3
"""Restore only from downloaded M1 assets into fresh isolated Docker volumes."""
import argparse,datetime,gzip,hashlib,json,os,secrets,subprocess,tarfile,time,shlex
from pathlib import Path
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def call(args,**kw):return subprocess.run(args,check=True,**kw)
def digest(path):
 h=hashlib.sha256()
 with path.open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--bundle",required=True);p.add_argument("--output",required=True)
 p.add_argument("--run",type=int,choices=[1,2],required=True)
 a=p.parse_args();bundle=Path(a.bundle).resolve();out=Path(a.output).resolve()
 out.mkdir(parents=True,exist_ok=False);os.umask(0o077)
 report={"kind":"E3","started_at":now(),"run":a.run,"passed":False,"source_access":"none"}
 try:
  for name in ("owr-m1-source-1","owr-m1-source-db-1","owr-m1-preview-1"):
   state=json.loads(call(["docker","inspect",name],capture_output=True,text=True).stdout)[0]
   assert not state["State"]["Running"],"Original source must be stopped"
  report["source_containers_stopped"]=True
  ram=json.loads((bundle/"ram.json").read_text())
  record=json.loads((bundle/"recovery-set.json").read_text())
  assert digest(bundle/"ram.json")==record["ram_sha256"]
  mapping=json.loads((bundle/"downloads.json").read_text());assets={}
  for asset in ram["assets"]:
   f=(bundle/mapping[asset["id"]]).resolve()
   assert f.is_relative_to(bundle) and f.stat().st_size==asset["size_bytes"]
   assert digest(f)==asset["sha256"]
   assets[asset["role"]]=f
  for role in ("database","uploads","themes","plugins","wordpress_core","configuration","runtime","recovery_manifest"):
   assert role in assets
  for role in ("uploads","themes","plugins","wordpress_core"):
   with tarfile.open(assets[role]) as archive:
    for member in archive:
     assert not (member.issym() or member.islnk() or member.isdev()
                 or member.name.startswith("/") or ".." in Path(member.name).parts)
  with assets["runtime"].open("rb") as stream:
   call(["docker","load"],stdin=stream,stdout=subprocess.DEVNULL)
  images=json.loads((bundle/"bootstrap/images.json").read_text())
  project="owr-m1-e3-"+str(a.run);wp=images["wordpress"];db=images["database"];proxy=images["proxy"]
  if call(["docker","ps","-aq","--filter","label=com.docker.compose.project="+project],
          capture_output=True,text=True).stdout.strip():
   raise RuntimeError("Recovery project already exists")
  report["project"]=project
  env=out/"runtime.env"
  env.write_text("RECOVERY_DB_PASSWORD="+secrets.token_hex(24)+"\nRECOVERY_ROOT_PASSWORD="
      +secrets.token_hex(24)+"\nOWR_ADMIN_PASSWORD="+secrets.token_hex(24)+"\n")
  var=lambda key:"$"+"{"+key+"}"
  service=lambda image:{"image":image,"pull_policy":"never","restart":"no","networks":["recovery"]}
  db_service=service(db)
  db_service.update(environment={"MARIADB_DATABASE":"owr_recovery","MARIADB_USER":"owr_recovery",
    "MARIADB_PASSWORD":var("RECOVERY_DB_PASSWORD"),"MARIADB_ROOT_PASSWORD":var("RECOVERY_ROOT_PASSWORD")},
    volumes=["db:/var/lib/mysql"],mem_limit="512m",
    healthcheck={"test":["CMD","healthcheck.sh","--connect","--innodb_initialized"],"interval":"3s","timeout":"5s","retries":40})
  wp_service=service(wp)
  wp_service.update(environment={"WORDPRESS_DB_HOST":"db:3306","WORDPRESS_DB_NAME":"owr_recovery",
    "WORDPRESS_DB_USER":"owr_recovery","WORDPRESS_DB_PASSWORD":var("RECOVERY_DB_PASSWORD"),
    "WORDPRESS_TABLE_PREFIX":"owr_","OWR_FIXTURE":"1","OWR_ADMIN_PASSWORD":var("OWR_ADMIN_PASSWORD"),
    "WORDPRESS_CONFIG_EXTRA":"\n".join("define('"+key+"', true);" for key in
      ["DISABLE_WP_CRON","WP_HTTP_BLOCK_EXTERNAL","AUTOMATIC_UPDATER_DISABLED","DISALLOW_FILE_MODS"])+"\ndefine('WP_ENVIRONMENT_TYPE', 'local');"},
    volumes=["site:/var/www/html",str(bundle/"bootstrap")+":/verify:ro"],mem_limit="768m",
    healthcheck={"test":["CMD","php","-r","exit(is_file('/var/www/html/wp-config.php') && @fsockopen('127.0.0.1',80) ? 0 : 1);"],
                 "interval":"3s","timeout":"5s","retries":40})
  preview=service(proxy)
  preview.update(networks=["recovery","ingress"],ports=["127.0.0.1:18081:80"],
    volumes=[str(bundle/"bootstrap/preview.conf")+":/etc/nginx/conf.d/default.conf:ro"],mem_limit="64m")
  net=48+(a.run-1)*32
  compose={"name":project,"services":{"db":db_service,"source":wp_service,"preview":preview},
    "volumes":{"db":{},"site":{}},"networks":{
      "recovery":{"internal":True,"ipam":{"config":[{"subnet":"10.203.106."+str(net)+"/28"}]}},
      "ingress":{"ipam":{"config":[{"subnet":"10.203.106."+str(net+16)+"/28"}]}}}}
  (out/"compose.json").write_text(json.dumps(compose,indent=2))
  cli=["docker","compose","--ansi","never","--progress","plain","--env-file",str(env),
       "-f",str(out/"compose.json")]
  call(cli+["up","-d","--wait","--wait-timeout","150","db"])
  call(["docker","volume","create",project+"_site"],stdout=subprocess.DEVNULL)
  names=[assets[x].name for x in ("wordpress_core","themes","plugins","uploads")]
  extract=" && ".join("tar -xzf /artifacts/"+shlex.quote(n)+" -C /site" for n in names)
  call(["docker","run","--rm","--pull=never","--network","none",
        "-v",project+"_site:/site","-v",str(bundle)+":/artifacts:ro","--entrypoint","sh",wp,
        "-c",extract+" && chown -R www-data:www-data /site"])
  with gzip.open(assets["database"],"rb") as sql:
   import shutil
   importer=subprocess.Popen(cli+["exec","-T","db","sh","-c",
       'MYSQL_PWD="$MARIADB_PASSWORD" exec mariadb -u "$MARIADB_USER" "$MARIADB_DATABASE"'],stdin=subprocess.PIPE)
   try:
    shutil.copyfileobj(sql,importer.stdin)
   finally:
    importer.stdin.close()
   assert importer.wait()==0,"SQL import failed"
  call(cli+["up","-d","--wait","--wait-timeout","150","source"])
  actual=json.loads(call(cli+["exec","-T","source","php","/verify/verify.php"],capture_output=True,text=True).stdout)
  expected=json.loads((bundle/"bootstrap/baseline.json").read_text());assert actual["passed"]
  for field in ("database_baseline","upload_inventory","ids","environment"):
   assert actual[field]==expected[field],field+" differs"
  (out/"restored-baseline.json").write_text(json.dumps(actual,ensure_ascii=False,indent=2)+"\n")
  call(cli+["exec","-T","source","php","/verify/reset-admin.php"],stdout=subprocess.DEVNULL)
  call(cli+["up","-d","preview"])
  import urllib.request
  for _ in range(30):
   try:
    with urllib.request.urlopen("http://127.0.0.1:18081/healthz",timeout=2) as response:
     if response.status==200:break
   except Exception:time.sleep(1)
  call(["python3",str(bundle/"bootstrap/verify-http.py"),str(bundle/"bootstrap"),str(env),str(out)])
  http=json.loads((out/"http.json").read_text());assert http["passed"]
  states=json.loads(call(["docker","inspect",project+"-source-1",project+"-db-1"],capture_output=True,text=True).stdout)
  assert all(not m["Name"].startswith("owr-m1_source") for state in states for m in state["Mounts"] if m["Type"]=="volume")
  networks=json.loads(call(["docker","network","inspect",project+"_recovery"],capture_output=True,text=True).stdout)
  assert networks[0]["Internal"]
  report.update(passed=True,baseline_checks=len(actual["checks"]),http_checks=len(http["checks"]),
                strict_baseline_fields_matched=4,independent_volumes=True,network_internal=True)
 except Exception as error:
  report["error_type"]=type(error).__name__;raise
 finally:
  report["finished_at"]=now()
  (out/"result.json").write_text(json.dumps(report,indent=2)+"\n")
 if a.run==1:call(cli+["stop"])
 print(json.dumps(report))
if __name__=="__main__":main()