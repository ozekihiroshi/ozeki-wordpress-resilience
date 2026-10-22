"""Administrator-only, compare-and-swap deployment of the fixed current trust registry."""
import argparse, datetime as dt, fcntl, hashlib, importlib.util, json, os, re, stat, tempfile
from pathlib import Path
s=importlib.util.spec_from_file_location('current_trust',Path(__file__).with_name('current-recovery-trust.py'))
g=importlib.util.module_from_spec(s);s.loader.exec_module(g)

def sha(raw):return hashlib.sha256(raw).hexdigest()
def unique(pairs):
    result={}
    for key,value in pairs:
        g.require(key not in result,'duplicate JSON key');result[key]=value
    return result

def validate(raw,fresh=True):
    g.require(len(raw)<=1048576,'registry too large')
    x=json.loads(raw,object_pairs_hook=unique)
    g.require(x['format']=='owr-current-recovery-trust-v1','format')
    g.require(type(x['revision']) is int and x['revision']>0,'revision')
    issued,expires=g.timestamp(x['issued_at']),g.timestamp(x['expires_at'])
    g.require(dt.timedelta(0)<expires-issued<=dt.timedelta(hours=24),'validity interval')
    if fresh:g.require(issued<=dt.datetime.now(dt.timezone.utc)<expires,'not currently valid')
    def fingerprint(v):return isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) is not None
    g.require(isinstance(x['revoked_key_sha256'],list) and all(fingerprint(k) for k in x['revoked_key_sha256']),'revocation fingerprints')
    g.require(isinstance(x['sets'],list),'sets')
    seen=set()
    for e in x['sets']:
        key=(e['site_id'],e['set_id'])
        g.require(all(isinstance(v,str) and 0<len(v)<=256 for v in key) and key not in seen,'duplicate/invalid set');seen.add(key)
        g.require(e['status'] in ('active','revoked'),'status')
        g.require(type(e['minimum_sequence']) is int and e['minimum_sequence']>0,'sequence')
        g.require(fingerprint(e['public_key_sha256']) and fingerprint(e['approved_document_sha256']),'fingerprints')
        g.require(e['status']!='active' or e['public_key_sha256'] not in x['revoked_key_sha256'],'active revoked key')
    return x

def protected_parent():
    p=g.AUTHORITY
    for directory in [*reversed(p.parents)]:
        st=directory.lstat()
        g.require(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and not st.st_mode & 0o022,'unprotected directory')

def read_current():
    try:fd=os.open(g.AUTHORITY,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except FileNotFoundError:return None
    with os.fdopen(fd,'rb') as f:
        st=os.fstat(f.fileno());g.require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode & 0o022,'unprotected registry')
        raw=f.read(1048577)
    validate(raw,False);return raw

def transition(old,new):
    g.require(new['revision']>old['revision'],'revision must increase')
    g.require(g.timestamp(new['issued_at'])>=g.timestamp(old['issued_at']),'issued time rollback')
    g.require(set(old['revoked_key_sha256'])<=set(new['revoked_key_sha256']),'revocations cannot be removed')
    entries={(e['site_id'],e['set_id']):e for e in new['sets']}
    for e in old['sets']:
        n=entries.get((e['site_id'],e['set_id']))
        g.require(n is not None,'retain removed sets as revoked tombstones')
        g.require(n['minimum_sequence']>=e['minimum_sequence'],'sequence rollback')
        g.require(e['status']!='revoked' or n['status']=='revoked','revoked set cannot reactivate')
        if (n['public_key_sha256'],n['approved_document_sha256'])!=(e['public_key_sha256'],e['approved_document_sha256']):
            g.require(n['minimum_sequence']>e['minimum_sequence'],'changed approval/key requires higher sequence')

def deploy(candidate,expected,candidate_sha,apply=False):
    g.require(os.geteuid()==0,'administrator required')
    protected_parent()
    with Path(candidate).open('rb') as source:raw=source.read(1048577)
    g.require(sha(raw)==candidate_sha,'candidate changed since review');new=validate(raw)
    lock=g.AUTHORITY.with_suffix('.lock')
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    with os.fdopen(fd,'r+b') as f:
        st=os.fstat(f.fileno());g.require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode & 0o022,'unprotected lock')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=read_current();actual=sha(old) if old is not None else 'absent'
        g.require(actual==expected,'current registry changed or bootstrap expectation wrong')
        if old is not None:transition(validate(old,False),new)
        result={'revision':new['revision'],'sha256':sha(raw),'previous_sha256':actual,'applied':False}
        if not apply:return result
        temp=None
        try:
            out,temp=tempfile.mkstemp(prefix='.current-',dir=g.AUTHORITY.parent)
            with os.fdopen(out,'wb') as t:
                t.write(raw);t.flush();os.fchmod(t.fileno(),0o644);os.fsync(t.fileno())
            # Revalidate freshness and compare state immediately before replacement.
            validate(raw);latest=read_current()
            g.require((sha(latest) if latest is not None else 'absent')==expected,'concurrent registry change')
            os.replace(temp,g.AUTHORITY);temp=None
            directory=os.open(g.AUTHORITY.parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
            g.require(read_current()==raw,'readback differs')
            result['applied']=True;return result
        finally:
            if temp is not None:os.unlink(temp)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspect',action='store_true')
    p.add_argument('--candidate');p.add_argument('--candidate-sha256');p.add_argument('--expected-current-sha256',help='Use absent only for explicitly reviewed first provisioning')
    p.add_argument('--apply',action='store_true',help='Without this flag, validate only (lock file may be created)')
    a=p.parse_args()
    if a.inspect:
        protected_parent();raw=read_current()
        print(json.dumps({'sha256':sha(raw) if raw is not None else 'absent','registry':validate(raw,False) if raw is not None else None}));return
    p.error('candidate and both review hashes required') if not all([a.candidate,a.candidate_sha256,a.expected_current_sha256]) else None
    print(json.dumps(deploy(a.candidate,a.expected_current_sha256,a.candidate_sha256,a.apply)))
if __name__=='__main__':main()
