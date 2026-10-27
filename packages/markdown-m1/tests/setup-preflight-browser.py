import os,time,subprocess,urllib.request
from driver import Driver,By
subprocess.Popen(['chromedriver','--port=9515','--allowed-ips=127.0.0.1'],stdout=open('/lab/setup-chrome.log','w'),stderr=subprocess.STDOUT)
for _ in range(50):
 try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1);break
 except Exception:time.sleep(.2)
d=Driver()
try:
 d.set_window_size(1440,1000);base=os.environ['M1_SOURCE'];d.get(base+'/wp-login.php')
 d.find_element(By.ID,'user_login').send_keys('operator');d.find_element(By.ID,'user_pass').send_keys('lab-only-password');d.find_element(By.ID,'wp-submit').click()
 d.get(base+'/wp-admin/tools.php?page=owr-m1')
 assert 'Preparation for protection' in d.find_element(By.TAG_NAME,'body').text
 checkbox=d.find_element(By.CSS_SELECTOR,'[name="confirm_terms"]')
 assert checkbox.get_attribute('required') and not checkbox.get_attribute('checked')
 assert len(d.find_elements(By.CSS_SELECTOR,'[name="setup_role"] option'))==2
 d.find_element(By.CSS_SELECTOR,'form:has(input[value="setup_check"]) input[type="submit"]').click()
 assert 'Connection and versioning confirmed' in d.find_element(By.TAG_NAME,'body').text
 d.save_screenshot('/lab/setup-desktop.png')
 d.set_window_size(390,844);d.save_screenshot('/lab/setup-mobile.png')
 assert d.find_element(By.ID,'owr-setup').is_displayed()
 print('PASS Chromium setup controls and responsive rendering')
finally:d.quit()
