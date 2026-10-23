#!/usr/bin/env python3
"""Build two explicit development distributions; no network or credentials."""
import argparse,hashlib,json,re,stat,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.0-alpha.4'
PLUGIN=['ozeki-wordpress-resilience.php','src/NotificationAdmin.php','src/ObserverAdmin.php','src/DailyAdmin.php','src/DailyWatchdogAdmin.php','src/PreflightAdmin.php','src/PreflightWatchdogAdmin.php','src/ObserverSettings.php','readme.txt','LICENSE']
DIRS=['assets','src','tools','tests','schemas','examples','lab','docs','packages','evidence-public']
TOP=['README.md','RAADME-jp.md','readme.txt','LICENSE','THIRD_PARTY_NOTICES.md','composer.json','composer.lock','requirements-dev.txt','ozeki-wordpress-resilience.php']
EXT={'.php','.py','.md','.json','.sh','.ps1','.txt','.yml','.yaml','.ini','.conf','.sql','.js','.css','.html','.service','.timer','.toml','.Dockerfile','.png'}
SECRET=re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}\b')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def build(output):
 output=Path(output);output.mkdir(parents=True,exist_ok=False)
 files=set(TOP)
 for folder in DIRS:
  for p in (ROOT/folder).rglob('*'):
   if any(x in ('__pycache__','.local','vendor','.git') for x in p.relative_to(ROOT).parts):continue
   if p.is_file() and (p.suffix in EXT or p.name in ('Dockerfile','LICENSE','images.env','Dockerfile.external')):files.add(p.relative_to(ROOT).as_posix())
 if 'Version: '+VERSION not in (ROOT/PLUGIN[0]).read_text():raise ValueError('version mismatch')
 records=[]
 for name,paths,prefix in [('ozeki-wordpress-resilience',PLUGIN,'ozeki-wordpress-resilience'),('owr-development-kit',sorted(files),'owr-development-kit')]:
  target=output/(name+'-'+VERSION+'.zip');entries={}
  with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for rel in sorted(paths):
    path=ROOT/rel
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):raise ValueError('unsafe source path')
    raw=path.read_bytes()
    if SECRET.search(raw):raise ValueError('secret pattern in '+rel)
    info=zipfile.ZipInfo(prefix+'/'+rel,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|0o644)<<16
    z.writestr(info,raw);entries[rel]=digest(raw)
  records.append(dict(file=target.name,sha256=digest(target.read_bytes()),bytes=target.stat().st_size,files=entries))
 manifest=dict(format='owr-development-distributions-v1',version=VERSION,production_ready=False,artifacts=records)
 (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({x['file']:dict(sha256=x['sha256'],files=len(x['files']),bytes=x['bytes']) for x in records},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();build(a.output)
