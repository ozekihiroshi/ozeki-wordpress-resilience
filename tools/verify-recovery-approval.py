#!/usr/bin/env python3
"""Verify a separately provisioned trust pin and signed M1 approval. Never executes assets."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from pathlib import PurePosixPath

def checked(ok, reason):
    if not ok:
        raise ValueError(reason)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def verify(trust, approval, signature, bundle, expected_site, expected_set):
    pin = json.loads((trust/'pin.json').read_text())
    key = trust/'public.pem'
    checked(digest(key.read_bytes()) == pin['public_key_sha256'], 'Untrusted key')
    checked(pin['status'] == 'active', 'Key revoked')
    checked(pin['site_id'] == expected_site, 'Untrusted site')
    raw = approval.read_bytes()
    checked(len(raw) < 65536, 'Approval too large')
    proc = subprocess.run(['openssl','dgst','-sha256','-verify',str(key),
        '-signature',str(signature),str(approval)], capture_output=True, timeout=10)
    checked(proc.returncode == 0, 'Invalid signature')
    data = json.loads(raw)
    checked(data['format'] == 'owr-recovery-approval-v1', 'Unknown format')
    checked(data['algorithm'] == 'rsa-sha256', 'Unknown algorithm')
    checked(data['site_id'] == expected_site and data['set_id'] == expected_set, 'Wrong target')
    checked(type(data['sequence']) is int and data['sequence'] >= pin['minimum_sequence'], 'Stale approval')
    now = datetime.now(timezone.utc)
    issued = datetime.fromisoformat(data['issued_at'])
    expires = datetime.fromisoformat(data['expires_at'])
    checked(issued <= now < expires and issued < expires, 'Invalid approval time')
    checked(digest(raw) == pin['approved_document_sha256'], 'Not the independently approved document')
    anchor_path = bundle/'anchor.json'
    checked(digest(anchor_path.read_bytes()) == data['anchor_sha256'], 'Anchor changed')
    anchor = json.loads(anchor_path.read_text())
    checked(anchor['site_id'] == expected_site and anchor['set_id'] == expected_set, 'Anchor target mismatch')
    for entry, filename in [('set','recovery-set.json'),('ram','ram.json'),('bootstrap','bootstrap.tar.gz')]:
        receipt = anchor[entry]
        checked(receipt['locator']['version_id'] not in ('', 'null', None), 'Unpinned version')
        path = bundle/filename
        checked(path.stat().st_size == receipt['size_bytes'], 'Size mismatch')
        checked(digest(path.read_bytes()) == receipt['sha256'], 'Hash mismatch')
    record = json.loads((bundle/'recovery-set.json').read_text())
    checked(record['site_id'] == expected_site and record['set_id'] == expected_set, 'Set mismatch')
    checked(record['ram_sha256'] == digest((bundle/'ram.json').read_bytes()), 'RAM binding mismatch')
    return {'passed':True,'kind':'signed_approval_verification','sequence':data['sequence'],
        'site_id':expected_site,'set_id':expected_set,'expires_at':data['expires_at'],
        'claim':'operator-approved metadata integrity only','malware_cleanliness':'unverified',
        'assets_executed':False}

def verify_restore_gate(trust, approval, signature, bundle, expected_site, expected_set):
    """Fail closed before any Docker operation; trust must be provisioned separately."""
    bundle = bundle.resolve()
    for path in (trust, approval, signature, Path(__file__)):
        checked(not path.resolve().is_relative_to(bundle), 'Trust or verifier inside downloaded bundle')
    result = verify(trust, approval, signature, bundle, expected_site, expected_set)
    # Bind the files actually executed/mounted to the signed archive, not merely its digest.
    expected = set()
    checked(not (bundle/'bootstrap').is_symlink(), 'Bootstrap symlink')
    with tarfile.open(bundle/'bootstrap.tar.gz') as archive:
        seen = set()
        for member in archive:
            name = PurePosixPath(member.name)
            checked(not name.is_absolute() and '..' not in name.parts and
                    name.parts and name.parts[0] == 'bootstrap', 'Unsafe bootstrap path')
            checked(member.isdir() or member.isfile(), 'Unsafe bootstrap member')
            checked(str(name) not in seen, 'Duplicate bootstrap member')
            seen.add(str(name))
            path = bundle.joinpath(*name.parts)
            checked(not any(p.is_symlink() for p in [path, *path.parents]), 'Bootstrap symlink')
            if member.isfile():
                expected.add(path.relative_to(bundle).as_posix())
                checked(path.is_file() and path.stat().st_size == member.size, 'Bootstrap size changed')
                checked(digest(path.read_bytes()) == digest(archive.extractfile(member).read()), 'Bootstrap changed')
    actual = set()
    for path in (bundle/'bootstrap').rglob('*'):
        checked(not path.is_symlink(), 'Bootstrap symlink')
        if path.is_file(): actual.add(path.relative_to(bundle).as_posix())
        else: checked(path.is_dir(), 'Unsafe bootstrap file')
    checked(actual == expected, 'Unexpected bootstrap files')
    ram = json.loads((bundle/'ram.json').read_text())
    checked(ram['site_id'] == expected_site and ram['set_id'] == expected_set, 'RAM target mismatch')
    result['bootstrap_tree_verified'] = True
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['trust-dir','approval','signature','bundle','site-id','set-id']:
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    try:
        result = verify(Path(args.trust_dir),Path(args.approval),Path(args.signature),
            Path(args.bundle),args.site_id,args.set_id)
    except Exception as error:
        print(json.dumps({'passed':False,'error_type':type(error).__name__}))
        return 1
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
