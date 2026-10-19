"""Pairing gate for lab queue recovery. Hashes are NOT a signature/trust root."""
import hashlib,re,sqlite3,tempfile
from pathlib import Path
FORMAT='owr-paired-queue-v1'
def digest(data):return hashlib.sha256(data).hexdigest()
def reconcile_done(jobs,ledger,inventory):
    """A queue ACK is safe only if its effect exists in this restored DB/file set."""
    for job in jobs:
        if job['state']!='done':continue
        effect=ledger.get(job['id'])
        if not effect or effect['kind']!=job['kind'] or inventory.get(effect['path'])!=effect['sha256']:
            raise ValueError('completed queue job has no matching restored effect')
def validate(manifest,assets,site_id,handler_hash):
    if manifest.get('format')!=FORMAT or manifest.get('site_id')!=site_id:raise ValueError('unsupported format/site')
    token=manifest.get('checkpoint','')
    if not re.fullmatch('[a-f0-9]{32}',token):raise ValueError('checkpoint missing')
    if manifest.get('handler_sha256')!=handler_hash:raise ValueError('handler mismatch')
    if set(assets)!={'database','files','queue'} or manifest.get('assets')!={k:digest(v) for k,v in assets.items()}:raise ValueError('asset mismatch')
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'queue.sqlite';path.write_bytes(assets['queue'])
        try:
            with sqlite3.connect(path) as db:
                if db.execute('PRAGMA integrity_check').fetchone()!=('ok',):raise ValueError('corrupt queue')
                if db.execute('SELECT id,checkpoint FROM control').fetchall()!=[(1,token)]:raise ValueError('queue generation mismatch')
                for ident,kind,state in db.execute('SELECT id,kind,state FROM jobs'):
                    if not re.fullmatch('[a-zA-Z0-9_-]{1,48}',ident) or kind not in ['write','deploy','slow'] or state not in ['pending','done','quarantined']:raise ValueError('unsupported job')
        except sqlite3.DatabaseError as exc:raise ValueError('invalid queue') from exc
    return token
