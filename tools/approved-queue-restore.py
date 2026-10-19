"""Read-only retrieval of an independently approved lab set; no restore on import."""
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('approved_publication',ROOT/'tools/daily-s3-publication.py')
publication=importlib.util.module_from_spec(s);s.loader.exec_module(publication)
gate=publication.gate


def archive_inventory(body):
    """Validate every member before extraction into a disposable container."""
    inventory={};seen=set();total=0
    with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as archive:
        for count, member in enumerate(archive,1):
            path=PurePosixPath(member.name)
            gate.check(count<=20000 and not path.is_absolute() and '..' not in path.parts and '\\' not in member.name,'unsafe archive path/count')
            name=str(path)
            gate.check(name not in seen,'duplicate archive path');seen.add(name)
            gate.check(member.isdir() or member.isfile(),'archive links/special files forbidden')
            gate.check(member.size>=0 and (not member.isdir() or member.size==0),'invalid archive directory payload')
            if member.isfile():
                gate.check(name!='.' and 0<=member.size<=128*1024*1024,'invalid archive file')
                total+=member.size;gate.check(total<=512*1024*1024,'expanded archive too large')
                data=archive.extractfile(member).read(member.size+1)
                gate.check(len(data)==member.size,'truncated archive')
                inventory[name]=gate.sha(data)
    gate.check(bool(inventory),'empty archive')
    # A regular file may not be the parent of another entry.
    for name in seen:
        gate.check(not any(str(parent) in inventory for parent in PurePosixPath(name).parents),'file/directory collision')
    return inventory


def fetch(trust,set_id,document_hash,key_hash,receipts,mark,adapter_factory=None):
    trust=Path(trust).resolve();receipts=Path(receipts).resolve()
    gate.check(not receipts.is_relative_to(trust) and not trust.is_relative_to(receipts),'trust and receipts must be separate')
    document=trust/'recovery-set.json';signature=trust/'recovery-set.sig'
    gate.check(gate.sha((trust/'public.pem').read_bytes())==key_hash,'operator key fingerprint mismatch')
    m=publication.candidate(document,document_hash)
    gate.check(m['set_id']==set_id,'wrong selected set')
    approved=json.loads((trust/'approval.json').read_text())
    gate.check(approved['state']=='approved' and approved['set_id']==set_id and approved['manifest_sha256']==document_hash and approved['public_key_sha256']==key_hash,'independent approval missing/mismatched')
    gate.check(approved['verification']['passed'] is True and approved['verification']['assets_verified']==3 and approved['verification']['checkpoint']==m['paired']['checkpoint'],'incomplete approval')
    gate.check(approved['approval_expires_at']==m['expires_at'] and approved['production_recovery_approved'] is False,'approval scope changed')
    gate.authorize(trust,document,signature,publication.SITE,set_id)
    mark('approved_signature_verified_before_s3_reads')
    adapter=(adapter_factory or publication.transport.S3Adapter)(receipts)
    try:
        handler=gate.sha((ROOT/'lab/consistency/external-job.php').read_bytes())
        assets,verified=gate.fetch_verified(trust,document,signature,publication.SITE,set_id,handler,adapter.get)
        mark('approved_three_fixed_versions_retention_checkpoint_verified')
        inventory=archive_inventory(assets['files'])
        mark('approved_archive_paths_and_types_verified')
        evidence={'set_id':set_id,'manifest_sha256':document_hash,'public_key_sha256':key_hash,
                  'verification':verified,'transport':'AWS S3 fixed VersionId, reader only','receipts_directory':str(receipts),
                  'file_count':len(inventory),'asset_locators':[e['locator'] for e in m['assets']],
                  'approval_expires_at':m['expires_at'],'minimum_retention_until':m['minimum_retention_until'],
                  'new_signature_created':False,'production_recovery_approved':False}
        publication.write_json(receipts/'retrieval.json',{'passed':True,'restore_completed':False,'evidence':evidence})
        return assets,evidence,m['paired']
    except Exception as exc:
        publication.write_json(receipts/'retrieval.json',{'passed':False,'restore_completed':False,'error_type':type(exc).__name__})
        raise
