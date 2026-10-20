"""Local operator-reviewed restore observations; never recovery authorization."""
import json
from pathlib import Path


def register(coordinator, day, directory, expected_hash, daily):
    g = daily.gate
    root = Path(directory).resolve()
    raw = (root/'result.json').read_bytes()
    g.check(len(raw)<65536 and g.sha(raw)==expected_hash, 'reviewed restore report changed')
    report = json.loads(raw)
    with coordinator.locked() as db:
        row = db.execute('SELECT * FROM runs WHERE day=?',(day,)).fetchone()
        g.check(row is not None and row['state']=='approved','approved daily run required')
        work = coordinator.root/row['id']
        receipt = daily.verify_saved(work)
        g.check(g.sha((work/'receipt.json').read_bytes())==row['digest'],'receipt changed')
        approval = json.loads((work/'approval.json').read_bytes())
        g.check(approval['state']=='approved' and approval['verification']['passed'] is True
                and approval['production_recovery_approved'] is False
                and approval['approval_expires_at']==receipt['approval_expires_at'],
                'approval evidence incomplete')
        trust = root/'trust-snapshot'
        doc, sig = trust/'approved.json', trust/'approved.sig'
        g.check(g.sha(doc.read_bytes())==approval['manifest_sha256']==receipt['manifest_sha256'],
                'restore belongs to another approved document')
        g.check(g.sha((trust/'public.pem').read_bytes())==approval['public_key_sha256'],'restore key mismatch')
        manifest, _ = g.authorize(trust,doc,sig,daily.SITE,receipt['set_id'])
        g.check(manifest['paired']['config_sha256']==receipt['config_sha256'],'restore configuration mismatch')
        g.check(report['format']=='owr-first-site-daily-restore-v1'
                and report['set_id']==receipt['set_id'] and type(report['passed']) is bool
                and report['production_recovery_approved'] is False,'invalid restore report')
        if 'completed_at' in report:
            g.check(g.date(approval['approved_at'])<=g.date(report['completed_at'])<=g.now(),
                    'restore observation time outside approved period')
        evidence = {'report':report,'manifest_sha256':receipt['manifest_sha256'],
                    'public_key_sha256':approval['public_key_sha256'],
                    'config_sha256':receipt['config_sha256'],'report_sha256':expected_hash}
        if report['passed']:
            g.check(report['assets_verified'] is True and report['restore_started'] is True
                    and report['source_workspace_used'] is False and report['source_server_used'] is False,
                    'incomplete recovery')
            g.check(report['verification']['passed'] is True
                    and report['verification']['assets_verified']==2
                    and report['verification']['attempt_id']==manifest['paired']['attempt_id'],
                    'capture verification binding mismatch')
            g.check(g.date(approval['approved_at'])<=g.date(report['completed_at'])<=g.now(),
                    'recovery predates approval or is in future')
            outcome = report['isolated_restore']
            g.check(outcome==json.loads((root/'isolation.json').read_bytes()),'isolation evidence mismatch')
            g.check(outcome['passed'] is True and outcome['resources_removed'] is True
                    and outcome['published_ports'] is False and outcome['source_mounts'] is False
                    and outcome['fresh_database_credentials'] is True
                    and outcome['network']=='none + shared private namespace','isolation/cleanup incomplete')
            wp=outcome['wordpress']
            g.check(wp['post']==1 and wp['attachment']=='one.png'
                    and wp['cron_disabled'] is True and wp['http_blocked'] is True
                    and outcome['http']['status']==200 and outcome['http']['post'] is True,
                    'WordPress verification incomplete')
            ops=json.loads((root/'reader-receipts/operations.json').read_bytes())
            g.check(len(ops)==2 and all(x['method']=='GET' for x in ops),'unexpected restore operations')
            assets={}
            for entry in manifest['assets']:
                loc=entry['locator']; role=entry['role']
                body=(root/'verified-assets'/g.NAMES[role]).read_bytes()
                matching=[op for op in ops if all(op.get(k)==v for k,v in
                    dict(key=loc['key'],version_id=loc['version_id'],bytes=loc['size_bytes'],sha256=loc['sha256']).items())]
                g.check(len(matching)==1,'fixed version observation mismatch')
                ret=matching[0]['retention']
                g.observe(role,body,loc,dict(body=body,version_id=loc['version_id'],
                          reader_identity='OwrM1RecoveryReader',**ret),'OwrM1RecoveryReader')
                g.check(g.date(ret['retain_until'])>=g.date(entry['retention']['retain_until']),
                        'retention shortened')
                assets[role]=body
            g.validate_capture(manifest['paired'],assets)
            capture=daily.load('observation_capture','first-site-capture.py')
            inventory=capture.archive_inventory(root/'verified-assets'/g.NAMES['files'],512*1024**2)
            g.check(capture.digest(inventory)==manifest['paired']['inventory_sha256']
                    and wp['media']==inventory['wp-content/uploads/one.png'],'restore inventory/media mismatch')
            evidence['reads']=ops
        payload=g.encode(evidence)
        db.execute('CREATE TABLE IF NOT EXISTS restore_observations(n INTEGER PRIMARY KEY,day TEXT,report_hash TEXT,registered_at TEXT,payload TEXT,payload_hash TEXT,UNIQUE(day,report_hash))')
        old=db.execute('SELECT payload_hash FROM restore_observations WHERE day=? AND report_hash=?',
                       (day,expected_hash)).fetchone()
        if old:
            g.check(old[0]==g.sha(payload),'observation content changed')
            return dict(registered=False,duplicate=True,report_sha256=expected_hash)
        db.execute('INSERT INTO restore_observations(day,report_hash,registered_at,payload,payload_hash) VALUES(?,?,?,?,?)',
                   (day,expected_hash,g.now().isoformat(),payload.decode(),g.sha(payload)))
        db.commit()
        return dict(registered=True,duplicate=False,restore_state='verified' if report['passed'] else 'failed',
                    report_sha256=expected_hash)


def aggregate(row, records, daily):
    row.update(restore_state='not_observed',restore_verified=False,restore_observation_count=len(records))
    valid=[]
    for record in records:
        try:
            raw=record['payload'].encode()
            daily.gate.check(daily.gate.sha(raw)==record['payload_hash'],'observation changed')
            value=json.loads(raw)
            daily.gate.check(value['manifest_sha256']==row.get('manifest_sha256')
                             and value['public_key_sha256']==row.get('approved_key_sha256')
                             and value['report_sha256']==record['report_hash'],'observation binding changed')
            at=daily.gate.date(value['report'].get('completed_at',record['registered_at']))
            valid.append((at,record['n'],value))
        except Exception:
            row['restore_state']='evidence_error'
            row['restore_evidence_error']=True
            return
    if valid:
        valid.sort(key=lambda x:(x[0],x[1]))
        latest=valid[-1][2]
        row['restore_state']='verified' if latest['report']['passed'] is True else 'failed'
        row['restore_verified']=row['restore_state']=='verified'
        row['last_restore_report_sha256']=latest['report_sha256']
        row['previous_restore_verified']=any(x[2]['report']['passed'] is True for x in valid[:-1])
