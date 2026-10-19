import base64,html,json,os,re,sys,types,urllib.request
from pathlib import Path
h=types.ModuleType('helpers');exec(Path(__file__).with_name('http-test.py').read_text().split("admin=Client('labadmin')")[0],h.__dict__)
admin=h.Client('labadmin');PAGE=h.BASE+'/wp-admin/admin.php?page=owr-observer-settings';checks=[]
def check(ok,label):
 if not ok:raise AssertionError(label)
 checks.append(label)
def form(action,url=PAGE):
 code,body=admin.get(url);check(code==200,'independent settings page loads')
 html=next(f for f in re.findall(r'<form\b.*?</form>',body,re.S) if 'value="'+action+'"' in f)
 p=h.Inputs();p.feed(html);return p.values,body
def save(fields=None,url=PAGE):
 f,_=form('owr_observer_save',url);data={k:f[k] for k in ('_wpnonce','revision','channel_id')}
 data.update(action='owr_observer_save',label='Independent iPhone',provider='pushover',profile='push_profile',recipient='Independent operator',enabled='1',retry='60',expire='300')
 data['kinds[]']=['monitor_stopped','heartbeat_invalid','notification_delivery_failed'];data.update(fields or {})
 return admin.post(h.BASE+'/wp-admin/admin-post.php',data),data
def apply():
 f,_=form('owr_observer_apply');return admin.post(h.BASE+'/wp-admin/admin-post.php',f),f
mode=sys.argv[1]
if mode=='request':
 normal=admin.export();Path('/tmp/observer-normal-settings.json').write_text(json.dumps(normal))
 check(h.Client('labeditor').get(PAGE)[0]==403,'editor cannot view independent settings')
 check('id="loginform"' in h.Client().get(PAGE)[1],'anonymous cannot view independent settings')
 check(admin.get(h.BASE+'/wp-admin/admin-post.php?action=owr_observer_save')[0]==405,'independent save rejects GET')
 check(admin.post(h.BASE+'/wp-admin/admin-post.php',dict(action='owr_observer_save'))[0]==403,'independent save requires nonce')
 check(save({'kinds[]':['backup_missing']})[0][0]==400,'ordinary backup alarm rejected for watchdog settings')
 (code,body),saved=save();check(code==200 and '設定候補を保存しました' in body,'independent candidate saved without applying')
 check(admin.post(h.BASE+'/wp-admin/admin-post.php',saved)[0]==409,'stale candidate save rejected')
 f,_=form('owr_observer_apply')
 bad=dict(f,expected_hash='0'*64);check(admin.post(h.BASE+'/wp-admin/admin-post.php',bad)[0]==409,'stale active configuration hash rejected by UI')
 check(h.Client('labeditor').post(h.BASE+'/wp-admin/admin-post.php',f)[0]==403,'editor cannot request independent cutover')
 bad=dict(f);bad.pop('_wpnonce');check(admin.post(h.BASE+'/wp-admin/admin-post.php',bad)[0]==403,'independent cutover requires nonce')
 code,body=admin.post(h.BASE+'/wp-admin/admin-post.php',f);check(code==200 and '反映完了とは扱いません' in body,'queued request is not shown as applied')
 check(admin.post(h.BASE+'/wp-admin/admin-post.php',f)[0]==200,'same cutover request is idempotent')
 check(admin.export()==normal,'ordinary notification settings untouched')
elif mode=='applied':
 _,body=admin.get(PAGE);check('data-observer-settings="applied"' in body,'external applied revision displayed');check('data-apply-outcome="applied"' in body,'external application outcome displayed')
 check('Independent iPhone' in body and '結果不明' not in body,'candidate remains editable')
elif mode=='test-request':
 f,_=form('owr_observer_test');url=h.BASE+'/wp-admin/admin-post.php'
 check(h.Client('labeditor').post(url,f)[0]==403,'editor cannot send independent test')
 bad=dict(f);bad.pop('_wpnonce');check(admin.post(url,bad)[0]==403,'independent test requires nonce')
 check(admin.get(url+'?action=owr_observer_test')[0]==405,'independent test rejects GET')
 for bad in [dict(f,expected_hash='0'*64),dict(f,revision_token='old'),dict(f,channel_id='missing'),dict(f,created_at='1')]:
  check(admin.post(url,bad)[0]==409,'independent test rejects stale or mismatched request')
 code,body=admin.post(url,f);check(code==200 and 'data-observer-test="pending"' in body, 'independent test pending is not delivery success')
 Path('/tmp/observer-test-request.json').write_text(json.dumps(f))
 check(admin.post(url,f)[0]==200,'duplicate queued independent test is idempotent')
 new,_=form('owr_observer_test');check(admin.post(url,new)[0]==429,'independent UI test rate limited')
