"""Local transport contract lab, NOT AWS Object Lock or IAM enforcement evidence."""
import copy,datetime as dt,importlib.util,json,secrets,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('protected_queue',ROOT/'tools/protected-queue-set.py')
gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)
class VersionStore:
    def __init__(self):self.objects={};self.calls=[]
    def put(self,bucket,key,body):
        version=secrets.token_hex(16);t=gate.now()
        self.objects[bucket,key,version]={'body':body,'version_id':version,'mode':'GOVERNANCE','last_modified':t.isoformat(),'retain_until':(t+dt.timedelta(days=35)).isoformat(),'reader_identity':'lab-reader'}
        return version
    def get(self,loc):
        self.calls.append((loc['key'],loc['version_id']))
        return dict(self.objects[loc['bucket'],loc['key'],loc['version_id']])
def exercise(assets,paired,mark):
    with tempfile.TemporaryDirectory(prefix='owr-signed-queue-') as tmp:
        root=Path(tmp);trust=root/'operator-trust';trust.mkdir(mode=0o700)
        signer=root/'operator-signer';signer.mkdir(mode=0o700);key=signer/'private.pem'
        document=root/'recovery-set.json';sig=root/'recovery-set.sig'
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],check=True,capture_output=True);key.chmod(0o600)
        subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(trust/'public.pem')],check=True,capture_output=True)
        store=VersionStore();site=paired['site_id'];set_id='LAB-'+secrets.token_hex(6)
        m=gate.build(assets,paired,site,set_id,'owr-offline-lab','ap-northeast-1','lab-writer','lab-reader',store.put,store.get)
        def sign(value):
            document.write_bytes(gate.encode(value))
            subprocess.run(['openssl','dgst','-sha256','-sign',str(key),'-out',str(sig),str(document)],check=True,capture_output=True)
            pin={'status':'active','site_id':site,'set_id':set_id,'minimum_sequence':1,'bucket':'owr-offline-lab','region':'ap-northeast-1','writer_identity':'lab-writer','reader_identity':'lab-reader','public_key_sha256':gate.sha((trust/'public.pem').read_bytes()),'approved_document_sha256':gate.sha(document.read_bytes())}
            (trust/'pin.json').write_bytes(gate.encode(pin))
        def fetch(get=None):return gate.fetch_verified(trust,document,sig,site,set_id,paired['handler_sha256'],get or store.get)
        def reject(label,fn):
            try:fn()
            except (ValueError,KeyError):mark(label);return
            raise RuntimeError('negative case accepted: '+label)
        sign(m)
        # Newer keys must never redirect recovery away from the signed versions.
        for e in m['assets']:store.put(e['locator']['bucket'],e['locator']['key'],b'newer unapproved bytes')
        fetched,result=fetch();check_equal=(fetched==assets)
        if not check_equal:raise RuntimeError('fixed-version retrieval changed assets')
        mark('signed_three_asset_set_fetches_fixed_versions_despite_newer_objects')
        original=sig.read_bytes();sig.write_bytes(b'invalid');before=len(store.calls)
        reject('invalid_signature_rejected_before_any_asset_fetch',fetch)
        if len(store.calls)!=before:raise RuntimeError('fetch before signature gate')
        sig.write_bytes(original)
        for label,mutate in [
            ('signed_missing_queue_rejected',lambda x:x['assets'].pop()),
            ('signed_null_version_rejected',lambda x:x['assets'][2]['locator'].update(version_id='null')),
            ('signed_short_retention_rejected',lambda x:x['assets'][2]['retention'].update(retain_until=(gate.now()+dt.timedelta(days=1)).isoformat())),
            ('signed_wrong_bucket_rejected',lambda x:x['assets'][2]['locator'].update(bucket='other')),
            ('signed_expired_approval_rejected',lambda x:x.update(expires_at=(gate.now()-dt.timedelta(seconds=1)).isoformat())),
            ('signed_mixed_checkpoint_rejected',lambda x:x['paired'].update(checkpoint='f'*32)),
        ]:
            altered=copy.deepcopy(m);mutate(altered);sign(altered);reject(label,fetch)
        sign(m)
        for label,change in [
            ('fresh_wrong_version_rejected',{'version_id':'other'}),
            ('fresh_queue_bytes_tampering_rejected',{'body':b'changed'}),
            ('fresh_retention_removed_rejected',{'mode':None}),
            ('fresh_reader_identity_mismatch_rejected',{'reader_identity':'lab-writer'}),
        ]:
            def bad_get(loc,change=change):
                r=store.get(loc)
                if loc['key'].endswith('queue.sqlite'):r.update(change)
                return r
            reject(label,lambda:fetch(bad_get))
        pin=json.loads((trust/'pin.json').read_bytes());pin['status']='revoked';(trust/'pin.json').write_bytes(gate.encode(pin))
        reject('revoked_independent_trust_rejected',fetch)
        sign(m)
        pin=json.loads((trust/'pin.json').read_bytes());pin['envelope']={}
        for role,path in [('document',document),('signature',sig)]:
            body=path.read_bytes();keyname=f'sites/{site}/sets/{set_id}/'+path.name
            loc={'bucket':pin['bucket'],'region':pin['region'],'key':keyname,'version_id':store.put(pin['bucket'],keyname,body),'size_bytes':len(body),'sha256':gate.sha(body)}
            r=store.get(loc);pin['envelope'][role]={'locator':loc,'retention':{k:r[k] for k in ['last_modified','retain_until']}}
            store.put(pin['bucket'],keyname,b'unapproved newer envelope')
        (trust/'pin.json').write_bytes(gate.encode(pin))
        document,sig=gate.fetch_envelope(trust,store.get,root/'download')
        fetched,result=fetch()
        mark('signed_envelope_retrieved_from_independently_pinned_versions')
        return fetched,{'verification':result,'transport':'local versioned-store test double; NOT real AWS','signature':'real RSA-SHA256; ephemeral operator-side key never mounted in guest','signed_document_sha256':gate.sha(document.read_bytes()),'private_key_retained':False,'aws_calls':0}
