import base64,json,os,time,urllib.request,subprocess
from pathlib import Path
# Reuse the repository's small WebDriver HTTP client without running its scenarios.
exec(Path('/kit/webdriver-base.py').read_text().split('mode=')[0].replace("'http://127.0.0.1:4444'+self.endpoint","'http://127.0.0.1:'+str(self.port)+self.endpoint"))
checks=[];drivers=[];lab=Path('/lab');config=json.loads((lab/'config.json').read_text());root='http://127.0.0.1'
def check(label,ok):
 if not ok:raise AssertionError(label)
 checks.append(label);(lab/'progress.json').write_text(json.dumps(checks));print('PASS '+label,flush=True)
def wait(d,state):
 end=time.monotonic()+(1100 if (lab/'live.json').exists() else 60)
 while time.monotonic()<end:
  found=d.find_elements(By.ID,'owr-status')
  if found and found[0].get_attribute('data-state')==state:return
  time.sleep(.2)
 raise RuntimeError('Expected editor state '+state+'; observed '+(found[0].text if found else 'no editor'))
def control(**kw):(lab/'control.json').write_text(json.dumps(kw))
def public(role):return urllib.request.urlopen(root+'/?page_id='+str(config['ids'][role]),timeout=10).read().decode()
def commits():
 if (lab/'live.json').exists():return json.loads((lab/'live-commits.json').read_text())
 return [json.loads(p.read_text()) for p in (lab/'s3/objects').glob('*.json') if '/commits/' in json.loads(p.read_text())['key']]
def editor(d,role='company'):
 d.get(root+'/wp-admin/post.php?post='+str(config['ids'][role])+'&action=edit')
def field(d,selector,text):
 e=d.find_element(By.CSS_SELECTOR,selector);e.clear();e.send_keys(text)
def login(d,user='labadmin',password=None):
 d.get(root+'/wp-login.php');field(d,'#user_login',user);field(d,'#user_pass',password or os.environ['LAB_ADMIN_PASSWORD']);d.find_element(By.ID,'wp-submit').click()
 end=time.monotonic()+30
 while 'wp-login.php' in d.current_url and time.monotonic()<end:time.sleep(.2)
def fresh():
 d=Driver.__new__(Driver);d.port=9515+len(drivers)
 log=open('/lab/chromedriver-'+str(d.port)+'.log','w')
 subprocess.Popen(['chromedriver','--port='+str(d.port),'--allowed-ips=127.0.0.1','--verbose'],stdout=log,stderr=log)
 end=time.monotonic()+15
 while True:
  try:urllib.request.urlopen('http://127.0.0.1:'+str(d.port)+'/status',timeout=1);break
  except Exception:
   if time.monotonic()>end:raise
   time.sleep(.2)
 Driver.__init__(d);drivers.append(d);d.set_window_size(1250,1000);return d
def jsfetch(d,path,body=None,nonce=True):
 return d.execute_async_script('''const done=arguments[arguments.length-1];fetch('''+json.dumps(path)+''',{method:'''+json.dumps('POST' if body else 'GET')+''',headers:{'Content-Type':'application/json','X-WP-Nonce':'''+('window.owrEditorConfig.nonce' if nonce else "''")+'''},'''+('body:'+json.dumps(json.dumps(body))+',' if body else '')+'''credentials:'same-origin'}).then(async r=>done({status:r.status,body:await r.text()})).catch(e=>done({error:String(e)}));''')
