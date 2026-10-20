from pathlib import Path
exec(Path('/lab/daily-browser-test.py').read_text().split("mode=sys.argv[1]")[0])
mode=sys.argv[1]
deadline=time.monotonic()+45
while True:
    try:
        driver=Driver();break
    except Exception:
        if time.monotonic()>deadline:raise
        time.sleep(1)
try:
    driver.set_window_size(1440,1100)
    driver.get('http://127.0.0.1/wp-login.php')
    driver.find_element(By.ID,'user_login').send_keys('labadmin')
    driver.find_element(By.ID,'user_pass').send_keys(os.environ['LAB_ADMIN_PASSWORD'])
    driver.find_element(By.ID,'wp-submit').click()
    WebDriverWait(driver,20).until(lambda d:'wp-login.php' not in d.current_url)
    driver.get('http://127.0.0.1/wp-admin/admin.php?page=owr-daily-status')
    el=driver.find_element(By.CSS_SELECTOR,'[data-daily-transfer]')
    assert el.get_attribute('data-daily-transfer')==mode,el.text
    text=driver.find_element(By.CSS_SELECTOR,'#wpbody-content .wrap').text
    assert '復元検証済み' in text and '後片付け確認済み' in text
    if mode=='stopped':assert '現在の状態は不明' in el.text
    if mode=='source_stale':assert '5分以上更新' in el.text
    assert not driver.find_elements(By.CSS_SELECTOR,'#wpbody-content .wrap form')
    driver.save_screenshot('/tmp/systemd-'+mode+'.png')
    print(json.dumps(dict(passed=True,state=mode,message=el.text),ensure_ascii=False))
finally:driver.quit()
