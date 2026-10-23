import base64,json,subprocess,time,urllib.request,urllib.error
from pathlib import Path
base=Path('/kit/lab/notification-admin/preflight-browser.py').read_text().split('mode=')[0].replace("'http://127.0.0.1:4444'+self.endpoint","'http://127.0.0.1:9515'+self.endpoint")
def diagnostic_open(req,timeout):
    try:return urllib.request.urlopen(req,timeout=timeout)
    except urllib.error.HTTPError as e:raise RuntimeError(e.read().decode()) from e
base=base.replace('with urllib.request.urlopen(req,timeout=60) as response:','with diagnostic_open(req,timeout=60) as response:')
exec(base)
lab=Path('/lab');checks=[];control=lab/'control.json'
subprocess.Popen(['chromedriver','--port=9515','--allowed-ips=127.0.0.1'],stdout=open('/lab/chromedriver.log','w'),stderr=subprocess.STDOUT)
for i in range(60):
    try:urllib.request.urlopen('http://127.0.0.1:9515/status',timeout=1);break
    except Exception:time.sleep(.2)
d=Driver();d.set_window_size(1280,1000);root='http://127.0.0.1'
def check(name,ok):
    if not ok:raise AssertionError(name)
    checks.append(name);(lab/'checks.json').write_text(json.dumps(checks));print('PASS '+name,flush=True)
def until(fn,seconds=100):
    end=time.time()+seconds
    while time.time()<end:
        if fn():return
        time.sleep(.4)
    raise RuntimeError('Timeout: '+str(d.execute_script('return document.body.innerText'))[-4000:])
def api(path,data=None):
    return d.call('POST','/execute/async',dict(script="const done=arguments[arguments.length-1];wp.apiFetch({path:arguments[0],...(arguments[1]===null?{}:{method:'POST',data:arguments[1]})}).then(v=>done({ok:true,value:v})).catch(e=>done({ok:false,error:e}));",args=[path,data]))
def snapshot():return api('/owr-test/v1/snapshot')['value']
def editor(kind='post',id=None):
    d.get(root+'/wp-admin/'+('post.php?post='+str(id)+'&action=edit' if id else 'post-new.php'+('?post_type=page' if kind=='page' else '')))
    until(lambda:d.execute_script("return !!(window.wp&&wp.data&&wp.data.select('core/editor')&&wp.data.select('core/editor').getCurrentPostId()&&window.owrNative)"))
def save(title,text,status='publish'):
    d.execute_script("window.nativeDone=false;wp.data.dispatch('core/editor').editPost({title:arguments[0],content:arguments[1],status:arguments[2]});wp.data.dispatch('core/editor').savePost().then(()=>window.nativeDone=true).catch(e=>{window.nativeError=String(e);window.nativeDone=true;});",title,text,status)
    until(lambda:d.execute_script('return window.nativeDone===true'),220)
