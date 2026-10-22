import importlib.util,json,tempfile,secrets,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("runtime",root/"tools/same-host-runtime.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def run(*args):return subprocess.check_output(args,timeout=30)
def main():
    images=dict(x.split("=",1) for x in (root/"lab/m1/images.env").read_text().splitlines() if "=" in x)
    ids=[]
    with tempfile.TemporaryDirectory(prefix="owr-pair-contract-") as tmp:
        p=Path(tmp);env=p/"env";env.write_text("MARIADB_ROOT_PASSWORD=generated-only\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD=generated-only\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD=generated-only\n")
        token=secrets.token_hex(16)
        try:
            c=dict(format=m.FORMAT,workspace=str(p),production_paths=[],token=token)
            for role,key in [("db","OWR_DB_IMAGE"),("web","OWR_WP_IMAGE")]:
                image=json.loads(run("docker","image","inspect",images[key]))[0]["Id"]
                ident=run(*m.create_args(role,"owr-pair-check-"+token+"-"+role,image,token,env,c.get("db_id"))).decode().strip()
                ids.append(ident);c[role+"_id"]=ident;c[role+"_image"]=image
            result=m.assess(c)
            assert not result["issues"],result
            cfg=p/"pair.json";cfg.write_text(json.dumps(c))
            cli=json.loads(run("python3",str(root/"tools/same-host-preflight.py"),"--config",str(cfg)))
            assert not cli["issues"],cli
            assert all(m.base.inspect_container(i)["State"]["Status"]=="created" for i in ids)
            run("docker","start",c["db_id"])
            deadline=time.monotonic()+60
            while subprocess.run(["docker","exec",c["db_id"],"healthcheck.sh","--connect","--innodb_initialized"],capture_output=True).returncode:
                assert m.base.inspect_container(c["db_id"])["State"]["Running"],"DB exited"
                assert time.monotonic()<deadline,"DB timeout"
                time.sleep(1)
            assert not m.assess(c,phase="db_started")["issues"]
            run("docker","start",c["web_id"])
            deadline=time.monotonic()+60
            while subprocess.run(["docker","exec",c["web_id"],"test","-f","/var/www/html/wp-config.php"],capture_output=True).returncode:
                assert m.base.inspect_container(c["web_id"])["State"]["Running"],"Web exited"
                assert time.monotonic()<deadline,"Web timeout"
                time.sleep(1)
            assert not m.assess(c,phase="running")["issues"]
            for ident in ids:
                assert subprocess.run(["docker","exec",ident,"touch","/etc/owr-forbidden"],capture_output=True).returncode!=0
                net=run("docker","exec",ident,"cat","/proc/net/dev").decode()
                assert "eth0" not in net and "lo:" in net
            print(json.dumps({"prepared_cli":True,"db_started":True,"pair_running":True,
                              "root_writes_denied":True,"loopback_only":True}))
        finally:
            for ident in reversed(ids):run("docker","rm","-f","-v",ident)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Disposable generated-data pair contract lab; no production access")
    parser.add_argument("--execute-lab",action="store_true")
    args=parser.parse_args()
    if not args.execute_lab:
        parser.error("--execute-lab required")
    main()
