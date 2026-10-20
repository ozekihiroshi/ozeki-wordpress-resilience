"""Real Chromium rendering of generated-only daily status fixtures."""
import base64,json,os,sys,time,urllib.request
from pathlib import Path
ELEMENT='element-6066-11e4-a52e-4f735466cecf'
class By:
    ID='id';CSS_SELECTOR='css selector';LINK_TEXT='link text';TAG_NAME='tag name'
class Element:
    def __init__(self,driver,value):self.driver=driver;self.ident=value[ELEMENT]
    def call(self,method,path,data=None):return self.driver.call(method,'/element/'+self.ident+path,data)
    @property
    def text(self):return self.call('GET','/text')
    def click(self):return self.call('POST','/click',{})
    def clear(self):return self.call('POST','/clear',{})
    def send_keys(self,text):return self.call('POST','/value',{'text':text})
    def get_attribute(self,name):return self.call('GET','/attribute/'+name)
    def find_elements(self,by,value):return self.driver.elements(by,value,'/element/'+self.ident)
    def is_displayed(self):return self.driver.execute_script('return !!arguments[0].getClientRects().length',self)
class Driver:
    def __init__(self):
        self.endpoint=''
        result=self.call('POST','/session',{'capabilities':{'alwaysMatch':{'browserName':'chrome','goog:chromeOptions':{'args':['--headless=new','--no-sandbox','--disable-dev-shm-usage']}}}})
        self.endpoint='/session/'+result['sessionId']
    def call(self,method,path,data=None):
        req=urllib.request.Request('http://127.0.0.1:4444'+self.endpoint+path,
             data=json.dumps(data).encode() if data is not None else None,
             headers={'Content-Type':'application/json'},method=method)
        with urllib.request.urlopen(req,timeout=60) as response:
            value=json.load(response)['value']
        if isinstance(value,dict) and 'error' in value:raise RuntimeError(value['error'])
        return value
    def get(self,url):self.call('POST','/url',{'url':url})
    @property
    def current_url(self):return self.call('GET','/url')
    def elements(self,by,value,prefix=''):
        if by=='id':by,value='css selector','#'+value
        if by=='tag name':by='css selector'
        return [Element(self,v) for v in self.call('POST',prefix+'/elements',{'using':by,'value':value})]
    def find_elements(self,by,value):return self.elements(by,value)
    def find_element(self,by,value):return self.elements(by,value)[0]
    def set_window_size(self,width,height):self.call('POST','/window/rect',dict(width=width,height=height))
    def execute_script(self,script,*args):
        return self.call('POST','/execute/sync',dict(script=script,args=[{ELEMENT:a.ident} if isinstance(a,Element) else a for a in args]))
    def execute_async_script(self,script):return self.call('POST','/execute/async',dict(script=script,args=[]))
    def delete_all_cookies(self):self.call('DELETE','/cookie')
    def refresh(self):self.call('POST','/refresh',{})
    def save_screenshot(self,path):Path(path).write_bytes(base64.b64decode(self.call('GET','/screenshot')))
    def quit(self):self.call('DELETE','')
class WebDriverWait:
    def __init__(self,driver,seconds):self.driver=driver;self.seconds=seconds
    def until(self,condition):
        end=time.monotonic()+self.seconds
        while not condition(self.driver):
            if time.monotonic()>end:raise TimeoutError('browser condition')
            time.sleep(.2)
mode=sys.argv[1];checks=[]
deadline=time.monotonic()+45
while True:
    try:
        driver=Driver();break
    except Exception:
        if time.monotonic()>deadline:raise
        time.sleep(1)
page='http://127.0.0.1/wp-admin/admin.php?page=owr-daily-status'
def check(value,label):
    if not value:raise AssertionError(label)
    checks.append(label)
