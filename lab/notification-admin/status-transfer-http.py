import json,sys,types
from pathlib import Path
h=types.ModuleType('helpers')
exec(Path('/lab/http-test.py').read_text().split("admin=Client('labadmin')")[0],h.__dict__)
page=h.BASE+'/wp-admin/admin.php?page=owr-daily-status'
c=h.Client('labadmin');mode=sys.argv[1]
code,body=c.get(page)
assert code==200 and 'data-daily-transfer="'+mode+'"' in body
if mode in ('transfer_failed','source_failed','source_stale'):assert '前回記録' in body or '最後に取得した記録' in body
if mode=='stopped':assert '現在の状態は不明' in body
assert c.post(page,{})[0]==405
assert h.Client('labeditor').get(page)[0]==403
print(json.dumps(dict(state=mode,passed=True)))
