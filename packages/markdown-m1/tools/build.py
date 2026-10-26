"""Build only the independent M1 product; preserve the research distribution unchanged."""
from pathlib import Path
import hashlib,json,sys,zipfile
root=Path(__file__).resolve().parents[1];vendor=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]).resolve()
assert (vendor/'autoload.php').is_file()
assert not output.exists(), 'Use a new output filename; preserve earlier evidence'
files=[root/x for x in ['ozeki-wordpress-resilience.php','README.md','RAADME-jp.md','LICENSE','composer.json','composer.lock']]
files+=list((root/'src').glob('*.php'))
files+=sorted(f for f in (root/'docs').rglob('*') if f.is_file())
output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
 for file in files:z.write(file,'ozeki-wordpress-resilience/'+file.relative_to(root).as_posix())
 for file in vendor.rglob('*'):
  if file.is_file():z.write(file,'ozeki-wordpress-resilience/vendor/'+file.relative_to(vendor).as_posix())
with zipfile.ZipFile(output) as z:
 assert all('/tests/'not in p and '/lab/'not in p and '/tools/'not in p.replace('/vendor/','/vendor-ignore/') for p in z.namelist() if '/vendor/'not in p)
manifest={'zip':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'product_files':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
output.with_suffix('.manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest))
