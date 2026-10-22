"""Fail-closed local current-trust checkpoint. Provisioned by an independent host admin.

No bundle/CLI/environment override. Root and code replacement are outside this boundary.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat

AUTHORITY = Path('/etc/owr-trust/current-recovery.json')

def require(ok, message):
    if not ok: raise ValueError(message)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def timestamp(value):
    result=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
    require(result.tzinfo is not None,'authority timestamp must include timezone')
    return result

def current(trust, document, site, set_id):
    """Return the pinned authority revision; exceptions must abort before side effects."""
    path=AUTHORITY
    require(path.is_absolute(),'authority path must be absolute')
    trust=Path(trust).resolve()
    require(not path.is_relative_to(trust),'authority must be independent of selected trust')
    # Parent paths must not permit a non-root user to replace the registry or symlink it.
    for parent in reversed(path.parents):
        info=parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid==0 and not info.st_mode & 0o022,
                'unprotected authority directory')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode & 0o022,
                'unprotected authority file')
        raw=stream.read(1048577)
    require(len(raw)<=1048576,'authority too large')
    registry=json.loads(raw)
    require(registry['format']=='owr-current-recovery-trust-v1','authority format')
    now=dt.datetime.now(dt.timezone.utc)
    issued,expires=timestamp(registry['issued_at']),timestamp(registry['expires_at'])
    require(issued<=now<expires and dt.timedelta(0)<expires-issued<=dt.timedelta(hours=24),
            'authority expired, future or excessive validity')
    require(type(registry['revision']) is int and registry['revision']>0,'authority revision')
    matches=[e for e in registry['sets'] if e['site_id']==site and e['set_id']==set_id]
    require(len(matches)==1,'missing or duplicate current set')
    entry=matches[0]
    require(entry['status']=='active','set revoked')
    key=digest(trust/'public.pem')
    require(key not in registry['revoked_key_sha256'],'key revoked')
    require(entry['public_key_sha256']==key,'not current signing key')
    require(entry['approved_document_sha256']==digest(document),'not current approval')
    manifest=json.loads(Path(document).read_bytes())
    require(type(entry['minimum_sequence']) is int and entry['minimum_sequence']>0
            and type(manifest['sequence']) is int and manifest['sequence']>=entry['minimum_sequence'],
            'approval generation obsolete')
    return {'revision':registry['revision'],'registry_sha256':hashlib.sha256(raw).hexdigest(),
            'expires_at':registry['expires_at']}

def unchanged(checkpoint, trust, document, site, set_id):
    require(current(trust,document,site,set_id)==checkpoint,'authority changed during recovery; new review required')
