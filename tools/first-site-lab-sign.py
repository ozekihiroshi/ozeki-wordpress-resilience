"""Explicit disposable operator approval for generated first-site lab candidates."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--operator',type=Path,required=True);a=p.parse_args()
    os.umask(0o077)
    m=json.loads(a.candidate.read_bytes())
    if m['format']!='owr-protected-first-site-set-v1' or m['paired']['site_id']!='generated-first-site' or m['site_id']!='isolated-queue-lab':raise ValueError('not generated lab candidate')
    if a.operator.resolve().is_relative_to(a.candidate.parent.resolve()):raise ValueError('operator must be outside publisher')
    a.operator.mkdir(mode=0o700,parents=True,exist_ok=False)
    doc=a.operator/'approved.json';doc.write_bytes(a.candidate.read_bytes())
    with tempfile.TemporaryDirectory(dir=a.operator) as tmp:
        key=Path(tmp)/'private.pem'
        for cmd in [['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],['openssl','pkey','-in',str(key),'-pubout','-out',str(a.operator/'public.pem')],['openssl','dgst','-sha256','-sign',str(key),'-out',str(a.operator/'approved.sig'),str(doc)]]:
            subprocess.run(cmd,check=True,capture_output=True,timeout=30)
    pin={'status':'active','site_id':m['site_id'],'set_id':m['set_id'],'minimum_sequence':1,'bucket':m['assets'][0]['locator']['bucket'],'region':m['assets'][0]['locator']['region'],'writer_identity':'my-ssm-role','reader_identity':'OwrM1RecoveryReader','public_key_sha256':hashlib.sha256((a.operator/'public.pem').read_bytes()).hexdigest(),'approved_document_sha256':hashlib.sha256(doc.read_bytes()).hexdigest(),'envelope':{}}
    (a.operator/'pin.json').write_text(json.dumps(pin,indent=2))
if __name__=='__main__':main()
