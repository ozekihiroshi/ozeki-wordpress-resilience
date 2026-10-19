import json,sys,types
from pathlib import Path
mode=sys.argv[1]
h=types.ModuleType('helpers')
exec(Path(__file__).with_name('http-test.py').read_text().split("admin=Client('labadmin')")[0],h.__dict__)
h.admin=h.Client('labadmin')
_,body=h.admin.form();checks=[]
def check(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
expected={'unavailable':'unavailable','stale':'stale','invalid':'invalid','future':'invalid','negative':'invalid','oversize':'invalid','current':'current','recovered':'current'}[mode]
check('data-observer-state="'+expected+'"' in body,'observer '+mode+' correctly labelled')
check('NEVER-RENDER-SECRET' not in body and '<script>evil' not in body,'observer excludes secret and injected fields')
if mode=='current':
 check('watchdogの処理完了' in body and '監視ホストへの到達性' in body,'separate watchdog and host rows')
 check('通知失敗・未配送' in body,'independent delivery failure visible')
 check('完了・応答の期限超過' in body and '発生' in body,'active alarm and history visible')
 check(h.Client('labeditor').get(h.PAGE)[0]==403,'editor cannot view observer state')
 check('id="loginform"' in h.Client().get(h.PAGE)[1],'anonymous cannot view observer state')
elif mode=='stale':
 check('現在の状態は不明' in body and '前回記録' in body,'stale report retains history without claiming current health')
elif mode=='recovered':
 check('発報中の警報なし' in body and '解消' in body,'fresh recovery with retained alarm history')
print(json.dumps(checks))
