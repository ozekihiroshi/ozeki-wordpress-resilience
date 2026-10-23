"""Opt-in generated-data reconstruction queue. No signing, approval renewal or publication.
Config and outcome directory must be inaccessible for writes by WordPress.
Only the inbox is writable by WordPress; report is a read-only mount there.
"""
import argparse, fcntl, hashlib, importlib.util, json, os, re, time, traceback
from pathlib import Path

def load_executor():
    spec=importlib.util.spec_from_file_location('approved_console',Path(__file__).with_name('rbr-approved-kit.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def atomic(path,data):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True));os.replace(tmp,path)
def args(item):return [Path(item[n]) for n in ('trust','approval','signature','receipt')]+[item['site_id'],item['set_id']]
def token(item):return digest(json.dumps(item,sort_keys=True).encode()+Path(item['approval']).read_bytes()+Path(item['receipt']).read_bytes())
def identify(item,executor):
    executor.verify(*args(item))
    work=Path(item['work']);executor.verify_received(work,Path(item['receipt']))
    definition=read(work/'bundle/definition.json')
    # Selection is operator-owned; exact generation identity, not sequence number alone.
    if definition['assets_ref']!=item['generation']:raise ValueError('Generation mismatch')
    if item.get('q_sha256') is not None and definition['expected_ref']['sha256']!=item['q_sha256']:raise ValueError('Request Q mismatch')
    return {'generation':definition['assets_ref'],'q_sha256':definition['expected_ref']['sha256'],
            'expires_at':read(item['approval'])['expires_at']}

def cycle(config,executor):
    inbox=Path(config['inbox']);state=Path(config['state']);items=[]
    for item in config['items']:
        name=item['item_id']
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',name):raise ValueError('Invalid configured item')
        public={'item_id':name,'origin':item['origin'],'approval':'unconfirmed','public_activation':False,'require_local_match':item.get('require_local_match',False)}
        try:
            t=token(item);public['token']=t
            public.update(identify(item,executor));public['approval']='approved'
        except Exception:
            public['approval']='blocked';public['reason']='Signature, current trust, expiry or kit verification did not pass'
        t=public.get('token','');rid=digest((name+':'+t).encode());journal=state/(rid+'.json');request=inbox/(rid+'.json')
        if journal.exists():
            result=read(journal)
            if result['state']=='running':
                result={'state':'interrupted','request_id':rid,'reason':'Previous execution did not finish; operator review required'};atomic(journal,result)
            public['result']=result
        elif request.exists() or request.is_symlink():
            try:
                fd=os.open(request,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                import stat
                try:
                    if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('Not regular')
                    raw=os.read(fd,1025)
                finally:os.close(fd)
                if len(raw)>1024 or json.loads(raw)!={'item_id':name,'token':t}:raise ValueError('Request mismatch')
                if public['approval']!='approved':raise ValueError('Approval blocked')
                identify(item,executor)
                if token(item)!=t:raise ValueError('Selection changed')
                public['result']={'state':'running','request_id':rid};atomic(journal,public['result'])
                # A running report ages naturally: stopped worker cannot appear healthy.
                atomic(config['report'],{'schema':'owr-reconstruction-console-v1','updated_at':int(time.time()),'items':items+[public]})
                output=state/('execution-'+rid)
                executor.execute(*args(item),Path(item['work']),output,received=True)
                public['result']={'state':'verified','request_id':rid,'q_match':True,'public_activation':False}
            except Exception:
                traceback.print_exc()
                public['result']={'state':'failed','request_id':rid,'reason':'Execution refused or failed; inspect operator logs; no automatic retry'}
            atomic(journal,public['result'])
        items.append(public)
    report={'schema':'owr-reconstruction-console-v1','updated_at':int(time.time()),'items':items}
    atomic(config['report'],report);return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--once',action='store_true');p.add_argument('--allow-disposable-lab',action='store_true');a=p.parse_args()
    if not a.allow_disposable_lab:p.error('Generated-data lab opt-in required')
    config=read(a.config)
    if config.get('schema')!='owr-reconstruction-console-config-v1':raise ValueError('Config schema')
    for name in ('inbox','state'):
        path=Path(config[name]);path.mkdir(parents=True,exist_ok=True)
        if path.is_symlink():raise ValueError('Symlink directory')
    inbox=Path(config['inbox']).resolve()
    for path in [a.config,Path(config['state']),Path(config['report'])]+[Path(i[n]) for i in config['items'] for n in ('trust','approval','signature','receipt','work')]:
        if path.resolve().is_relative_to(inbox):raise ValueError('Trusted inputs cannot be inside inbox')
    lock=open(Path(config['state'])/'worker.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    executor=load_executor()
    while True:
        cycle(config,executor)
        if a.once:break
        time.sleep(15)
if __name__=='__main__':main()
