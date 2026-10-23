# Runs inside the authenticated real-browser editor test, after continuous edits.
source_before=snapshot();latest=state()['receipt'];d.get(root+'/wp-admin/admin.php?page=owr-site-reconstruction')
(lab/'recovery-page.txt').write_text(d.execute_script('return document.body.innerText'))
d.save_screenshot('/lab/recovery-page.png')
def recovery_state():return fetch('/owr-materials-recovery/v1/state')['body']
def until(fn,timeout=1200):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        v=fn()
        if v:return v
        time.sleep(1)
    raise RuntimeError('Recovery condition timeout')
until(lambda: any(x.get('id')==latest['sha256'] for x in recovery_state().get('items',[])))
v=recovery_state();check('new schema generation catalog shown',v['schema']=='owr-site-reconstruction-v1' and len(v['items'])>=7)
check('Q and material summary visible',all(x.get('q') and x.get('summary') for x in v['items'] if x['eligible']))
check('catalog reads do not change source',snapshot()==source_before)
for path in ('state','request'):
    req=urllib.request.Request(root+'/?rest_route=/owr-materials-recovery/v1/'+path,headers=headers,data=b'{}' if path=='request' else None)
    try:urllib.request.urlopen(req);code=200
    except urllib.error.HTTPError as e:code=e.code
    check('subscriber denied recovery '+path,code==403)
# Actual selected editor generation, followed by an older complete generation.
for index,receipt in enumerate([latest,original['receipt']]):
    v=recovery_state();selected=next(x for x in v['items'] if x['id']==receipt['sha256'])
    bad={'generation':selected['id'],'q':'0'*64,'profile':v['profile']}
    check('mismatched Q rejected '+str(index),fetch('/owr-materials-recovery/v1/request',bad)['status']==409)
    d.execute_script("const s=document.getElementById('owr-recovery-generation');s.value=arguments[0];s.dispatchEvent(new Event('change'));",selected['id'])
    until(lambda:not recovery_state().get('stale',True) and not d.find_element(By.ID,'owr-recovery-start').get_attribute('disabled'))
    d.find_element(By.ID,'owr-recovery-start').click()
    job=until(lambda:next((j for j in recovery_state()['jobs'] if j['generation']==selected['id'] and j['state'] in ('verified','failed','interrupted')),None))
    check('selected generation reconstructed '+str(index),job['state']=='verified' and job['result']['logical_sha256']==selected['q'])
    check('complete chosen material set '+str(index),set(job['result']['verified_ids'])=={x['id'] for x in selected['summary']})
    check('private target no publication '+str(index),not job['result']['public_activation'] and job['result']['side_effect_attempts']==0 and job['result']['target']['retained_private'])
    request={'generation':selected['id'],'q':selected['q'],'profile':v['profile']}
    duplicate=fetch('/owr-materials-recovery/v1/request',request)
    check('duplicate request keeps same job '+str(index),duplicate['body'].get('job')==job['job'])
    time.sleep(4);check('no duplicate target '+str(index),len([x for x in recovery_state()['jobs'] if x['generation']==selected['id']])==1)
check('reconstruction leaves source unchanged',snapshot()==source_before)
control.write_text(json.dumps({'pause_recovery':True}));time.sleep(6)
p=lab/'bridge/reconstruction/status.json';report=json.loads(p.read_bytes());report['updated_at']=0;p.write_text(json.dumps(report))
d.refresh();until(lambda:d.find_element(By.ID,'owr-recovery-start').get_attribute('disabled'))
check('stale status blocks request',fetch('/owr-materials-recovery/v1/request',request)['status']==409)
control.write_text('{}');until(lambda:not recovery_state()['stale']);check('report resumes without new job',len(recovery_state()['jobs'])==2)
d.save_screenshot('/lab/reconstruction-complete.png');(lab/'recovery-result.json').write_text(json.dumps(recovery_state(),ensure_ascii=False))
