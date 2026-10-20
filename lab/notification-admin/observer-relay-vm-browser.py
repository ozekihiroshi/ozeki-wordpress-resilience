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
mode=sys.argv[1];expected=json.loads(sys.argv[2])
deadline=time.monotonic()+90
while True:
 try:
  with urllib.request.urlopen('http://127.0.0.1:4444/status',timeout=3) as response:ready=json.load(response)['value']['ready']
  if ready:break
 except (OSError,ValueError,KeyError):pass
 if time.monotonic()>=deadline:raise TimeoutError('Selenium readiness deadline')
 time.sleep(1)
driver=Driver()
page='http://127.0.0.1/wp-admin/admin.php?page=owr-daily-watchdog'
try:
 driver.set_window_size(1440,1200);driver.get('http://127.0.0.1/wp-login.php')
 for field,value in [('user_login','labadmin'),('user_pass',os.environ['LAB_ADMIN_PASSWORD'])]:
  e=driver.find_element(By.ID,field);e.clear();e.send_keys(value)
 driver.find_element(By.ID,'wp-submit').click();WebDriverWait(driver,30).until(lambda d:'wp-login.php' not in d.current_url)
 driver.get(page)
 for role,want in expected.items():
  actual=driver.find_element(By.CSS_SELECTOR,'#owr-daily-watchdog-'+role+' [data-observer-state]').get_attribute('data-observer-state')
  assert actual==want['report'],(role,actual,want)
  actual=driver.find_element(By.CSS_SELECTOR,'[data-transfer-role="'+role+'"]') .get_attribute('data-transfer-state')
  assert actual==want['transfer'],(role,actual,want)
  body=driver.find_element(By.ID,'owr-daily-watchdog-'+role).text
  for word in want.get('text',[]):assert word in body,(role,word,body)
 content=driver.find_element(By.CSS_SELECTOR,'#wpbody-content .wrap')
 assert not content.find_elements(By.CSS_SELECTOR,'form,button,input,select')
 assert driver.execute_async_script("const cb=arguments[arguments.length-1];fetch(location.href,{method:'POST'}).then(r=>cb(r.status));")==405
 driver.save_screenshot('/tmp/relay-'+mode+'.png')
 print(json.dumps(dict(passed=True,mode=mode,expected=expected,readonly=True)))
except Exception:
 print(json.dumps(dict(url=driver.current_url,login_errors=[e.text for e in driver.find_elements(By.ID,'login_error')])),file=sys.stderr);raise
finally:driver.quit()
