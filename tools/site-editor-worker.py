"""Single worker for a dedicated editor. Never applies WordPress or publishes content."""
import argparse,base64,fcntl,importlib.util,json,os,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('materials_worker','site-materials.py');k=load('kit_worker','rbr-generation-kit.py')
class LabStore:
    def __init__(self,root):self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
    def put(self,raw,key):
        path=self.root/(m.sha(key.encode())+'.json')
        if path.exists():
            old=json.loads(path.read_bytes());m.require(base64.b64decode(old['raw'])==raw,'Immutable key conflict')
        else:
            old={'raw':base64.b64encode(raw).decode(),'until':int(time.time())+36*86400,'stored':int(time.time())};m.atomic(path,old)
        return {'locator':{'kind':'s3','bucket':'dedicated-editor-double','region':'ap-northeast-1','key':key,'version_id':m.sha(raw)},'sha256':m.sha(raw),'size_bytes':len(raw)}
    def get(self,ref):
        old=json.loads((self.root/(m.sha(ref['locator']['key'].encode())+'.json')).read_bytes());raw=base64.b64decode(old['raw']);m.require(m.sha(raw)==ref['sha256'] and len(raw)==ref['size_bytes'],'Fixed version mismatch');return raw,old['until'],old['stored']
def store(config):
    if config['transport']=='filesystem-lab':return LabStore(Path(config['work'])/'objects')
    if config['transport']=='experimental-s3':return k.LiveStore(Path(config['work'])/'s3')
    raise ValueError('Dedicated transport required')
def process(config,hook=None):
    work=Path(config['work']);work.mkdir(parents=True,exist_ok=True);bridge=Path(config['bridge']);transport=store(config)
    with (work/'worker.lock').open('a+b') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        for path in sorted((bridge/'requests').glob('*.json')):
            q=json.loads(path.read_bytes());op=q['operation'];m.require(__import__('re').fullmatch('editor-[a-f0-9]{32}',op),'Operation ID')
            m.require(type(q['attempt']) is int and 0<q['attempt']<10000,'Attempt bound')
            digest=m.sha(m.canon({'parent':q['parent'],'site':q['site']}));m.require(digest==q['request_sha256'],'Request identity')
            report=bridge/'reports'/(op+'.json');previous=json.loads(report.read_bytes()) if report.exists() else {}
            if previous.get('attempt',0)>q['attempt']:continue
            if previous.get('attempt')==q['attempt'] and previous.get('state')in ('stored','failed','blocked'):continue
            v={'operation':op,'attempt':q['attempt'],'request_sha256':digest,'state':'working','updated_at':int(time.time())};m.atomic(report,v)
            try:
                m.normalize(q['site'])
                if hook:hook('before_save')
                repo=m.Repository(transport,work/'journal',config['prefix']);ref=repo.save(op,q['parent'],q['site'])
                if hook:hook('after_save')
                received=m.receive(transport,ref);v.update(state='stored',received=received)
            except Exception as e:
                uncertain=False
                if config['transport']=='experimental-s3':uncertain=any(x['method']=='PUT' and x['state']!='acknowledged' for x in transport.store.adapter.operations)
                v.update(state='blocked' if uncertain else 'failed',reason='unresolved-storage' if uncertain else 'validation-or-save-failed')
            v['updated_at']=int(time.time());m.atomic(report,v)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--once',action='store_true');p.add_argument('--lab-control',type=Path);a=p.parse_args();c=json.loads(a.config.read_bytes())
    def hook(stage):
        v=json.loads(a.lab_control.read_bytes()) if a.lab_control and a.lab_control.exists() else {}
        if stage=='before_save' and v.get('fail_before'):raise RuntimeError('Injected before any PUT')
        if stage=='after_save' and v.get('stop_after_store'):raise SystemExit(77)
    while True:
        process(c,hook)
        if a.once:break
        time.sleep(1)
