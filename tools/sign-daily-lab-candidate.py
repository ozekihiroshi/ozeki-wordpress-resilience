#!/usr/bin/env python3
"""Offline lab signer; never invoked by the daily publisher; no AWS/network calls."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sign-lab-candidate',action='store_true')
    p.add_argument('--document',type=Path,required=True)
    p.add_argument('--private-key',type=Path,required=True)
    p.add_argument('--signature',type=Path,required=True)
    p.add_argument('--expected-document-sha256',required=True)
    p.add_argument('--expected-public-key-sha256',required=True)
    a=p.parse_args()
    if not a.sign_lab_candidate:p.error('explicit lab signing required')
    if a.document.stat().st_size>=65536:raise ValueError('candidate too large')
    raw=a.document.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.expected_document_sha256:raise ValueError('document hash mismatch')
    m=json.loads(raw)
    if m['site_id']!='isolated-queue-lab' or m['scope']!='storage_integrity_candidate_only' or m['production_recovery_approved'] is not False or m['malware_cleanliness']!='unverified':raise ValueError('lab candidate only')
    now=datetime.now(timezone.utc)
    if not datetime.fromisoformat(m['issued_at'])<=now<datetime.fromisoformat(m['expires_at']):raise ValueError('expired/future candidate')
    if datetime.fromisoformat(m['expires_at'])>datetime.fromisoformat(m['issued_at'])+timedelta(days=7):raise ValueError('approval window exceeds seven days')
    public=subprocess.run(['openssl','pkey','-in',str(a.private_key),'-pubout'],check=True,capture_output=True).stdout
    if hashlib.sha256(public).hexdigest()!=a.expected_public_key_sha256:raise ValueError('operator key mismatch')
    with tempfile.TemporaryDirectory(prefix='owr-offline-review-') as tmp:
        document=Path(tmp)/'reviewed.json';document.write_bytes(raw)
        signature=subprocess.run(['openssl','dgst','-sha256','-sign',str(a.private_key),str(document)],check=True,capture_output=True).stdout
    with a.signature.open('xb') as f:f.write(signature)
    print('Signed the exact reviewed lab candidate. No storage or restore was performed.')


if __name__=='__main__':main()