def login(user):
    driver.get('http://127.0.0.1/wp-login.php?lab='+str(time.time_ns()))
    driver.find_element(By.ID,'user_login').clear()
    driver.find_element(By.ID,'user_pass').clear()
    driver.find_element(By.ID,'user_login').send_keys(user)
    driver.find_element(By.ID,'user_pass').send_keys(os.environ['LAB_ADMIN_PASSWORD'])
    driver.find_element(By.ID,'wp-submit').click()
    try:WebDriverWait(driver,20).until(lambda d:'wp-login.php' not in d.current_url)
    except TimeoutError:
        errors=driver.find_elements(By.ID,'login_error')
        raise RuntimeError('Login did not complete: '+(' | '.join(e.text for e in errors) or 'no login error displayed'))
try:
    driver.set_window_size(1440,1100)
    driver.get(page);check(bool(driver.find_elements(By.ID,'loginform')),'anonymous redirected to login')
    login('labadmin')
    # Navigate via the actual WordPress sidebar.
    driver.get('http://127.0.0.1/wp-admin/admin.php?page=owr-notifications')
    driver.find_element(By.LINK_TEXT,'日次バックアップ・復元').click()
    WebDriverWait(driver,20).until(lambda d:bool(d.find_elements(By.CSS_SELECTOR,'[data-daily-state]')))
    expected='current' if mode in ('current','matrix') else mode
    check(driver.find_element(By.CSS_SELECTOR,'[data-daily-state]').get_attribute('data-daily-state')==expected,'browser state '+mode)
    content=driver.find_element(By.CSS_SELECTOR,'#wpbody-content .wrap')
    text=content.text
    check('読取り専用' in text,'read-only explanation visible')
    check(not content.find_elements(By.CSS_SELECTOR,'form,button,input,select'),'no mutation controls in status page')
    check('NEVER-RENDER-SECRET' not in text,'unknown secret omitted')
    if mode=='matrix':
        for label in ('途中停止・結果不明','後片付け未完了','後片付け確認済み','復元検証済み','復元処理で資源削除済み'):
            check(label in text,'visible '+label)
        driver.save_screenshot('/tmp/daily-desktop.png')
        driver.set_window_size(390,844)
        check(driver.execute_script('return document.documentElement.scrollWidth<=window.innerWidth+1'),'mobile document fits viewport')
        table=driver.find_elements(By.CSS_SELECTOR,'.wrap table')[1]
        driver.execute_script('arguments[0].scrollIntoView({block:"center"});',table)
        check(table.is_displayed(),'mobile history table visible')
        check(driver.execute_script('const p=arguments[0].parentElement;p.scrollLeft=p.scrollWidth;return p.scrollLeft>0;',table),'mobile table scrolls horizontally')
        driver.save_screenshot('/tmp/daily-mobile.png')
        driver.set_window_size(1440,1100)
    if mode=='stale':check('現在の状態は不明' in text and '前回記録' in text,'stale not presented as current')
    if mode in ('current','matrix'):
        status=driver.execute_async_script("""
          const done=arguments[arguments.length-1];
          fetch(location.href,{method:'POST',credentials:'same-origin',body:new URLSearchParams({action:'cleanup-reviewed'})})
          .then(r=>done(r.status)).catch(()=>done(-1));
        """)
        check(status==405,'browser POST refused 405')
        driver.refresh()
        check(bool(driver.find_elements(By.CSS_SELECTOR,'[data-daily-state="current"]')),'refresh remains read-only view')
    driver.delete_all_cookies();login('labeditor');driver.get(page)
    check(not driver.find_elements(By.CSS_SELECTOR,'[data-daily-state]'),'editor cannot read status')
    check('日次バックアップ・隔離復元' not in driver.find_element(By.TAG_NAME,'body').text,'no data in permission error')
    check(not driver.find_elements(By.LINK_TEXT,'日次バックアップ・復元'),'editor menu not exposed')
    print(json.dumps(dict(mode=mode,checks=checks,passed=True)))
finally:driver.quit()
