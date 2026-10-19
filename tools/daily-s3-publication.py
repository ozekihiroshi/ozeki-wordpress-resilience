"""Unsigned lab publication and separately invoked operator approval. No keys in publisher."""
import importlib.util
from datetime import timedelta
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


gate = load('daily_protected_gate', 'protected-queue-set.py')
transport = load('daily_transport', 'queue-s3-adapter.py')
SITE = 'isolated-queue-lab'


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('wb') as f:
        f.write(gate.encode(value)); f.flush(); os.fsync(f.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def candidate(path, expected_hash):
    path = Path(path)
    if path.stat().st_size >= 65536: raise ValueError('candidate too large')
    raw = path.read_bytes()
    if gate.sha(raw) != expected_hash: raise ValueError('candidate hash changed')
    m = json.loads(raw)
    gate.check(m['format'] == gate.FORMAT and m['site_id'] == SITE and re.fullmatch('AWS-[a-f0-9]{16}', m['set_id']), 'not a lab candidate')
    gate.check(m['scope'] == 'storage_integrity_candidate_only' and m['production_recovery_approved'] is False and m['malware_cleanliness'] == 'unverified', 'unexpected claim')
    gate.check(gate.date(m['issued_at']) < gate.date(m['expires_at']) <= gate.date(m['issued_at']) + timedelta(days=7), 'approval window exceeds lab contract')
    gate.check(len(m['assets']) == 3 and {e['role'] for e in m['assets']} == set(gate.NAMES), 'incomplete assets')
    total = 0
    for entry in m['assets']:
        loc = entry['locator']
        gate.check(loc['bucket'] == transport.BUCKET and loc['region'] == transport.REGION, 'wrong destination')
        gate.check(loc['key'] == f"sites/{SITE}/sets/{m['set_id']}/{gate.NAMES[entry['role']]}", 'wrong asset key')
        gate.check(isinstance(loc['version_id'], str) and loc['version_id'] not in ('', 'null'), 'unfixed version')
        gate.check(type(loc['size_bytes']) is int and loc['size_bytes'] > 0 and re.fullmatch('[a-f0-9]{64}', loc['sha256']), 'invalid size/hash')
        gate.check(loc['writer_identity'] == 'my-ssm-role' and entry['verification']['reader_identity'] == 'OwrM1RecoveryReader', 'role separation')
        gate.check(entry['verification']['size_and_sha256_match'] is True, 'unverified storage')
        total += loc['size_bytes']
    gate.check(total <= 128*1024*1024, 'lab size limit')
    return m


def publish(assets, paired, directory, mark, adapter_factory=None, preflight=None):
    gate.check(paired['site_id'] == SITE and sum(map(len, assets.values())) <= 128*1024*1024, 'lab assets only')
    gate.pair.validate(paired, assets, SITE, paired['handler_sha256'])
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    set_id = 'AWS-'+secrets.token_hex(8)
    receipt = {'format': 'owr-daily-s3-pending-v1', 'set_id': set_id, 'storage_complete': False,
               'approval_state': 'pending', 'restore_allowed': False, 'production_data_used': False}
    write_json(directory/'receipt.json', receipt)
    try:
        receipt['preflight'] = (preflight or transport.preflight)()
        adapter = (adapter_factory or transport.S3Adapter)(directory/'transfer-receipts')
        m = gate.build(assets, paired, SITE, set_id, transport.BUCKET, transport.REGION,
                       'my-ssm-role', 'OwrM1RecoveryReader', adapter.put, adapter.get)
        write_json(directory/'candidate.json', m)
        receipt.update(storage_complete=True, manifest_sha256=gate.sha((directory/'candidate.json').read_bytes()),
                       minimum_retention_until=m['minimum_retention_until'], signature_created=False,
                       bucket=transport.BUCKET, prefix=f'sites/{SITE}/sets/{set_id}/')
        write_json(directory/'receipt.json', receipt)
        mark('daily_three_assets_stored_unsigned_awaiting_independent_approval')
        return {k: receipt[k] for k in ['format','set_id','storage_complete','approval_state','restore_allowed','manifest_sha256','signature_created','bucket','prefix','minimum_retention_until']}
    except Exception as exc:
        receipt['error_type'] = type(exc).__name__
        write_json(directory/'receipt.json', receipt)
        raise


def verify_saved(directory, summary):
    directory = Path(directory)
    receipt = json.loads((directory/'receipt.json').read_text())
    gate.check(receipt['storage_complete'] is True and receipt['approval_state'] == 'pending' and receipt['restore_allowed'] is False and receipt['signature_created'] is False, 'not an unsigned stored candidate')
    for k, v in summary.items(): gate.check(receipt.get(k) == v, 'receipt/report mismatch')
    m = candidate(directory/'candidate.json', receipt['manifest_sha256'])
    gate.check(m['set_id'] == receipt['set_id'], 'set mismatch')
    operations = json.loads((directory/'transfer-receipts/operations.json').read_text())
    puts = [e for e in operations if e['method'] == 'PUT']
    gate.check(len(puts) == 3 and all(e['state'] == 'acknowledged' for e in puts), 'incomplete/uncertain PUT')
    for entry in m['assets']:
        loc = entry['locator']
        matching = [e for e in puts if e['key'] == loc['key'] and e['version_id'] == loc['version_id'] and e['sha256'] == loc['sha256'] and e['bytes'] == loc['size_bytes']]
        gate.check(len(matching) == 1, 'PUT receipt mismatch')
        gate.check(any(e['method'] == 'GET' and e['key'] == loc['key'] and e['version_id'] == loc['version_id'] and e['sha256'] == loc['sha256'] for e in operations), 'independent read missing')
    return m


def approve(document, signature, public_key, expected_hash, expected_key_hash, operator_dir, adapter_factory=None):
    """Key and hashes are operator inputs, never taken from the unsigned candidate."""
    document, signature, public_key = map(Path, (document, signature, public_key))
    gate.check(gate.sha(public_key.read_bytes()) == expected_key_hash, 'untrusted public key')
    m = candidate(document, expected_hash)
    operator_dir = Path(operator_dir).resolve()
    gate.check(not operator_dir.is_relative_to(document.parent.resolve()), 'operator trust inside daily work')
    operator_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    # Freeze the reviewed inputs before verification, and keep them for failure diagnosis.
    shutil.copyfile(document, operator_dir/'recovery-set.json')
    shutil.copyfile(signature, operator_dir/'recovery-set.sig')
    shutil.copyfile(public_key, operator_dir/'public.pem')
    pin = {'status':'active','site_id':SITE,'set_id':m['set_id'],'minimum_sequence':1,
           'bucket':transport.BUCKET,'region':transport.REGION,'writer_identity':'my-ssm-role',
           'reader_identity':'OwrM1RecoveryReader','public_key_sha256':expected_key_hash,
           'approved_document_sha256':expected_hash,'envelope':{}}
    write_json(operator_dir/'pin.json', pin)
    doc, sig = operator_dir/'recovery-set.json', operator_dir/'recovery-set.sig'
    gate.authorize(operator_dir, doc, sig, SITE, m['set_id'])
    # No network or reader adapter construction before signature authorization.
    adapter = (adapter_factory or transport.S3Adapter)(operator_dir/'reader-receipts')
    handler = gate.sha((ROOT/'lab/consistency/external-job.php').read_bytes())
    _, result = gate.fetch_verified(operator_dir, doc, sig, SITE, m['set_id'], handler, adapter.get)
    approved = {'state':'approved','set_id':m['set_id'],'manifest_sha256':expected_hash,
                'public_key_sha256':expected_key_hash,'verification':result,'operator_directory':str(operator_dir),
                'approved_at':gate.now().isoformat(),'approval_expires_at':m['expires_at'],
                'isolated_restore_verified':False,'production_recovery_approved':False}
    write_json(operator_dir/'approval.json', approved)
    return approved
