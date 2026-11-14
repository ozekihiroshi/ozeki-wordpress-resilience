import json, sys
from pathlib import Path
summary=json.loads(Path(sys.argv[1]).read_text())
expected_hash='e9eacd49757cb10851c0bdeb92bec9c58f97e95592158bfdd5673d62969dc41f'
assert set(summary)=={'A','B','C','D'}
for case,r in summary.items():
    assert r['source']['hash']==expected_hash, (case,'fixture bytes')
    assert r['source']['image_http']==('403' if case in ['B','C'] else '200')
    assert r['recovery_objects_unchanged']
    if case=='B':
        assert any(h['type']=='owr_media_access' for h in r['source']['history']), 'Condition-only change missing from formal history'
    for phase in ['first_recovery','after_resave','second_recovery']:
        x=r[phase]
        assert not x['pending'] and not x['related_pending'], (case,phase,'pending')
        assert x['member_body_visible'], (case,phase,'member page use')
        assert x['anonymous_body_visible']==(case!='D'), (case,phase,'page membership')
        if case in ['B','C']:
            assert x['image_http']=='404' and not x['file_exists'] and x['held_hash']==expected_hash, (case,phase,'private bytes')
        else:
            assert x['image_http']=='200' and x['hash']==expected_hash, (case,phase,'public image')
    for phase in ['after_resave','second_recovery']:
        assert 'RESAVED' in r[phase]['body'], (case,phase,'saved edit absent')
print('PASS A/B/C/D: use, exact public/held bytes, formal history, resave and second recovery')