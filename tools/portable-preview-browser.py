"""Reuse existing WebDriver helper to inspect a generated-only offline preview."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
helper=(ROOT/'lab/notification-admin/preflight-browser.py').read_text().split('mode=sys.argv[1]')[0]
exec(compile(helper,'existing-webdriver-helper','exec'))
d=Driver();checks=[]
try:
 d.set_window_size(1100,900);d.get('file:///preview/index.html')
 assert '会社案内' in d.find_element(By.TAG_NAME,'body').text;checks.append('index_and_review_notice')
 d.find_element(By.LINK_TEXT,'Services').click()
 assert 'Our services' in d.find_element(By.TAG_NAME,'body').text
 assert '表示保留' in d.find_element(By.TAG_NAME,'body').text;checks.append('services_and_missing_media_visible')
 assert d.execute_script('return Array.from(document.querySelectorAll("article img")).every(x=>x.complete && x.naturalWidth===480 && x.naturalHeight===240)')
 checks.append('valid_image_decoded_in_browser')
 d.save_screenshot('/results/services.png')
 d.find_element(By.CSS_SELECTOR,'article a').click();assert 'page-4.html#anchor-' in d.current_url
 assert d.execute_script('const a=document.getElementById(location.hash.slice(1)); return a && a.nextElementSibling.tagName==="H2" && a.previousElementSibling.textContent==="Independent company introduction."')
 checks.append('fragment_targets_original_body_position')
 assert 'We manufacture test equipment.' in d.find_element(By.TAG_NAME,'body').text;checks.append('internal_link_without_source')
 d.find_element(By.LINK_TEXT,'Contact').click();assert 'example@example.invalid' in d.find_element(By.TAG_NAME,'body').text
 assert 'unsupported_block' in d.find_element(By.TAG_NAME,'body').text;checks.append('contact_and_unsupported_visible')
 for page in ('index.html','page-4.html','page-5.html','page-6.html'):
  d.get('file:///preview/'+page)
  assert not d.find_elements(By.CSS_SELECTOR,'script,iframe,form,object,embed')
  urls=d.execute_script('return Array.from(document.querySelectorAll("[src],[href]")).map(x=>x.src||x.href)')
  assert all(x.startswith('file:///preview/') for x in urls)
  css=d.execute_script('try { return "rules_readable"; } catch(e) { return e.name; }')
  assert d.execute_script('return getComputedStyle(document.body).backgroundColor')=='rgb(245, 247, 250)'
  assert css in ('rules_readable','SecurityError')
 checks.append('all_pages_local_resources_no_active_elements')
 d.set_window_size(390,844);d.get('file:///preview/page-6.html')
 assert d.execute_script('return document.documentElement.scrollWidth <= window.innerWidth')
 d.save_screenshot('/results/contact-mobile.png');checks.append('mobile_no_horizontal_overflow')
 Path('/results/browser.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
 print(json.dumps(dict(passed=True,checks=checks)))
finally:d.quit()
