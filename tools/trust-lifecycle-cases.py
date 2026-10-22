"""Generated-only lifecycle checks against the existing first-site authorization gate.

No S3, Docker, notifications, production keys or physical removable media.
The old-trust rollback case is an expected limitation, not a security pass.
"""
import argparse, copy, datetime as dt, hashlib, importlib.util, json, os, secrets, shutil, subprocess, tempfile
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();os.umask(0o077)
    a.workspace.mkdir(parents=True,exist_ok=False,mode=0o700)
    spec=importlib.util.spec_from_file_location('gate',Path(__file__).with_name('protected-first-site-set.py'))
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    results=[]
    def run(args,**kw):return subprocess.run(['openssl']+args,check=True,capture_output=True,timeout=40,**kw)
    def sha(b):return hashlib.sha256(b).hexdigest()
    def record(name,fn):
        fn();results.append({'case':name,'passed':True})
    with tempfile.TemporaryDirectory(prefix='disposable-keys-',dir=a.workspace) as td:
        keys=Path(td)
        for name in ['old','new']:
            run(['genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(keys/(name+'.pem'))])
            run(['pkey','-in',str(keys/(name+'.pem')),'-pubout','-out',str(keys/(name+'.pub'))])
        t=dt.datetime.now(dt.timezone.utc);iso=lambda x:x.isoformat()
        entries=[]
        for role,filename in gate.NAMES.items():
            entries.append({'role':role,'locator':{'bucket':'generated-bucket','region':'ap-northeast-1','key':'sites/generated-site/sets/generated-set/'+filename,'version_id':'generated-v1','size_bytes':1,'sha256':sha(b'x'),'writer_identity':'generated-writer'},'retention':{'mode':'GOVERNANCE','last_modified':iso(t-dt.timedelta(hours=1)),'retain_until':iso(t+dt.timedelta(days=36))},'verification':{'reader_identity':'generated-reader','checked_at':iso(t-dt.timedelta(minutes=1)),'size_and_sha256_match':True}})
        m={'format':gate.FORMAT,'algorithm':'rsa-sha256','site_id':'generated-site','set_id':'generated-set','sequence':1,'scope':'storage_integrity_candidate_only','production_recovery_approved':False,'malware_cleanliness':'unverified','issued_at':iso(t),'expires_at':iso(t+dt.timedelta(days=1)),'minimum_retention_until':iso(t+dt.timedelta(days=36)),'assets':entries,'paired':{'config_sha256':sha(b'generated')}}
        def package(label,key,manifest):
            root=a.workspace/label;root.mkdir();(root/'approved.json').write_bytes(gate.encode(manifest))
            run(['dgst','-sha256','-sign',str(keys/(key+'.pem')),'-out',str(root/'approved.sig'),str(root/'approved.json')])
            shutil.copyfile(keys/(key+'.pub'),root/'public.pem')
            pin={'status':'active','site_id':m['site_id'],'set_id':m['set_id'],'minimum_sequence':manifest['sequence'],'bucket':'generated-bucket','region':'ap-northeast-1','writer_identity':'generated-writer','reader_identity':'generated-reader','public_key_sha256':sha((root/'public.pem').read_bytes()),'approved_document_sha256':sha((root/'approved.json').read_bytes()),'envelope':{}}
            (root/'pin.json').write_text(json.dumps(pin));return root
        def verify(trust,source=None):
            source=source or trust
            return gate.authorize(trust,source/'approved.json',source/'approved.sig',m['site_id'],m['set_id'])
        def reject(trust,source=None):
            try:verify(trust,source)
            except ValueError:return
            raise AssertionError('Invalid approval was accepted')
        old=package('generation-1','old',m)
        record('original_approval',lambda:verify(old))
        newer=copy.deepcopy(m);newer['sequence']=2;newer['expires_at']=iso(t+dt.timedelta(days=2))
        new=package('generation-2','new',newer)
        record('reviewed_rotation_new_key_new_sequence',lambda:verify(new))
        record('old_document_against_current_pin_rejected',lambda:reject(new,old))
        revoked=a.workspace/'revoked-generation-1';shutil.copytree(old,revoked)
        pin=json.loads((revoked/'pin.json').read_text());pin['status']='revoked';(revoked/'pin.json').write_text(json.dumps(pin))
        record('revocation_rejected',lambda:reject(revoked))
        expired=copy.deepcopy(m);expired['issued_at']=iso(t-dt.timedelta(days=2));expired['expires_at']=iso(t-dt.timedelta(days=1))
        ex=package('expired','old',expired);record('expired_rejected_with_valid_signature',lambda:reject(ex))
        stale=a.workspace/'stale-sequence';shutil.copytree(old,stale)
        pin=json.loads((stale/'pin.json').read_text());pin['minimum_sequence']=2;(stale/'pin.json').write_text(json.dumps(pin))
        record('old_sequence_rejected',lambda:reject(stale))
        mixed=a.workspace/'mixed';shutil.copytree(new,mixed);shutil.copyfile(old/'public.pem',mixed/'public.pem')
        record('mixed_key_pin_rejected',lambda:reject(mixed))
        tamper=a.workspace/'tampered';shutil.copytree(new,tamper);(tamper/'approved.json').write_bytes(b'{}')
        record('partial_or_tampered_bundle_rejected',lambda:reject(tamper))
        # Same-machine directories simulate recipient and removable media, not physical independence.
        media=a.workspace/'simulated-usb-generation-2';shutil.copytree(new,media)
        password=secrets.token_urlsafe(40).encode()
        run(['pkcs8','-topk8','-in',str(keys/'new.pem'),'-out',str(media/'private.encrypted.pem'),'-v2','aes-256-cbc','-iter','600000','-passout','stdin'],input=password+b'\n')
        try:run(['pkey','-in',str(media/'private.encrypted.pem'),'-passin','stdin','-pubout'],input=b'wrong-password\n')
        except subprocess.CalledProcessError:results.append({'case':'wrong_media_password_rejected','passed':True})
        else:raise AssertionError('Wrong password accepted')
        hashes={f.name:sha(f.read_bytes()) for f in media.iterdir() if f.is_file()}
        successor=a.workspace/'successor-readback';shutil.copytree(media,successor)
        assert all(sha((successor/n).read_bytes())==v for n,v in hashes.items())
        # Remove the new plaintext key before exercising the encrypted readback.
        (keys/'new.pem').unlink()
        pub=run(['pkey','-in',str(successor/'private.encrypted.pem'),'-passin','stdin','-pubout'],input=password+b'\n').stdout
        assert pub==(successor/'public.pem').read_bytes()
        run(['dgst','-sha256','-sign',str(successor/'private.encrypted.pem'),'-passin','stdin','-out',str(successor/'readback.sig'),str(successor/'approved.json')],input=password+b'\n')
        run(['dgst','-sha256','-verify',str(new/'public.pem'),'-signature',str(successor/'readback.sig'),str(successor/'approved.json')])
        record('encrypted_readback_signing_without_plaintext_key',lambda:verify(successor))
        record('successor_current_bundle_accepted',lambda:verify(successor))
        interrupted=a.workspace/'interrupted-update';interrupted.mkdir();shutil.copyfile(new/'pin.json',interrupted/'pin.json')
        try:verify(interrupted)
        except (ValueError,FileNotFoundError):results.append({'case':'incomplete_copy_rejected','passed':True})
        else:raise AssertionError('Incomplete copy accepted')
        # Deliberately retain the original trusted pin: current gate has no external revocation registry.
        verify(old)
        limitations=[{'case':'complete_old_trust_bundle_rollback','observed':'accepted while original approval remains valid','security_requirement_met':False,'reason':'Current verifier trusts the operator-selected pin; no independent latest generation or global revocation registry.'}]
        # Do not retain even disposable encrypted private keys/passwords in evidence.
        for root in [media,successor]:(root/'private.encrypted.pem').unlink()
    output={'format':'owr-trust-lifecycle-lab-v1','checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'passed_checks':len(results),'checks':results,'known_limitations':limitations,'real_s3':False,'physical_usb':False,'separate_operator_identity':False,'production_keys_used':False,'private_keys_retained':False,'assets_fetched_or_executed':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
if __name__=='__main__':main()
