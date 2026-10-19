"""Fail-closed assessment of one coordinated DB/files capture observation.

This assesses evidence, not source-host truth or malware cleanliness.
"""
import argparse,json,re
from pathlib import Path

def assess(record, expected_writers):
    reasons=[]
    def result(state):
        return {'state':state,'eligible_for_consistency_acceptance':state=='consistent',
                'reasons':reasons,'production_recovery_approved':False,
                'claim':'coordinated capture evidence only; source integrity not attested'}
    try:
        if not expected_writers or len(expected_writers)!=len(set(expected_writers)):
            raise ValueError('Independent nonempty writer scope required')
        if record['format']!='owr-capture-consistency-v1':raise ValueError('Unknown format')
        if not record['attempt_id'] or not record['site_id']:raise ValueError('Missing target')
        for field in ['generation_before','generation_after']:
            if type(record[field]) is not int or record[field]<0:raise ValueError('Invalid generation')
        for field in ['file_inventory_before','file_inventory_after','captured_file_inventory']:
            inventory=record[field]
            if not isinstance(inventory,dict) or not inventory:raise ValueError('Missing inventory')
            if any(not isinstance(k,str) or not k or not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v) for k,v in inventory.items()):raise ValueError('Invalid inventory')
        assets=record['assets']
        if set(assets)!={'database','files'}:raise ValueError('Missing capture outputs')
        for asset in assets.values():
            if asset['attempt_id']!=record['attempt_id'] or asset['site_id']!=record['site_id']:
                reasons.append('mixed_capture_attempt_or_target');return result('inconsistent')
            if (asset['completed'] is not True or type(asset['exit_code']) is not int
                or asset['exit_code']!=0 or type(asset['bytes']) is not int or asset['bytes']<=0
                or not re.fullmatch('[a-f0-9]{64}',asset['sha256'])):
                reasons.append('incomplete_or_failed_stream');return result('capture_failed')
        if record['release_confirmed'] is not True:
            reasons.append('source_release_unconfirmed');return result('capture_failed')
        if (record['file_inventory_before']!=record['file_inventory_after']
            or record['file_inventory_before']!=record['captured_file_inventory']
            or record['generation_before']!=record['generation_after']
            or record['references_match'] is not True):
            reasons.append('source_changed_or_reference_mismatch');return result('inconsistent')
        barrier=record['barrier']
        if (barrier['scope_complete'] is not True
            or set(barrier['writers'])!=set(expected_writers)
            or any(w['fenced'] is not True or type(w['inflight']) is not int or w['inflight']!=0
                   for w in barrier['writers'].values())):
            reasons.append('writer_scope_not_quiescent');return result('unverified')
        if (not isinstance(barrier['token'],str) or not barrier['token'] or barrier['token']!=record['end_token']
            or barrier['held_through_verification'] is not True
            or record['phases']!=['fence','drain','snapshot','copy','verify','release']):
            reasons.append('capture_window_not_protected');return result('unverified')
        if (record['db_snapshot_consistent'] is not True or record['schema_stable'] is not True
            or not record['file_inventory_before']):
            reasons.append('snapshot_or_inventory_unverified');return result('unverified')
        return result('consistent')
    except (KeyError,TypeError,ValueError,AttributeError):
        reasons.append('missing_or_invalid_evidence');return result('unverified')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--record',type=Path,required=True)
    p.add_argument('--writer',action='append',required=True,help='Independent expected writer inventory; repeat for each writer')
    a=p.parse_args()
    try:r=assess(json.loads(a.record.read_text()),a.writer)
    except (OSError,ValueError):r={'state':'unverified','eligible_for_consistency_acceptance':False,'reasons':['unreadable_record']}
    print(json.dumps(r));return 0 if r['eligible_for_consistency_acceptance'] else 1
if __name__=='__main__':raise SystemExit(main())