elif mode=='test-result':
 _,body=admin.get(PAGE);check('data-observer-test="accepted"' in body,'external independent test service acceptance visible')
 f=json.loads(Path('/tmp/observer-test-request.json').read_text());check(f['request_id'] in body,'independent delivery result bound to request id')
elif mode=='test-waiting':
 f=json.loads(Path('/tmp/observer-test-request.json').read_text());_,body=admin.get(PAGE+'&test_id='+f['request_id'])
 check('data-observer-test="pending"' in body,'stopped transfer or worker remains pending')
 check('data-observer-test="accepted"' not in body,'pending test never claims acceptance')
elif mode=='test-worker-stopped':
 _,body=admin.get(PAGE)
 check('外部のテスト処理に異常' in body,'external test processing failure displayed')
 check('value="owr_observer_test"' not in body,'test disabled while worker reports error')
 check('data-observer-delivery="failed"' in body,'regular alarm failure displayed separately')
elif mode=='test-stale':
 _,body=admin.get(PAGE)
 check('前回報告の履歴' in body,'stale accepted result explicitly historical')
 check('value="owr_observer_test"' not in body,'no test request from stale report')
 check('data-observer-test="accepted"' in body,'stale report retains result history')
elif mode=='alarm-with-test':
 _,body=admin.get(PAGE)
 check('data-observer-delivery="failed"' in body and 'data-observer-test="accepted"' in body,'alarm failure and test acceptance coexist without conflation')
elif mode=='disable':
 _,body=admin.get(PAGE);edit=html.unescape(re.search(r'href="([^"]*page=owr-observer-settings[^" ]*edit=[^"]+)"',body).group(1))
 (code,body),_=save({'enabled':'0'},edit);check(code==200 and '無効候補' in body,'disable saved as candidate only')
 check('value="owr_observer_test"' not in body,'unapplied configuration cannot send test')
 (code,body),_=apply();check(code==200,'disable request queued for external policy check')
elif mode=='rejected':
 _,body=admin.get(PAGE);check('data-apply-outcome="rejected"' in body and '外部の許可条件に合わず拒否' in body,'external safety policy rejection visible')
 check('data-observer-settings="pending"' in body,'rejected candidate never appears applied')
 check(admin.export()==json.loads(Path('/tmp/observer-normal-settings.json').read_text()),'ordinary settings unchanged after independent rejection')
 def webdriver(method,path,data=None):
  request=urllib.request.Request('http://127.0.0.1:4444'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=60) as r:return json.load(r)['value']
 session=webdriver('POST','/session',{'capabilities':{'alwaysMatch':{'browserName':'chrome','goog:chromeOptions':{'args':['--headless=new','--no-sandbox','--disable-dev-shm-usage']}}}})['sessionId'];endpoint='/session/'+session
 try:
  webdriver('POST',endpoint+'/url',dict(url=h.BASE+'/wp-login.php'))
  for cookie in admin.cookies:webdriver('POST',endpoint+'/cookie',dict(cookie=dict(name=cookie.name,value=cookie.value,path=cookie.path)))
  for width,height,name in [(1440,1600,'desktop'),(390,844,'mobile')]:
   webdriver('POST',endpoint+'/window/rect',dict(width=width,height=height));webdriver('POST',endpoint+'/url',dict(url=PAGE))
   check(webdriver('POST',endpoint+'/execute/sync',dict(script='return document.documentElement.scrollWidth <= window.innerWidth',args=[])),name+' independent settings has no page overflow')
   Path('/tmp/observer-settings-'+name+'.png').write_bytes(base64.b64decode(webdriver('GET',endpoint+'/screenshot')))
 finally:webdriver('DELETE',endpoint)
else:raise ValueError('mode')
print(json.dumps(checks))
