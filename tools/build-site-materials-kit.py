"""Small explicit experimental distribution; excludes legacy UIs and whole-DB recovery."""
import argparse,hashlib,json,stat,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/SiteReconstructionAdmin.php','assets/site-reconstruction.js','tools/site-reconstruction-worker.py','tools/site-reconstruct-private.py','tools/run-site-materials-lab.py','docs/site-reconstruction-console.md','src/SiteMaterialsProjection.php','src/SiteMaterialsEditor.php','assets/site-materials-editor.js','tools/site-editor-worker.py','tools/site-materials.py','tools/site-materials-command.py','tools/site-wordpress-apply.php','tools/rbr-generation-kit.py','tools/rbr-s3-kit.py','tools/queue-s3-adapter.py','tools/lab-s3-request.py','docs/site-materials-v1.md','docs/site-materials-v1-jp.md','docs/legacy-transfer-inventory.md','LICENSE']
def build(path):
    if path.exists():raise ValueError('Output exists')
    records={}
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            p=ROOT/name
            if p.is_symlink():raise ValueError('Symlink source')
            raw=p.read_bytes();records[name]=hashlib.sha256(raw).hexdigest();i=zipfile.ZipInfo('owr-site-materials/'+name,(2026,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=(stat.S_IFREG|0o644)<<16;z.writestr(i,raw)
        z.writestr('owr-site-materials/MANIFEST.json',json.dumps({'experimental':True,'wordpress_installable':False,'files':records},indent=2))
    print(json.dumps({'file':str(path),'files':len(FILES),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output)
