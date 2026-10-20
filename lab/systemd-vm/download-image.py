import os
import hashlib,json,urllib.request
from pathlib import Path
base='https://cloud-images.ubuntu.com/noble/20261017/'
name='noble-server-cloudimg-amd64.img'
out=Path.home()/'.local/share/owr-vm-images'
out.mkdir(parents=True,exist_ok=True)
sums=urllib.request.urlopen(base+'SHA256SUMS',timeout=60).read().decode()
expected=next(line.split()[0] for line in sums.splitlines() if line.split()[-1].lstrip('*')==name)
dest=out/name
if not dest.exists():
    temp=out/(name+'.partial')
    with urllib.request.urlopen(base+name,timeout=60) as r,temp.open('wb') as f:
        while b:=r.read(1024*1024):f.write(b)
    assert hashlib.file_digest(temp.open('rb'),'sha256').hexdigest()==expected
    temp.rename(dest)
assert hashlib.file_digest(dest.open('rb'),'sha256').hexdigest()==expected
(out/'image-source.json').write_text(json.dumps(dict(url=base+name,sha256=expected,bytes=dest.stat().st_size),indent=2))
print((out/'image-source.json').read_text())
