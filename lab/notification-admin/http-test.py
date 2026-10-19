import base64,http.cookiejar,json,os,re,sys,urllib.request,urllib.parse,urllib.error
from html.parser import HTMLParser
from pathlib import Path
BASE='http://127.0.0.1'
PAGE=BASE+'/wp-admin/admin.php?page=owr-notifications'
checks=[]
def check(condition,label):
    if not condition:raise RuntimeError(label)
    checks.append(label)
class Inputs(HTMLParser):
    def __init__(self):super().__init__();self.values={}
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='input' and values.get('name') not in self.values:self.values[values.get('name')]=values.get('value','')
class Client:
    def __init__(self,user=None):
        self.cookies=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))
        if user:
            self.get(BASE+'/wp-login.php')
            code,body=self.post(BASE+'/wp-login.php',dict(log=user,pwd=os.environ['LAB_ADMIN_PASSWORD'],redirect_to=PAGE,testcookie='1'))
            if user=='labadmin':check(code==200 and 'Resilience — 通知' in body,'administrator login')
    def request(self,url,data=None):
        try:
            with self.opener.open(url,data=data,timeout=20) as response:return response.status,response.read().decode()
        except urllib.error.HTTPError as e:return e.code,e.read().decode()
    def get(self,url):return self.request(url)
    def post(self,url,fields):return self.request(url,urllib.parse.urlencode(fields,doseq=True).encode())
    def form(self,url=PAGE):
        code,body=self.get(url);check(code==200,'admin page loads');p=Inputs();p.feed(body);return p.values,body
    def save(self,extra,form=None):
        fields,_=self.form() if form is None else (form,'')
        data={k:fields[k] for k in ('_wpnonce','revision','channel_id')}
        data.update(action='owr_notification_save',label='Main iPhone',profile='push_profile',recipient='Test iPhone',provider='pushover',enabled='1',retry='60',expire='300')
        data['kinds[]']=['backup_missing','restore_failed','approval_expired'];data.update(extra)
        return self.post(BASE+'/wp-admin/admin-post.php',data)
    def export(self):
        _,body=self.get(PAGE)
        forms=re.findall(r'<form\b.*?</form>',body,re.S)
        form=next(f for f in forms if 'owr_notification_export' in f)
        p=Inputs();p.feed(form)
        code,body=self.post(BASE+'/wp-admin/admin-post.php',dict(action='owr_notification_export',_wpnonce=p.values['_wpnonce']))
        check(code==200,'settings export succeeds');return json.loads(body)

admin=Client('labadmin')
mode=sys.argv[1]
if mode=='settings':
    initial,body=admin.form();check('data-status="unavailable"' in body,'missing status not healthy');check('data-owr-development-scope="true"' in body,'development scope and external dependency shown')
    anonymous=Client();code,body=anonymous.get(PAGE);check('id="loginform"' in body,'anonymous cannot view settings')
    editor=Client('labeditor');check(editor.get(PAGE)[0]==403,'editor cannot view settings')
    check(editor.post(BASE+'/wp-admin/admin-post.php',dict(action='owr_notification_save',_wpnonce=initial['_wpnonce']))[0]==403,'editor cannot save')
    check(admin.post(BASE+'/wp-admin/admin-post.php',dict(action='owr_notification_save'))[0]==403,'missing nonce rejected')
    check(admin.get(BASE+'/wp-admin/admin-post.php?action=owr_notification_save')[0]==405,'GET mutation rejected')
    for fields,label in [({'provider':'line'},'unsupported provider rejected'),({'kinds[]':[]},'empty alarms rejected'),({'label':'<script>alert(1)</script>'},'HTML input rejected'),({'profile':'../secret'},'profile path rejected'),({'retry':'1'},'invalid retry rejected'),({'provider':'smtp_tls','recipient':'a@example.invalid\r\nBcc:b@example.invalid'},'email header injection rejected')]:
        check(admin.save(fields)[0]==400,label)
    check(admin.save({})[0]==200,'first destination saved')
    check(admin.save({},initial)[0]==409,'stale revision rejected')
    check(admin.save(dict(label='History mail',provider='smtp_starttls',profile='mail_profile',recipient='operator@example.invalid'))[0]==200,'second destination saved')
    settings=admin.export();check(len(settings['channels'])==2,'two destinations retained')
    first=settings['channels'][0]['id'];before=settings['revision']
    edit,body=admin.form(PAGE+'&edit='+first)
    check(admin.save({'enabled':'0'},edit)[0]==200,'destination disabled without deletion')
    settings=admin.export();check(settings['channels'][0]['id']==first and not settings['channels'][0]['enabled'],'stable id retained')
    edit,_=admin.form(PAGE+'&edit='+first);check(admin.save({'enabled':'1'},edit)[0]==200,'destination enabled as requested configuration')
    settings=admin.export();check(settings['revision']==before+2,'revision increments')
    check('token' not in json.dumps(settings).replace('revision_token','revision_ref') and 'password' not in json.dumps(settings),'export contains no credential values')
    Path('/tmp/owr-settings.json').write_text(json.dumps(settings))
