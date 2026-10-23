import base64,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
base=Path('/kit/lab/notification-admin/preflight-browser.py').read_text().split('mode=')[0].replace("'http://127.0.0.1:4444'+self.endpoint","'http://127.0.0.1:9515'+self.endpoint").replace("return self.call('GET','/attribute/'+name)","return self.call('GET',('/property/' if name=='value' else '/attribute/')+name)")
base=base.replace('with urllib.request.urlopen(req,timeout=60) as response:', 'with diagnostic_open(req,timeout=60) as response:')
def diagnostic_open(req,timeout):
    try:return urllib.request.urlopen(req,timeout=timeout)
    except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from e
exec(base);lab=Path('/lab');checks=[];control=lab/'control.json'
subprocess.Popen(['chromedriver','--port=9515','--allowed-ips=127.0.0.1'],stdout=open('/lab/chromedriver.log','w'),stderr=subprocess.STDOUT)
for i in range(60):
    try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1);break
    except Exception:time.sleep(.2)
d=Driver();d.set_window_size(1280,1000);root='http://127.0.0.1'
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name);(lab/'checks.json').write_text(json.dumps(checks));print('PASS '+name,flush=True)
def field(id,text):e=d.find_element(By.ID,id);e.clear();e.send_keys(text)
def fetch(route,body=None):
    return d.call('POST','/execute/async',dict(script="const done=arguments[arguments.length-1];fetch(arguments[0],{method:arguments[1]===null?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-WP-Nonce':(window.owrRecoveryConfig||window.owrMaterialsConfig).nonce},body:arguments[1]===null?undefined:JSON.stringify(arguments[1])}).then(async r=>done({status:r.status,body:await r.json()})).catch(e=>done({error:String(e)}));",args=[root+'/?rest_route='+route,body]))
def state():return fetch('/owr-materials/v1/state')['body']
def snapshot():return fetch('/owr-test/v1/snapshot')['body']
def wait(kind,seconds=1200):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        e=d.find_elements(By.ID,'owr-material-status')
        if e and e[0].get_attribute('data-state')==kind:return
        time.sleep(.3)
    raise RuntimeError('Expected '+kind+'; observed '+(e[0].text if e else 'no status'))