def html(text):return '<!-- wp:paragraph --><p>'+text+'</p><!-- /wp:paragraph -->'
try:
    d.get(root+'/wp-login.php');d.find_element(By.ID,'user_login').send_keys('operator');d.find_element(By.ID,'user_pass').send_keys('lab-only-password');d.find_element(By.ID,'wp-submit').click()
    editor();check('standard editor remains open','post-new.php' in d.current_url)
    ident=d.execute_script("return wp.data.select('core/editor').getCurrentPostId()")
    save('Native published post',html('Original <strong>bold</strong> text'))
    posts=snapshot()['posts'];check('new post published after material save',any(int(x['id'])==ident and x['status']=='publish' and 'Original' in x['content'] for x in posts))
    state=api('/owr-materials/v1/state')['value'];check('S3 generation contains publication intent',any(x.get('title')=='Native published post' and x.get('status')=='publish' for x in state['site']['entries']))
    before=snapshot();control.write_text('{"fail_before":true}');save('Failed update',html('Must not replace published text'))
    check('failed native save preserves public DB',snapshot()==before)
    if (lab/'plugin.zip').exists():
        check('ZIP update preserves failed request settings and history',api('/owr-test/v1/upgrade',{})['ok'])
    control.write_text('{}');res=api('/owr-materials/v1/resume',{});check('same request can resume',res['ok'])
    until(lambda:api('/owr-materials/v1/state')['value']['state']=='stored')
    check('stored retry applied',api('/owr-materials/v1/apply',{})['ok'])
    check('resumed publication updated same post',any(int(x['id'])==ident and x['title']=='Failed update' and x['status']=='publish' for x in snapshot()['posts']))
    # Old editor still has old parent and must not overwrite the newly applied generation.
    before=snapshot();save('Stale overwrite',html('Stale'));check('stale editor rejected',snapshot()==before)
    editor('page');pageid=d.execute_script("return wp.data.select('core/editor').getCurrentPostId()")
    complex_body=d.execute_script("return wp.blocks.serialize([wp.blocks.createBlock('core/heading',{level:3,content:'Heading'}),wp.blocks.createBlock('core/list',{},[wp.blocks.createBlock('core/list-item',{content:'Item'})]),wp.blocks.createBlock('core/quote',{},[wp.blocks.createBlock('core/paragraph',{content:'Quote'})])])")
    save('Native page',complex_body);check('new page published',any(int(x['id'])==pageid and x['type']=='page' and x['status']=='publish' for x in snapshot()['posts']))
    editor('page',pageid)
    check('heading list quote remain editable',d.execute_script("return wp.data.select('core/block-editor').getBlocks().every(b=>b.isValid!==false)"))
    # Native media REST upload, through the same editor middleware used by image blocks.
    raw=base64.b64encode((lab/'normal.png').read_bytes()).decode()
    d.execute_script("window.uploadDone=false;const raw=atob(arguments[0]);const b=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)b[i]=raw.charCodeAt(i);const f=new FormData();f.append('file',new File([b],'normal.png',{type:'image/png'}));wp.apiFetch({path:'/wp/v2/media',method:'POST',body:f}).then(v=>{window.uploadResult=v;window.uploadDone=true;}).catch(e=>{window.uploadError=e;window.uploadDone=true;});",raw)
    until(lambda:d.execute_script('return window.uploadDone===true'),220)
    image=d.execute_script('return window.uploadResult||window.uploadError');print('Upload '+json.dumps(image),flush=True)
    check('native image upload returns attachment',isinstance(image,dict) and bool(image.get('source_url')))
    content=html('Image page <a href="http://127.0.0.1/?p='+str(ident)+'">News</a>')+'<!-- wp:image {"id":'+str(image['id'])+'} --><figure class="wp-block-image"><img src="'+image['source_url']+'" alt="test" class="wp-image-'+str(image['id'])+'"/></figure><!-- /wp:image -->'
    save('Native page with image',content)
    check('image inserted after S3 save',any(int(x['id'])==pageid and '<img' in x['content'] for x in snapshot()['posts']))
    editor('page',pageid)
    invalid=d.execute_script("return wp.data.select('core/block-editor').getBlocks().filter(b=>b.isValid===false).map(b=>b.name)")
    check('saved blocks remain editable after reload',not invalid)
    count=len(snapshot()['images'])
    d.execute_script("wp.media({title:'Native image test',multiple:false}).open()")
    until(lambda:d.execute_script("return !!document.querySelector('.media-modal input[type=file]')"))
    upload=d.find_element(By.CSS_SELECTOR,'.media-modal input[type=file]');upload.send_keys('/lab/replacement.png')
    until(lambda:len(snapshot()['images'])==count+1,220)
    until(lambda:d.execute_script("return wp.Uploader.queue.length===0"),20)
    check('standard media modal image registration',len(snapshot()['images'])==count+1)
    editor('page',pageid)
    before=snapshot();control.write_text('{"stop_after_store":true}')
    d.execute_script("window.nativeDone=false;wp.data.dispatch('core/editor').editPost({title:'Resumed after stop'});wp.data.dispatch('core/editor').savePost().then(()=>window.nativeDone=true)")
    until(lambda:(lab/'worker-paused.json').exists())
    check('interruption after storage keeps published DB unchanged',snapshot()==before)
    paused=json.loads((lab/'worker-paused.json').read_text())
    control.write_text('{}');until(lambda:d.execute_script('return window.nativeDone===true'),220)
    final=api('/owr-materials/v1/state')['value'];check('restart uses the same stored generation',final['receipt']==paused['head'])
    check('restart updates same page without duplicate',len([x for x in snapshot()['posts'] if int(x['id'])==pageid and x['title']=='Resumed after stop'])==1)
    before=snapshot();save('Unsupported', '<!-- wp:shortcode -->[contact-form]<!-- /wp:shortcode -->');check('unsupported block rejected without DB write',snapshot()==before)
    # Reconstructable received material is emitted by the normal worker, not fixture glue.
    state=api('/owr-materials/v1/state')['value'];(lab/'native-final-state.json').write_text(json.dumps(state));check('completed journal has no pending request',state['pending'] is None)
    if (lab/'plugin.zip').exists():
        check('ZIP reinstall preserves completed generations and history',api('/owr-test/v1/upgrade',{})['ok'])
    d.save_screenshot('/lab/native-editor.png')
    (lab/'browser-result.json').write_text(json.dumps({'checks':checks}));print('PASS native editor',flush=True)
finally:d.quit()
