"""Build an approval-pending kit from an actual fixed S3 generation. No fixture generator."""
import fcntl
import argparse, datetime as dt, importlib.util, json, secrets, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rbr_kit',Path(__file__).with_name('rbr-s3-kit.py'))
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
CODE=['src/RbrGenerationCoordinator.php','src/RbrReconstructionPlanner.php','tools/rbr-wordpress-apply.php','tools/rbr-wordpress-observe.php','tools/rbr-compare.py','tools/rbr-reconstruct-lab.py','tools/rbr-plan.php','tools/rbr-planner-build.php']

def check(ok,message):
    if not ok:raise ValueError(message)

def definition(profile,generation):
    check(set(profile)=={'schema','site_id','rules_ref','environment_ref','comparison_ref','required_scope','expected_ref'},'Explicit profile fields required; no supplied assets/plan')
    check(profile['schema']=='owr-rbr-definition-profile-v1','Profile schema')
    return dict(profile,schema='owr-rbr-definition-v1',assets_ref=generation)

class LiveStore:
    def __init__(self,work):
        k.transport.authorize=lambda actor,**q:k.authorize(actor,retention_days=36,**q)
        self.store=k.Store(work)
    def get(self,ref):
        raw=self.store.get(ref)
        retention=self.store.adapter.operations[-1]['retention']
        return raw,dt.datetime.fromisoformat(retention['retain_until'].replace('Z','+00:00')).timestamp(),dt.datetime.fromisoformat(retention['last_modified']).timestamp()
    def put(self,raw,key):return self.store.put(raw,key)

