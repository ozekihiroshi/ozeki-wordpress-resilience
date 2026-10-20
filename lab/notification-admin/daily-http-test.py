import json,sys,types
from pathlib import Path
h=types.ModuleType('helpers')
exec(Path('/lab/http-test.py').read_text().split("admin=Client('labadmin')")[0],h.__dict__)
admin=h.Client('labadmin');page=h.BASE+'/wp-admin/admin.php?page=owr-daily-status'
mode=sys.argv[1];code,body=admin.get(page)
assert code==200
expected=mode if mode in ('current','stale','unavailable') else 'invalid'
assert 'data-daily-state="'+expected+'"' in body,(mode,body[-1500:])
assert 'NEVER-RENDER-SECRET' not in body and '<script>evil' not in body
assert 'cleanup-reviewed' not in body and '<form' not in body.split('<h1>日次バックアップ')[1]
if mode=='current':
    assert '復元検証済み' in body and '後片付け確認済み' in body
    assert 'interrupted-01' in body and 'fresh-02' in body
    assert h.Client('labeditor').get(page)[0]==403
    assert 'id="loginform"' in h.Client().get(page)[1]
    post_code,post_body=admin.post(page,{})
    assert post_code==405,('POST response',post_code,post_body[-500:])
    # WP core can dispatch an unknown action before this page callback.
    # It must not create any request; the harness hashes all source state.
    admin.post(page,dict(action='cleanup-reviewed'))
print(json.dumps(dict(mode=mode,passed=True)))