try:
 a=fresh();editor(a);check('anonymous editor requires login',bool(a.find_elements(By.ID,'loginform')))
 login(a);editor(a);wait(a,'ready');check('normal page edit opens protected editor','page=owr-protected-editor' in a.current_url)
 check('resume button hidden when editable',not a.find_element(By.ID,'owr-resume').is_displayed())
 before=public('company');check('initial paragraph from enrolled public page',a.find_element(By.CSS_SELECTOR,'#owr-paragraphs textarea').get_attribute('value')=='Before company')
 b=fresh();login(b);editor(b);wait(b,'ready')
 field(a,'#owr-title','会社案内 Browser');field(a,'#owr-paragraphs textarea','Browser company <script>window.owrInjected=true</script>')
 check('typing does not update public content',public('company')==before)
 control(fail='/commits/');a.find_element(By.ID,'owr-save').click();wait(a,'unresolved');check('storage failure leaves public text unchanged','Before company' in public('company') and 'Browser company' not in public('company'))
 check('failed request locks content for exact retry',a.find_element(By.ID,'owr-fields').get_attribute('disabled') is not None)
 check('resume button visible only for unresolved request',a.find_element(By.ID,'owr-resume').is_displayed())
 a.save_screenshot('/lab/editor-failed.png')
 field(b,'#owr-title','Competing');b.find_element(By.ID,'owr-save').click();wait(b,'conflict');check('different pending operation shows conflict',len(commits())==0)
 a.refresh();wait(a,'pending');check('reload retrieves frozen operation from server',a.find_element(By.ID,'owr-title').get_attribute('value')=='会社案内 Browser')
 control();a.find_element(By.ID,'owr-resume').click();wait(a,'applied');check('resume applies exactly one generation',len(commits())==1 and 'Browser company' in public('company'))
 check('other two pages retained','Before services' in public('services') and 'Before contact' in public('contact'))
 check('text escaped in projection','&lt;script&gt;' in public('company'))
 check('resume button hidden after completion',not a.find_element(By.ID,'owr-resume').is_displayed())
 a.save_screenshot('/lab/editor-applied.png')
 # Open a fresh stale editor before a winning edit in another browser.
 b.refresh();wait(b,'ready');editor(a,'services');wait(a,'ready');field(a,'#owr-paragraphs textarea','Browser services winner');a.find_element(By.ID,'owr-save').click();wait(a,'applied')
 field(b,'#owr-title','Stale edit');b.find_element(By.ID,'owr-save').click();wait(b,'conflict');check('stale editor rejected without overwrite',len(commits())==2 and 'Browser services winner' in public('services') and 'Stale edit' not in public('company'))
 b.save_screenshot('/lab/editor-conflict.png')
 editor(a,'contact');wait(a,'ready');control(stop='after_s3');field(a,'#owr-paragraphs textarea','Browser contact after restart');a.find_element(By.ID,'owr-save').click();wait(a,'unresolved')
 check('S3 committed but not projected state visible','S3確定済み' in a.find_element(By.ID,'owr-status').text and 'Before contact' in public('contact'))
 version=commits()[-1]['version'];a.refresh();wait(a,'pending');control();a.find_element(By.ID,'owr-resume').click();wait(a,'applied')
 check('interrupted HTTP save resumes same fixed generation',len(commits())==3 and version in [x['version'] for x in commits()] and 'Browser contact after restart' in public('contact'))
 if not (lab/'live.json').exists():
  # Two UI result-handling guards added during implementation review.
  field(a,'#owr-title','長'*100);a.find_element(By.ID,'owr-save').click();wait(a,'invalid')
  check('invalid input stays editable without creating a generation',a.find_element(By.ID,'owr-fields').get_attribute('disabled') is None and len(commits())==3)
  field(a,'#owr-title','Contact lost response')
  a.execute_script("const original=window.fetch;window.fetch=(url,options)=>options && options.method==='POST' ? original(url,options).then(()=>Promise.reject(new Error('injected lost response'))) : original(url,options);")
  a.find_element(By.ID,'owr-save').click();wait(a,'applied')
  check('lost successful save response reconciles as applied not conflict',len(commits())==4 and 'Contact lost response' in public('contact'))
  a.refresh();wait(a,'ready')
  field(a,'#owr-title','Contact verified')
  a.execute_script("const original=window.fetch;window.fetch=(url,options)=>String(url).includes('editor') ? Promise.resolve(new Response('{}',{status:503,headers:{'Content-Type':'application/json'}})) : original(url,options);")
  a.find_element(By.ID,'owr-save').click();wait(a,'unavailable')
  check('state-refresh failure never displays false completion',len(commits())==5 and '反映しました' not in a.find_element(By.ID,'owr-status').text)
  a.refresh();wait(a,'ready')
 check('editor status GET requires nonce',jsfetch(a,'/index.php?rest_route=/owr-rbr/v1/editor',nonce=False)['status'] in [401,403])
 q=a.execute_async_script("const done=arguments[arguments.length-1];fetch('/wp-admin/post.php',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'action=editpost&post_ID="+str(config['ids']['company'])+"&post_content=BYPASS'}).then(r=>done(r.status));")
 check('classic form POST bypass blocked',q==409 and 'BYPASS' not in public('company'))
 a.get(root+'/wp-admin/post.php?post='+str(config['unrelated'])+'&action=edit');check('unrelated page retains normal editor','owr-protected-editor' not in a.current_url and not a.find_elements(By.ID,'owr-form'))
 sub=fresh();login(sub,'labsubscriber','Test-only-pass123!');editor(sub);check('subscriber has no protected form',not sub.find_elements(By.ID,'owr-form'))
 (lab/'browser-result.json').write_text(json.dumps({'passed':True,'checks':checks,'commits':len(commits())},indent=2))
finally:
 for n,d in enumerate(drivers):
  try:
   if not (lab/'browser-result.json').exists():d.save_screenshot('/lab/failed-browser-'+str(n)+'.png')
  except Exception:pass
  try:d.quit()
  except Exception:pass
