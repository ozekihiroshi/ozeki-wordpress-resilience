import json,os,sys,time,subprocess,urllib.request
from pathlib import Path
from driver import Driver,By,Element,WebDriverWait
By.NAME='name'
original_elements=Driver.elements
def elements(self,by,value,prefix=''):
 if by=='name':by,value='css selector','[name="'+value+'"]'
 return original_elements(self,by,value,prefix)
Driver.elements=elements
Driver.title=property(lambda self:self.call('GET','/title'))
Element.find_element=lambda self,by,value:self.find_elements(by,value)[0]
class EC:
 @staticmethod
 def presence_of_element_located(pair):return lambda d:bool(d.find_elements(*pair))
 @staticmethod
 def staleness_of(el):
  def stale(d):
   try:el.text;return False
   except Exception:return True
  return stale
lab=Path('/lab')
try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1)
except Exception:subprocess.Popen(['chromedriver','--port=9515','--allowed-ips=127.0.0.1'],stdout=open('/lab/chromedriver.log','a'),stderr=subprocess.STDOUT)
for _ in range(50):
 try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1);break
 except Exception:time.sleep(.2)
d=Driver();d.set_window_size(1440,1000);wait=WebDriverWait(d,210)
base=os.environ.get('M1_TARGET') or os.environ['M1_SOURCE']
def log(s):print(s,flush=True)
def open_(path):d.get(base+path)
def field(name,value):
 el=d.find_element(By.NAME,name);el.clear();el.send_keys(value)
def save():
 old=d.find_element(By.TAG_NAME,'body');d.find_element(By.ID,'publish').click();wait.until(EC.staleness_of(old));wait.until(lambda x:x.execute_script('return document.readyState')=='complete')
def edit(id):open_('/wp-admin/post.php?post='+str(id)+'&action=edit');wait.until(EC.presence_of_element_located((By.ID,'ozmd-source')))
def source():return d.execute_script("return document.getElementById('ozmd-source').value")
def create(title,body):
 open_('/wp-admin/post-new.php?post_type=ozmd_document');wait.until(EC.presence_of_element_located((By.ID,'ozmd-source')));field('post_title',title);field('ozmd_source',body);save()
 if not d.find_elements(By.ID,'post_ID'):raise RuntimeError(d.find_element(By.TAG_NAME,'body').text)
 return int(d.find_element(By.ID,'post_ID').get_attribute('value'))
try:
 open_('/wp-login.php');field('log','operator');field('pwd','lab-only-password');d.find_element(By.ID,'wp-submit').click();wait.until(lambda x:'/wp-admin/' in x.current_url)
 if len(sys.argv)>1:
  open_('/wp-admin/tools.php?page=ozeki-resilience');wait.until(EC.presence_of_element_located((By.NAME,'sequences[]')))
  # Last version of A and the only version of B. Earlier versions remain selectable.
  seen=set()
  for row in d.find_elements(By.CSS_SELECTOR,'table tr')[1:]:
   title=row.find_elements(By.TAG_NAME,'td')[2].text
   if title not in seen:row.find_element(By.NAME,'sequences[]').click();seen.add(title)
  button=next(b for b in d.find_elements(By.CSS_SELECTOR,'input[type=submit]') if b.get_attribute('value')=='Restore selected versions');button.click()
  wait.until(lambda x:'"sha256"' in x.find_element(By.TAG_NAME,'body').text)
  d.save_screenshot('/lab/restore-admin.png')
  open_('/?post_type=ozmd_document');links=d.find_elements(By.CSS_SELECTOR,'a[href*="ozmd_document"]');log('Restored documents visible')
  # Verify canonical old-server links are rendered as target links.
  old=json.loads((lab/'origin.json').read_text());open_('/?ozmd_document=m1-a')
  wait.until(lambda x:len(x.find_elements(By.LINK_TEXT,'Document B'))>0)
  href=d.find_element(By.LINK_TEXT,'Document B').get_attribute('href');assert href.startswith(base),href
  d.find_element(By.LINK_TEXT,'Document B').click();wait.until(lambda x:'Document B' in x.find_element(By.TAG_NAME,'body').text)
  log('PASS restored A→B link uses new WordPress URL')
 else:
  raw='# Document A\n\n```mermaid\ngraph LR\n A --> B\n```\n\n$$E=mc^2$$\n\n```php\necho "原文";\n```\n'
  a=create('M1 A',raw);log('Published A')
  for v in [2,3]:
   edit(a);field('ozmd_source',raw+'\nRevision '+str(v));save();assert source()==raw+'\nRevision '+str(v);log('Updated A '+str(v))
  braw='# Document B\n\n[Document A]('+base+'/?ozmd_document=m1-a)\n';b=create('M1 B',braw);log('Published B')
  braw+='\nUpdated document B\n';edit(b);field('ozmd_source',braw);save();assert source()==braw;log('Updated B')
  final=raw+'\n[Document B]('+base+'/?ozmd_document=m1-b)\n'
  edit(a);field('ozmd_source',final);save();assert source()==final
  for failure in ['s3','wordpress','stop']:
   (lab/'control.json').write_text(json.dumps({'fail':failure}));edit(a);field('ozmd_source',raw+'FAIL '+failure);save()
   if failure!='stop':assert 'Resilience' in d.title
   (lab/'control.json').write_text('{}');edit(a);assert source()==final;log('PASS '+failure+' preserves committed source')
  # Stale editor optimistic conflict must not write another original or history.
  edit(a);d.execute_script("document.querySelector('[name=ozeki_resilience_m1_base]').value='stale'");field('ozmd_source','stale edit');save();assert 'changed since' in d.find_element(By.TAG_NAME,'body').text
  edit(a);assert source()==final;log('PASS stale editor rejected')
  # A lost formal-history write preserves WP state and resumes the same operation.
  (lab/'control.json').write_text(json.dumps({'fail':'history'}));edit(a);final+='\nFinal confirmed update\n';field('ozmd_source',final);save();assert source()==final
  open_('/wp-admin/tools.php?page=ozeki-resilience');assert 'Resume history' in d.find_element(By.TAG_NAME,'body').text
  (lab/'control.json').write_text('{}');next(b for b in d.find_elements(By.CSS_SELECTOR,'input[type=submit]') if b.get_attribute('value')=='Resume history').click();wait.until(lambda x:not any(b.get_attribute('value')=='Resume history' for b in x.find_elements(By.CSS_SELECTOR,'input[type=submit]')))
  d.save_screenshot('/lab/source-history.png');log('PASS formal history resumed')
  (lab/'expected.json').write_text(json.dumps({'M1 A':{'source':final.replace('\n','\r\n'),'status':'publish','slug':'m1-a'},'M1 B':{'source':braw.replace('\n','\r\n'),'status':'publish','slug':'m1-b'}},ensure_ascii=False))
  (lab/'origin.json').write_text(json.dumps({'server':base,'A':a,'B':b}))
except Exception:
 d.save_screenshot('/lab/failure.png');(lab/'failure-body.txt').write_text(d.find_element(By.TAG_NAME,'body').text);raise
finally:d.quit()
