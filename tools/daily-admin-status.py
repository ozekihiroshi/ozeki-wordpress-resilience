#!/usr/bin/env python3
"""Export a bounded, read-only daily/recovery view; never runs a worker."""
import argparse,importlib.util,json,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('daily',ROOT/'tools/first-site-daily.py')
d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
def snapshot(root,site):
    root=Path(root).resolve()
    if not (root/'daily.sqlite').is_file():raise ValueError('existing daily ledger required')
    status=d.Coordinator(root).status(d.gate.now())
    runs=[]
    for row in status['runs'][-30:]:
        runs.append({k:row.get(k) for k in ('day','phase','storage_complete','approval_state','restore_state')})
    attempts=[]
    with sqlite3.connect((root/'daily.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='recovery_attempts'").fetchone():
            for row in db.execute('SELECT request_id,day,state,outcome,registration,report_hash FROM recovery_attempts ORDER BY n DESC LIMIT 30'):
                value=dict(row);value.pop('report_hash');base=root/'recovery-attempts'/row['request_id']
                cleanup='not_recorded'
                try:
                    receipt=base/'cleanup-review.json';progress=base/'cleanup-progress.json'
                    if receipt.exists():
                        r=json.loads(receipt.read_bytes())
                        cleanup='closed' if r['request_id']==row['request_id'] and r['resources_removed'] is True and row['state']=='reviewed_closed' else 'invalid'
                    elif progress.exists():cleanup='incomplete'
                    elif row['state']=='reviewed_closed':cleanup='invalid'
                    elif row['state']=='finished' and row['outcome']=='succeeded':
                        raw=(base/'result.json').read_bytes()
                        r=json.loads(raw)
                        cleanup='automatic_removed' if d.gate.sha(raw)==row['report_hash'] and r.get('isolated_restore',{}).get('resources_removed') is True else 'invalid'
                except (ValueError,KeyError,OSError,TypeError):cleanup='invalid'
                value['cleanup']=cleanup;attempts.append(value)
    return dict(format='owr-daily-admin-v1',site_id=site,observed_at=d.gate.now().isoformat(),
                missing_due_slot=status['missing_due_slot'],runs=runs,attempts=attempts)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',required=True);p.add_argument('--site-id',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();root=Path(a.state).resolve();out=Path(a.output).resolve()
    if out.is_relative_to(root):raise ValueError('export outside source state required')
    d.io.write_json(out,snapshot(root,a.site_id))