def choose(id):d.execute_script("const e=document.getElementById('owr-material-select');e.value=arguments[0];e.dispatchEvent(new Event('change'));",id)
def save():d.find_element(By.ID,'owr-material-save').click()
try:
    d.get(root+'/wp-login.php');field('user_login','operator');field('user_pass','lab-only-password');d.find_element(By.ID,'wp-submit').click()
    d.get(root+'/wp-admin/post-new.php');wait('ready');check('normal new-post entry opens S3-first editor','page=owr-site-materials' in d.current_url)
    before=snapshot();original=state();choose('company');field('owr-material-title','編集した会社案内');field('owr-material-body','## 見出し\n編集前にS3へ保存する本文\n[サービス](asset:services)\n![画像](asset:logo)')
    check('typing leaves WordPress unchanged',snapshot()==before)
    control.write_text(json.dumps({'fail_before':True}));save();wait('failed');check('save failure leaves posts and media unchanged',snapshot()==before)
    conflict=json.loads(json.dumps(original['site']));conflict['title']='競合する要求'
    check('different pending request rejected',fetch('/owr-materials/v1/save',{'site':conflict,'parent':original['receipt']})['status']==409)
    d.refresh();wait('failed');check('reload preserves exact pending title',d.find_element(By.ID,'owr-material-title').get_attribute('value')=='編集した会社案内')
    if (lab/'plugin.zip').exists():
        update=fetch('/owr-test/v1/upgrade',{});print('Lifecycle update response '+json.dumps(update),flush=True)
        check('ZIP update preserves pending save and settings',update['body'].get('state')=='PASS');d.refresh();wait('failed')
    control.write_text('{}');d.find_element(By.ID,'owr-material-resume').click();wait('ready');after=snapshot();check('confirmed save updates WordPress',after!=before and any(x['title']=='編集した会社案内' for x in after['posts']))
    check('stale editor generation rejected',fetch('/owr-materials/v1/save',{'site':conflict,'parent':original['receipt']})['status']==409)
    for kind in ['post','page']:
        d.find_element(By.ID,'owr-add-'+kind).click();field('owr-material-title','追加した'+kind);field('owr-material-slug','added-'+kind);field('owr-material-body','新しい本文');save();wait('ready');check('new '+kind+' reflected after S3',any(x['title']=='追加した'+kind for x in snapshot()['posts']))
    d.get(root+'/wp-admin/media-new.php');wait('ready');check('normal media entry opens S3-first registration','page=owr-site-materials' in d.current_url)
    before=snapshot();d.find_element(By.ID,'owr-add-image').click();field('owr-material-title','登録した画像');d.find_element(By.ID,'owr-material-file').send_keys('/lab/normal.png');check('selecting image creates no attachment',snapshot()==before);save();wait('ready');check('image registered after S3',len(snapshot()['images'])==len(before['images'])+1)
    image_id=d.find_element(By.ID,'owr-material-select').get_attribute('value');field('owr-material-title','差し替えた画像');d.find_element(By.ID,'owr-material-file').send_keys('/lab/replacement.png');save();wait('ready');check('image replacement keeps logical ID',any(x['id']==image_id and x['alt']=='差し替えた画像' for x in state()['site']['entries']))
    choose('company');field('owr-material-body','途中停止後も同じ世代で再開する本文\n![新画像](asset:'+image_id+')');before=snapshot();control.write_text(json.dumps({'stop_after_store':True}));save()
    end=time.monotonic()+1200
    while time.monotonic()<end and not (lab/'worker-paused.json').exists():time.sleep(.3)
    check('worker actually exited after S3 commit',(lab/'worker-paused.json').exists());check('commit without projection leaves WordPress unchanged',snapshot()==before)
    paused=json.loads((lab/'worker-paused.json').read_text());d.save_screenshot('/lab/after-s3-before-apply.png');control.write_text('{}');d.find_element(By.ID,'owr-material-resume').click();wait('ready');check('resumes committed generation',state()['receipt']==paused['head']);check('resumed content appears',any('途中停止後も同じ世代' in x['content'] for x in snapshot()['posts']))
    before=snapshot();check('ordinary REST post write rejected',fetch('/wp/v2/posts',{'title':'Bypass'})['status']==409);check('ordinary REST image write rejected',fetch('/wp/v2/media',{})['status']==409);check('bypass attempts change nothing',snapshot()==before)
    check('read-only status does not change content',state() is not None and snapshot()==before)
    credentials=json.loads((lab/'subscriber.json').read_text());headers={'Cookie':credentials['cookie'],'X-WP-Nonce':credentials['nonce']}
    for path in ['state','save']:
        req=urllib.request.Request(root+'/?rest_route=/owr-materials/v1/'+path,headers=headers,data=b'{}' if path=='save' else None)
        try:urllib.request.urlopen(req);code=200
        except urllib.error.HTTPError as e:code=e.code
        check('subscriber denied '+path,code==403)
    if (lab/'recovery-enabled').exists():
        exec(Path('/kit/lab/site-materials-editor/recovery-checks.py').read_text())
        if (lab/'plugin.zip').exists():
            control.write_text(json.dumps({'pause_recovery':True}));time.sleep(6)
            update=fetch('/owr-test/v1/upgrade',{})
            check('ZIP reinstall preserves reconstruction report and requests',update['body'].get('state')=='PASS')
            control.write_text('{}')
    d.save_screenshot('/lab/editor-complete.png');(lab/'browser-result.json').write_text(json.dumps({'state':'PASS','checks':checks,'final':state()},ensure_ascii=False));print(json.dumps({'state':'PASS','checks':len(checks)}))
finally:d.quit()
