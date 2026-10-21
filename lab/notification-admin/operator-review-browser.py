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
mode=sys.argv[1]
driver=Driver()
try:
 driver.get('http://127.0.0.1/wp-login.php')
 for key,value in [('user_login','labadmin'),('user_pass',os.environ['LAB_ADMIN_PASSWORD'])]:driver.find_element(By.ID,key).send_keys(value)
 driver.find_element(By.ID,'wp-submit').click()
 WebDriverWait(driver,30).until(lambda d:'wp-login.php' not in d.current_url)
 page='http://127.0.0.1/wp-admin/admin.php?page=owr-preflight';driver.get(page)
 content=driver.find_element(By.CSS_SELECTOR,'#wpbody-content .wrap')
 assert driver.find_element(By.CSS_SELECTOR,'[data-operator-review]').get_attribute('data-operator-review')==('valid' if mode=='stale' else mode)
 assert not content.find_elements(By.CSS_SELECTOR,'form,button,input,select')
 assert 'NEVER_RENDER_SECRET' not in content.text
 if mode=='stale':assert '現在の有効性は未確認' in content.text
 if mode=='valid':assert '有効期限' in content.text
 if '--require-current' in sys.argv:
  assert '現在の有効性は未確認' not in content.text
  assert '定期取得・受渡しは成功しています' in content.text
 driver.save_screenshot('/tmp/operator-review-'+mode+'.png')
 status=driver.execute_async_script("const done=arguments[0];fetch(location.href,{method:'POST'}).then(r=>done(r.status));")
 assert status==405
 driver.delete_all_cookies();driver.get('http://127.0.0.1/wp-login.php')
 for key,value in [('user_login','labeditor'),('user_pass',os.environ['LAB_ADMIN_PASSWORD'])]:driver.find_element(By.ID,key).send_keys(value)
 driver.find_element(By.ID,'wp-submit').click();WebDriverWait(driver,30).until(lambda d:'wp-login.php' not in d.current_url)
 driver.get(page);assert not driver.find_elements(By.CSS_SELECTOR,'[data-operator-review]')
 print(json.dumps({'mode':mode,'passed':True,'checks':['state','readonly','redaction','POST405','editor_denied']}))
finally:driver.quit()
