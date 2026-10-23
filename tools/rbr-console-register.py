"""Register an approved received kit for the exact applied editor receipt. Never signs or renews."""
import argparse,importlib.util,json,re
from pathlib import Path

def bind(save,definition,root):
    if save.get('state')!='applied' or type(save.get('sequence')) is not int or save['sequence']<1:raise ValueError('Applied editor receipt required')
    if not save.get('expected_ref') or root.get('schema')!='owr-rbr-s3-kit-v2':raise ValueError('Request-bound Q required')
    if definition['assets_ref']!=save['generation'] or root.get('expected_binding_ref')!=save['expected_ref']:raise ValueError('Different editor generation or bound Q')
    return definition['expected_ref']['sha256']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('save-receipt','received','trust','approval','signature','receipt','inbox','report','state','output'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('item-id','site-id','set-id'):p.add_argument('--'+n,required=True)
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',a.item_id):raise ValueError('Item identity')
    spec=importlib.util.spec_from_file_location('console',Path(__file__).with_name('rbr-console-worker.py'));worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker);executor=worker.load_executor()
    save=worker.read(a.save_receipt)
    item={'item_id':a.item_id,'origin':'Current protected editor: exact saved generation and request-derived Q','require_local_match':True,'site_id':a.site_id,'set_id':a.set_id,'generation':save['generation'],'work':str(a.received.resolve()),**{n:str(getattr(a,n).resolve()) for n in ('trust','approval','signature','receipt')}}
    worker.identify(item,executor)
    item['q_sha256']=bind(save,worker.read(a.received/'bundle/definition.json'),worker.read(a.received/'root-manifest.json'))
    config={'schema':'owr-reconstruction-console-config-v1','items':[item],**{n:str(getattr(a,n).resolve()) for n in ('inbox','report','state')}}
    raw=json.dumps(config,sort_keys=True,indent=2)
    with a.output.open('x') as f:f.write(raw)
    print('Exact editor generation registered; no reconstruction or publication started')
if __name__=='__main__':main()