elif mode=='status':
    _,body=admin.form();check('data-status="connected"' in body,'worker report bound to current settings')
    check('配送が拒否されました' in body,'delivery rejection visible')
    check('サービス受付: 1' in body,'provider acceptance visible')
    check('確認待ち: 1' in body,'human acknowledgement separate from acceptance')
    check('専用環境・模擬配送' in body,'simulation clearly labelled')
    check('NEVER-RENDER-SECRET' not in body,'extra report fields not rendered')
    def webdriver(method,path,data=None):
        request=urllib.request.Request('http://127.0.0.1:4444'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=60) as response:return json.load(response)['value']
    session=webdriver('POST','/session',{'capabilities':{'alwaysMatch':{'browserName':'chrome','goog:chromeOptions':{'args':['--headless=new','--no-sandbox','--disable-dev-shm-usage']}}}})['sessionId']
    endpoint='/session/'+session
    try:
        webdriver('POST',endpoint+'/window/rect',dict(width=1440,height=1600))
        webdriver('POST',endpoint+'/url',dict(url=BASE+'/wp-login.php'))
        for cookie in admin.cookies:
            webdriver('POST',endpoint+'/cookie',dict(cookie=dict(name=cookie.name,value=cookie.value,path=cookie.path)))
        webdriver('POST',endpoint+'/url',dict(url=PAGE))
        check('Resilience — 通知' in webdriver('POST',endpoint+'/execute/sync',dict(script='return document.querySelector("h1").textContent',args=[])),'browser renders admin page')
        check(webdriver('POST',endpoint+'/execute/sync',dict(script='return document.documentElement.scrollWidth <= window.innerWidth',args=[])),'desktop has no horizontal overflow')
        Path('/tmp/owr-admin.png').write_bytes(base64.b64decode(webdriver('GET',endpoint+'/screenshot')))
        webdriver('POST',endpoint+'/window/rect',dict(width=390,height=844))
        webdriver('POST',endpoint+'/url',dict(url=PAGE))
        Path('/tmp/owr-admin-mobile.png').write_bytes(base64.b64decode(webdriver('GET',endpoint+'/screenshot')))
        check(webdriver('POST',endpoint+'/execute/sync',dict(script='return document.documentElement.scrollWidth <= window.innerWidth',args=[])),'mobile has no page overflow')
    finally:
        webdriver('DELETE',endpoint)
elif mode=='test-request':
    _,body=admin.get(PAGE)
    form=next(f for f in re.findall(r'<form\b.*?</form>',body,re.S) if 'owr_notification_test' in f)
    parser=Inputs();parser.feed(form);fields=parser.values;fields.pop(None,None)
    endpoint=BASE+'/wp-admin/admin-post.php'
    editor=Client('labeditor');check(editor.post(endpoint,fields)[0]==403,'editor cannot request test')
    no_nonce=dict(fields);no_nonce.pop('_wpnonce');check(admin.post(endpoint,no_nonce)[0]==403,'test requires nonce')
    check(admin.get(endpoint+'?action=owr_notification_test')[0]==405,'test rejects GET')
    check(admin.post(endpoint,dict(fields,revision_token='stale'))[0]==409,'test rejects stale settings')
    check(admin.post(endpoint,dict(fields,channel_id='missing'))[0]==409,'test rejects unknown channel')
    code,body=admin.post(endpoint,fields);check(code==200 and '外部配送の処理待ち' in body,'test enqueued without claiming delivery')
    check(admin.post(endpoint,fields)[0]==200,'same request submission is idempotent')
    _,body=admin.get(PAGE);form=next(f for f in re.findall(r'<form\b.*?</form>',body,re.S) if 'owr_notification_test' in f)
    parser=Inputs();parser.feed(form);parser.values.pop(None,None)
    check(admin.post(endpoint,parser.values)[0]==429,'test button rate limited')
elif mode=='test-result':
    _,body=admin.form();check('テスト：サービス受付（端末で確認してください）' in body,'external test result displayed separately from device confirmation')
    check('確認待ち: 1' in body,'old receipt still visible after configuration migration')
elif mode in ('stale','invalid','pending'):
    _,body=admin.form();check('data-status="'+mode+'"' in body,mode+' report cannot appear current')
else:raise RuntimeError('unknown mode')
print(json.dumps(checks))
