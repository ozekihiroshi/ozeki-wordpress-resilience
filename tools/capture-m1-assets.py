#!/usr/bin/env python3
"""Capture synthetic M1 assets locally; no cloud operations."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
BASE = ["docker", "compose", "--project-name", "owr-m1", "--env-file",
        ".local/runtime.env", "-f", "lab/m1/compose.yml"]
def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
def call(args, **kw):
    return subprocess.run(args, cwd=ROOT, check=True, **kw)
def main():
    os.umask(0o077)
    identifier = "CAP-M1-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    destination = ROOT / ".local/captures" / identifier
    destination.mkdir(parents=True)
    report = {"evidence_id": identifier, "kind": "E1", "site_id": "owr-m1-synthetic",
              "actor": "local-wsl-operator", "started_at": now(), "result": "incomplete",
              "method": "pinned-plugin-php-dumper-and-tar",
              "scope": "local capture only; no external storage or authenticity claim",
              "consistency": "uncoordinated", "assets": [],
              "plugin_commit": "627e47c2b31527ef1486e582b79fd5dba875843f"}
    stopped = False
    def stream(args, path, compressed=False):
        with path.open("xb") as target:
            process = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                out = gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) if compressed else target
                while block := process.stdout.read(1024*1024):
                    out.write(block)
                if compressed:
                    out.close()
                # bounded fixture operations; never print SQL or credential-bearing output
                errors = process.stderr.read()
                if process.wait() != 0:
                    raise RuntimeError("capture subprocess failed")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
    def record(role, path):
        sha=hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda:f.read(1024*1024),b""):
                sha.update(block)
        report["assets"].append({"role":role,"path":str(path.relative_to(ROOT)),
                                 "size_bytes":path.stat().st_size,"sha256":sha.hexdigest()})
    try:
        status = call(BASE+["ps","--status","running","--services"],capture_output=True,text=True).stdout.split()
        if not {"source","source-db","preview"}.issubset(status):
            raise RuntimeError("source, database and preview must be running")
        call(BASE+["stop","preview"],stdout=subprocess.DEVNULL)
        stopped = True
        report["http_ingress_stopped_at"]=now()
        dump=destination/"database.sql.gz"
        stream(BASE+["exec","-T","source","php","/fixture/capture-database.php"],dump,True)
        with gzip.open(dump,"rb") as f:
            sql=f.read(32*1024*1024+1)
        if not sql or len(sql)>32*1024*1024 or b"owr_posts" not in sql:
            raise RuntimeError("unexpected synthetic database dump")
        record("database",dump)
        groups = {
            "uploads":["wp-content/uploads"],
            "themes":["wp-content/themes"],
            "plugins":["wp-content/plugins","wp-content/mu-plugins"],
            "wordpress_core":["wp-admin","wp-includes","index.php","wp-activate.php",
                "wp-blog-header.php","wp-comments-post.php","wp-cron.php","wp-links-opml.php",
                "wp-load.php","wp-login.php","wp-mail.php","wp-settings.php","wp-signup.php",
                "wp-trackback.php","xmlrpc.php",".htaccess"]}
        for role, names in groups.items():
            path=destination/(role+".tar.gz")
            stream(BASE+["exec","-T","source","tar","-czf","-","-C","/var/www/html"]+names,path)
            with tarfile.open(path) as archive:
                for member in archive:
                    if member.issym() or member.islnk() or member.isdev() or member.name.startswith("/") or ".." in Path(member.name).parts:
                        raise RuntimeError("unsupported archive member")
            record(role,path)
        path=destination/"configuration.tar.gz"
        with tarfile.open(path,"x:gz") as archive:
            for name in ["lab/m1/compose.yml","lab/m1/images.env","lab/m1/images.lock.json",
                         "lab/m1/preview.conf","lab/m1/fixture/guard.php"]:
                archive.add(ROOT/name,arcname=name,recursive=False)
        record("configuration",path)
        record("runtime_wordpress",ROOT/".local/images/wordpress-phase1.tar")
        report["result"]="captured_locally"
    except Exception as exc:
        report["result"]="failed"
        report["error_type"]=type(exc).__name__
        raise
    finally:
        if stopped:
            try:
                call(BASE+["start","preview"],stdout=subprocess.DEVNULL)
                report["http_ingress_resumed_at"]=now()
            except Exception:
                report["result"]="failed"
                report["resume_failed"]=True
        report["finished_at"]=now()
        (destination/"capture.json").write_text(json.dumps(report,indent=2)+"\n")
        evidence=ROOT/"evidence/m1/e1"
        evidence.mkdir(parents=True,exist_ok=True)
        (evidence/(identifier+".json")).write_text(json.dumps(report,indent=2)+"\n")
    if report["result"] != "captured_locally":
        raise RuntimeError("capture or source resume failed")
    print(json.dumps({"capture_id":identifier,"result":report["result"],
                      "asset_count":len(report["assets"]),
                      "total_bytes":sum(a["size_bytes"] for a in report["assets"])},indent=2))
if __name__ == "__main__":
    main()