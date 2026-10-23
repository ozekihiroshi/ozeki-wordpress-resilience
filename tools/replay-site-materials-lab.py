"""Read existing generated S3 generations; exercise sequential private projection, no PUT."""
import argparse,importlib.util,json
from pathlib import Path
s=importlib.util.spec_from_file_location('lab',Path(__file__).with_name('run-site-materials-lab.py'));l=importlib.util.module_from_spec(s);s.loader.exec_module(l)
def replay(source,output):
    scope=json.loads((source/'scope.json').read_bytes())
    if scope.get('generated_only') is not True:raise ValueError('Generated lab scope required')
    output.mkdir(mode=0o700,exist_ok=False);reader=l.k.LiveStore(output/'reader');sequence=[]
    for i,ref in enumerate(json.loads((source/'receipts.json').read_bytes())):
        sequence.append(l.m.receive(reader,ref));print(json.dumps({'received_for_projection':i+1}),flush=True)
    bundle=output/'bundle';bundle.mkdir();(bundle/'received.json').write_bytes(l.m.canon(sequence[0]));images=json.loads((source/'result.json').read_bytes())['runtime_images']
    result=l.trial_target(output/'target',bundle,images['wordpress'],images['database'],sequence);(output/'result.json').write_bytes(l.m.canon(result));print(json.dumps(result))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-disposable-lab',action='store_true');a=p.parse_args()
    if not a.allow_disposable_lab:p.error('Explicit private lab opt-in required')
    replay(a.source,a.output)
