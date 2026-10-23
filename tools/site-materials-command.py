"""Explicit CLI for the experimental S3 scope. Does not modify WordPress or publish."""
import argparse,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('materials','site-materials.py');k=load('kit','rbr-generation-kit.py')
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['save','receive']);p.add_argument('--work',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--operation');p.add_argument('--parent',type=Path);p.add_argument('--scope',type=Path);a=p.parse_args()
    if a.output.exists():p.error('Output must be new; preserve existing receipts')
    value=json.loads(a.input.read_bytes())
    if a.action=='save':
        if not a.operation or not a.scope:p.error('Save requires operation and fixed experimental scope file')
        prefix=json.loads(a.scope.read_bytes())['prefix']
        import re
        if not re.fullmatch('sites/isolated-queue-lab/sets/AWS-[a-f0-9]{16}/',prefix):p.error('Existing experimental permissions only')
        parent=json.loads(a.parent.read_bytes()) if a.parent else None
        result=m.Repository(k.LiveStore(a.work/'writer'),a.work/'journal',prefix).save(a.operation,parent,value)
    else:result=m.receive(k.LiveStore(a.work/'reader'),value)
    a.output.write_bytes(m.canon(result));print(json.dumps({'state':'saved' if a.action=='save' else 'received','output':str(a.output),'wordpress_changed':False}))
if __name__=='__main__':main()
