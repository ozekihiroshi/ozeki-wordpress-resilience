"""New multi-material schema only. Read-only storage, fixed-profile reconstruction queue."""
import argparse,fcntl,hashlib,importlib.util,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('site_worker',ROOT/'site-editor-worker.py');w=importlib.util.module_from_spec(s);s.loader.exec_module(w);m=w.m

def profile(c):
    return m.sha(m.canon({k:c[k] for k in ('target_label','wordpress_image','database_image','recovery_work')}))
def execute(c,bundle,target):
    with (bundle/'execution.log').open('wb') as log:
        subprocess.run(['python3',str(ROOT/'site-reconstruct-private.py'),'--bundle',str(bundle),'--output',str(target),'--wordpress-image',c['wordpress_image'],'--database-image',c['database_image'],'--allow-dedicated-target'],check=True,stdout=log,stderr=log,timeout=900)
    return json.loads((target/'result.json').read_bytes())
def cycle(c,executor=execute):
    bridge=Path(c['bridge'])/'reconstruction';requests=bridge/'requests';requests.mkdir(parents=True,exist_ok=True)
    work=Path(c['recovery_work']);work.mkdir(parents=True,exist_ok=True);jobs=work/'jobs';jobs.mkdir(exist_ok=True)
    with (work/'worker.lock').open('a+b') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        reader_config=dict(c,work=str(work/'reader')) if c['transport']=='experimental-s3' else c
        store=w.store(reader_config);items=[];records={};errors=0
        cache=work/'catalog';cache.mkdir(exist_ok=True)
        context=m.sha(m.canon({k:c[k] for k in ('transport','work','prefix')}))
        for p in sorted((p for p in (Path(c['work'])/'journal').glob('*.json') if p.name!='head.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:50]:
            if p.name=='head.json':continue
            op=json.loads(p.read_bytes())
            if op.get('state')!='committed' or not op.get('receipt'):continue
            ref=op['receipt'];ident=ref['sha256']
            try:
                cachefile=cache/(m.sha(m.canon({'context':context,'receipt':ref}))+'.json')
                try:cached=json.loads(cachefile.read_bytes())
                except (OSError,ValueError):cached=None
                now=time.time()
                if cached and cached.get('receipt')==ref and 0<=now-cached.get('checked_at',0)<3600 and now<cached.get('protect_until',0):
                    entry=dict(cached,operation=p.stem,catalog_cached=True)
                    records[ident]=ref;items.append(entry);continue
                received=m.receive(store,ref);q=m.sha(m.canon(received['expected']))
                entry={'id':ident,'operation':p.stem,'receipt':ref,'q':q,'summary':[{'id':x['id'],'kind':x['kind'],'title':x.get('title',x.get('alt',''))} for x in received['expected']['entries']],'assets':len(received['site']['entries']),'title':received['site']['title'],'eligible':True}
                entry.update(checked_at=int(time.time()),protect_until=received['protect_until'],catalog_cached=False)
                m.atomic(cachefile,entry)
                records[ident]=ref
            except Exception:
                errors+=1;entry={'id':ident,'operation':p.stem,'receipt':ref,'eligible':False,'reason':'generation-verification-failed'}
            items.append(entry)
        state={'schema':'owr-site-reconstruction-v1','updated_at':int(time.time()),'profile':profile(c),'target':c['target_label'],'items':items,'jobs':[],'verification_failures':errors}
        def publish():
            state['updated_at']=int(time.time());state['jobs']=[json.loads(p.read_bytes()) for p in sorted(jobs.glob('*.json'))];m.atomic(bridge/'status.json',state)
        # A worker restart must never blindly rerun an interrupted target creation.
        for p in jobs.glob('*.json'):
            job=json.loads(p.read_bytes())
            if job['state']=='running':job.update(state='interrupted',reason='inspect-private-target-before-retry');m.atomic(p,job)
        publish()
        for request in sorted(requests.glob('*.json')):
            q=json.loads(request.read_bytes());ident=q.get('generation');token=q.get('job')
            if not isinstance(token,str) or not re.fullmatch('[a-f0-9]{64}',token):continue
            path=jobs/(token+'.json')
            if path.exists():continue
            job={'job':token,'generation':ident,'q':q.get('q'),'state':'running','started_at':int(time.time())}
            try:
                m.require(set(q)=={'job','generation','q','profile'},'Request fields')
                m.require(q['profile']==profile(c) and ident in records,'Generation/profile mismatch')
                m.require(token==m.sha(m.canon({'generation':ident,'q':q['q'],'profile':q['profile']})),'Job identity')
                # Fetch again immediately before execution; catalog is not authorization.
                received=m.receive(store,records[ident]);m.require(m.sha(m.canon(received['expected']))==q['q'],'Q changed')
                m.atomic(path,job);publish()
                bundle=work/('input-'+token);bundle.mkdir(exist_ok=False);m.atomic(bundle/'received.json',received)
                result=executor(c,bundle,work/('target-'+token))
                m.require(result['state']=='verified-private' and result['logical_sha256']==q['q'] and result['side_effect_attempts']==0 and not result['public_activation'],'Result does not match requested Q')
                job.update(state='verified',result=result)
            except Exception:
                job.update(state='failed',reason='verification-or-target-failed-inspect-records')
            job['finished_at']=int(time.time());m.atomic(path,job);publish()
        return state
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--once',action='store_true');a=p.parse_args();c=json.loads(a.config.read_bytes())
    while True:
        cycle(c)
        if a.once:break
        time.sleep(5)
