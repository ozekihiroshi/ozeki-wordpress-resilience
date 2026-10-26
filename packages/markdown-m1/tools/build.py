"""Build the current Ozeki Resilience product for WordPress.org."""
from pathlib import Path
import hashlib,json,sys,zipfile
root=Path(__file__).resolve().parents[1];vendor=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve()
assert (vendor/'autoload.php').is_file()
assert not output.exists(), 'Use a new output filename; preserve earlier evidence'
files=[root/x for x in ['ozeki-wordpress-resilience.php','README.md','RAADME-jp.md','readme.txt','LICENSE','composer.json','composer.lock']]
files+=list((root/'src').glob('*.php'))
files+=sorted(f for f in (root/'docs').rglob('*') if f.is_file())
output.parent.mkdir(parents=True,exist_ok=True)
def add(z,file,name):
 info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
 z.writestr(info,file.read_bytes())
with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
 for file in sorted(files):add(z,file,'ozeki-resilience/'+file.relative_to(root).as_posix())
 for file in sorted(vendor.rglob('*')):
  if file.is_file():add(z,file,'ozeki-resilience/vendor/'+file.relative_to(vendor).as_posix())
with zipfile.ZipFile(output) as z:
 assert all('/tests/'not in p and '/lab/'not in p and '/tools/'not in p.replace('/vendor/','/vendor-ignore/') for p in z.namelist() if '/vendor/'not in p)
manifest={'zip':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'product_files':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