class Builder:
    def __init__(self,store,work,prefix):
        self.store=store;self.work=work;self.prefix=prefix;self.seen={};self.active=set();self.total=0
        self.cache=work/'cache';self.cache.mkdir(exist_ok=True);self.evidence=[]
    def read(self,ref):
        # Store.get validates fixed locator, bytes, minimum duration and unexpired protection.
        ident=k.canonical(ref)
        if ident not in self.seen:
            check(len(self.seen)<500,'Closure object bound')
            raw,until,stored_at=self.store.get(ref);self.total+=len(raw)
            check(self.total<=1024**3,'Closure size bound')
            check(len(raw)==ref['size_bytes'] and k.sha(raw)==ref['sha256'],'Fixed bytes mismatch')
            self.seen[ident]=(raw,until,stored_at);(self.cache/(ref['sha256']+'.blob')).write_bytes(raw)
            self.evidence.append({'ref':ref,'retain_until_epoch':until,'stored_at_epoch':stored_at})
        return self.seen[ident]
    def walk(self,ref,horizon,preserve=False):
        ident=k.canonical(ref);check(ident not in self.active,'Cyclic closure');self.active.add(ident)
        try:
            raw,until,_=self.read(ref)
            try:value=json.loads(raw)
            except (ValueError,UnicodeError):value=None
            changed=False
            def rewrite(v):
                nonlocal changed
                if isinstance(v,dict):
                    if {'locator','size_bytes','sha256'}<=set(v):
                        target=self.walk(v,horizon,preserve);changed|=target!=v;return target
                    return {key:rewrite(item) for key,item in v.items()}
                if isinstance(v,list):return [rewrite(item) for item in v]
                return v
            rewritten=rewrite(value) if value is not None else None
            if preserve:
                check(not changed and until>=horizon,'Committed generation/dependency protection insufficient; do not rewrite the generation')
                return ref
            if changed:raw=k.canonical(rewritten)
            if changed or until<horizon:return self.put(raw,horizon)
            return ref
        finally:self.active.remove(ident)
    def put(self,raw,horizon):
        ref=self.store.put(raw,self.prefix+'rbr-'+k.sha(raw)+'.blob')
        actual,until,_=self.read(ref)
        check(actual==raw and until>=horizon,'New object protection below generation promise')
        return ref
    def execution_ref(self,raw,horizon):
        # The strict receiver uses one immutable reference per content digest.
        # Reuse a verified, sufficiently retained code reference already in E/C.
        for identity,(observed,until,_) in self.seen.items():
            if observed==raw and until>=horizon:
                return json.loads(identity)
        return self.put(raw,horizon)
    def prepare(self,generation,profile):
        d=definition(profile,generation);raw,until,stored_at=self.read(generation);a=json.loads(raw)
        check(a.get('schema')=='owr-rbr-generation-v1' and a.get('site_id')==profile['site_id'],'Generation/site mismatch')
        check(type(a.get('deadline')) is int and type(a.get('protect_until')) is int,'Generation times')
        check(stored_at<=a['deadline'],'Generation committed after deadline')
        horizon=a['protect_until'];now=dt.datetime.now(dt.timezone.utc).timestamp()
        check(horizon==a['deadline']+35*86400 and now<horizon<=now+36*86400,'Expired or unsupported generation horizon')
        check(type(a.get('sequence')) is int and a['sequence']>=1,'Generation sequence')
        # Parent manifests are historical provenance, not reconstruction dependencies. Their full
        # retention is currently required too; this bounded inlet intentionally fails closed.
        self.walk(generation,horizon,True)
        for field in ['rules_ref','environment_ref','comparison_ref','expected_ref']:
            d[field]=self.walk(profile[field],horizon)
        definition_path=self.work/'definition.json';definition_path.write_bytes(k.canonical(d))
        plan=self.work/'plan.json'
        if plan.exists():
            # Recompute into a new file on resume; do not trust a previous success flag.
            plan=self.work/('plan-'+secrets.token_hex(6)+'.json')
        subprocess.run(['php',str(ROOT/'tools/rbr-plan.php'),'--definition='+str(definition_path),'--objects='+str(self.cache),'--output='+str(plan)],check=True)
        p=json.loads(plan.read_bytes());check(p['environment_mode']=='pinned-runtime','Runnable pinned environment required')
        dref=self.put(definition_path.read_bytes(),horizon)
        code=[{'path':name,'ref':self.execution_ref((ROOT/name).read_bytes(),horizon)} for name in CODE]
        root={'schema':'owr-rbr-s3-kit-v1','definition_ref':dref,'code':code,'scope':'generated-corporate-site','public_activation':False}
        receipt=self.put(k.canonical(root),horizon)
        result={'state':'stored_awaiting_independent_approval','generation_ref':generation,'root_receipt':receipt,'protect_until':horizon,'plan_sha256':k.sha(plan.read_bytes()),'public_activation':False}
        (self.work/'root-receipt.json').write_bytes(k.canonical(receipt));(self.work/'result.json').write_bytes(k.canonical(result))
        (self.work/'retention-evidence.json').write_bytes(k.canonical(self.evidence))
        return result

def _main(generation,profile,work):
    request={'generation':json.loads(generation.read_bytes()),'profile':json.loads(profile.read_bytes())}
    definition(request['profile'],request['generation'])
    work.mkdir(mode=0o700,exist_ok=True)
    state=work/'input.json'
    if state.exists():check(state.read_bytes()==k.canonical(request),'Resume input changed')
    else:
        check(not any(p.name!='.lock' for p in work.iterdir()),'New private work directory required')
        state.write_bytes(k.canonical(request))
    prefix_path=work/'prefix.json'
    if not prefix_path.exists():prefix_path.write_bytes(k.canonical({'prefix':'sites/isolated-queue-lab/sets/AWS-'+secrets.token_hex(8)+'/'}))
    k.transport.authorize=lambda actor,**q:k.authorize(actor,retention_days=36,**q)
    (work/'preflight.json').write_bytes(k.canonical(k.transport.preflight()))
    store=LiveStore(work/'transport')
    return Builder(store,work,json.loads(prefix_path.read_bytes())['prefix']).prepare(request['generation'],request['profile'])

def main(generation,profile,work):
    check(not work.is_symlink(), 'Private non-symlink workspace required')
    work.mkdir(mode=0o700,exist_ok=True)
    with (work/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _main(generation,profile,work)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['generation','profile','work']:p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--execute-generated-lab',action='store_true');a=p.parse_args()
    if not a.execute_generated_lab:p.error('Dedicated generated-data opt-in required')
    print(json.dumps(main(a.generation,a.profile,a.work)))
