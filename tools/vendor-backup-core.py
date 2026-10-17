#!/usr/bin/env python3
"""Verify or generate a pinned distribution copy; never edit that copy manually."""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--target',required=True);p.add_argument('--check',action='store_true');a=p.parse_args()
 source=ROOT/'packages/backup-core';target=Path(a.target).resolve()
 if not (target/'composer.json').is_file():raise SystemExit('Target must be an existing product root')
 dest=target/'libs/backup-core';manifest=dest/'distribution.json'
 files={x.relative_to(source).as_posix():digest(x) for x in source.rglob('*') if x.is_file()}
 old=json.loads(manifest.read_text()) if manifest.exists() else None
 if dest.exists() and not old:raise SystemExit('Refusing unmanaged destination')
 if old:
  actual={x.relative_to(dest).as_posix():digest(x) for x in dest.rglob('*') if x.is_file() and x!=manifest}
  if actual!=old['files']:raise SystemExit('Generated component has local changes; refusing overwrite')
 if a.check:
  if not old or old['files']!=files:raise SystemExit('Distribution differs from canonical source')
  print('Pinned component verified');return
 if old and set(old['files'])-set(files):raise SystemExit('File removals require an explicit migration')
 dest.mkdir(parents=True,exist_ok=True)
 for name in files:
  out=dest/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,out)
 manifest.write_text(json.dumps({'package':'ozeki/backup-core','version':'0.1.0','source':'https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/codex/shared-backup-core/packages/backup-core','files':files},indent=2)+'\n')
 print('Generated pinned component:',len(files),'files')
if __name__=='__main__':main()
