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
def check(value,label):
 if not value:raise AssertionError(label)
 checks.append(label)
end=time.monotonic()+45
while True:
 try:driver=Driver();break
 except Exception:
  if time.monotonic()>end:raise
  time.sleep(1)
page='http://127.0.0.1/wp-admin/admin.php?page=owr-preflight'
def login(user):
 driver.delete_all_cookies()
 driver.set_window_size(1440,1000)
 driver.get('http://127.0.0.1/wp-login.php?trial='+str(time.time_ns()))
 for key,value in [('user_login',user),('user_pass',os.environ['LAB_ADMIN_PASSWORD'])]:
  e=driver.find_element(By.ID,key);e.clear();e.send_keys(value)
 driver.find_element(By.ID,'wp-submit').click()
 try:WebDriverWait(driver,30).until(lambda d:'wp-login.php' not in d.current_url)
 except TimeoutError:
  error=driver.find_elements(By.ID,'login_error')
  raise RuntimeError('login failed user='+user+' url='+driver.current_url+' error='+(' | '.join(e.text for e in error)))
try:
 driver.set_window_size(1440,1000)
 driver.get(page);check(bool(driver.find_elements(By.ID,'loginform')),'anonymous requires login')
 login('labadmin');driver.get(page)
 try:WebDriverWait(driver,15).until(lambda d:bool(d.find_elements(By.LINK_TEXT,'導入前検査')))
 except TimeoutError:raise AssertionError('admin page not ready: '+driver.current_url+' body='+driver.find_element(By.TAG_NAME,'body').text)
 check(bool(driver.find_elements(By.LINK_TEXT,'導入前検査')),'admin menu present')
 # Real periodic publication writes report and health separately. A bounded wait
 # accepts only convergence, never replaces persistent mismatch with success.
 settling=[];deadline=time.monotonic()+15
 while mode!='inconsistent' and driver.find_element(By.CSS_SELECTOR,'[data-preflight-transfer]').get_attribute('data-preflight-transfer')=='inconsistent' and time.monotonic()<deadline:
  settling.append('inconsistent');time.sleep(.5);driver.refresh()
 content=driver.find_element(By.CSS_SELECTOR,'#wpbody-content .wrap');text=content.text
 expected='stopped' if mode=='stopped' else ('inconsistent' if mode=='inconsistent' else ('acquisition_failed' if mode=='acquisition_failed' else ('transfer_failed' if mode=='transfer_failed' else 'ok')))
 check(driver.find_element(By.CSS_SELECTOR,'[data-preflight-transfer]').get_attribute('data-preflight-transfer')==expected,'transfer '+expected+' actual='+driver.find_element(By.CSS_SELECTOR,'[data-preflight-transfer]').get_attribute('data-preflight-transfer')+' body='+text)
 if mode=='acquisition_failed':check('取得失敗・取得不可' in text,'acquisition failure shown')
 if mode=='transfer_failed':check('受渡しに失敗' in text,'publication failure distinguished')
 if mode=='stopped':check('5分以上確認できません' in text and '現在の状態は未確認' in text,'stopped and stale shown')
 if mode in ('restarted','recovered','ok'):check('定期取得・受渡しは成功' in text,'recovery shown')
 check('読取り専用' in text and not content.find_elements(By.CSS_SELECTOR,'form,button,input,select'),'read-only controls absent')
 driver.save_screenshot('/tmp/preflight-'+mode+'.png')
 driver.set_window_size(390,844)
 check(driver.execute_script('return document.documentElement.scrollWidth <= window.innerWidth+2'),'mobile no page overflow')
 if mode=='ok':driver.save_screenshot('/tmp/preflight-mobile.png')
 response=driver.execute_async_script("const done=arguments[0];fetch(location.href,{method:'POST',credentials:'same-origin'}).then(async r=>done({status:r.status,text:await r.text()})).catch(e=>done({error:true}));")
 check(response.get('status')==405,'POST returns405')
 driver.delete_all_cookies();login('labeditor');driver.get(page)
 check(not driver.find_elements(By.CSS_SELECTOR,'[data-preflight-state]'),'editor cannot read report')
 check(not driver.find_elements(By.LINK_TEXT,'導入前検査'),'editor has no menu')
 print(json.dumps(dict(mode=mode,checks=checks,publication_settling=settling)))
finally:driver.quit()
