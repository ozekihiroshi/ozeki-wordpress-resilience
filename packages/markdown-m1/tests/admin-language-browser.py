import os,time,subprocess,urllib.request,re
from driver import Driver,By
subprocess.Popen(['chromedriver','--port=9515','--allowed-ips=127.0.0.1'],stdout=open('/lab/language-chrome.log','w'),stderr=subprocess.STDOUT)
for _ in range(50):
 try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1);break
 except Exception:time.sleep(.2)
d=Driver();base=os.environ['M1_SOURCE']
def css(selector):return d.find_element(By.CSS_SELECTOR,selector)
def page():d.get(base+'/wp-admin/tools.php?page=ozeki-resilience')
def body():return d.execute_script('return document.body ? document.body.innerText : ""')
def wait_text(text):
 for _ in range(60):
  try:
   if text in body():return
  except (IndexError,RuntimeError):pass
  time.sleep(.5)
 d.save_screenshot('/lab/language-failed.png')
 open('/lab/language-failed.txt','w').write(body());raise AssertionError(text+' missing from '+body()[:2500])
def button(operation):return css('form:has(input[value="'+operation+'"]) input[type="submit"]')
try:
 d.set_window_size(1440,1100);d.get(base+'/wp-login.php');css('#user_login').send_keys('operator');css('#user_pass').send_keys('lab-only-password');css('#wp-submit').click()
 d.call('POST','/cookie',{'cookie':{'name':'owr_test_locale','value':'ja','path':'/'}});page()
 assert '保護開始までの準備状況' in body()
 for name,value in [('bucket','m1-generated'),('region','ap-northeast-1'),('prefix','language/')]:css('[name="'+name+'"]').send_keys(value)
 assert button('configure').get_attribute('value')=='設定を保存'
 assert not css('[name="confirm_terms"]').get_attribute('checked')
 css('[name="confirm_terms"]').click();button('configure').click()
 wait_text('初期保存とサイト全体の復旧');button('setup_check').click()
 wait_text('接続とバージョン管理を確認しました。')
 css('form:has(input[value="whole_initial"]) [name="trust_initial"]').click();button('whole_initial').click()
 wait_text('この保存先で完了しています。')
 css('[name="protect"]').click();css('[name="confirm_terms"]').click();button('configure').click()
 wait_text('保護中です。')
 assert button('whole_restore').get_attribute('value')=='サイト全体を復旧'
 d.execute_script('window.scrollTo(0,0)');d.save_screenshot('/lab/admin-ja.png')
 # Only static UI is localized: form parameters continue to use the same identifiers.
 fields_ja=d.execute_script('return Array.from(document.querySelectorAll("input[name],select[name]")).map(e=>e.name)')
 d.call('DELETE','/cookie/owr_test_locale');page()
 assert 'Preparation for protection' in body() and 'Protection is enabled' in body()
 assert button('configure').get_attribute('value')=='Save settings'
 assert button('whole_initial').get_attribute('value')=='Create complete initial snapshot'
 assert button('whole_restore').get_attribute('value')=='Restore complete site'
 assert not re.search('[ぁ-んァ-ヶ一-龠]',body()),'English interface leaked Japanese'
 assert fields_ja==d.execute_script('return Array.from(document.querySelectorAll("input[name],select[name]")).map(e=>e.name)')
 d.save_screenshot('/lab/admin-en.png')
 print('PASS Japanese complete setup workflow, English controls, unchanged form names')
finally:d.quit()
