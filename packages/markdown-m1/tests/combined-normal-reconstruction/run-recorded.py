from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64,re
b=Path('/tmp/construction-record-integration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='construction-record-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-markdown.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def d(*args):
 p=subprocess.run(D+list(args),capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError(p.stderr[:2000]+p.stdout[-1000:])
 return p.stdout
def setup(label):
 web=name+'-'+label;vol=web+'-vol';d('volume','create',vol);made.append(('volume',vol))
 d('run','-d','--name',web,'--network',net,'--memory','512m','-v',vol+':/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e','WORDPRESS_TABLE_PREFIX='+label+'_','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
 for _ in range(60):
  if subprocess.run(D+['exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
  time.sleep(1)
 d('exec',web,'sh','-c','echo memory_limit=256M > /usr/local/etc/php/conf.d/fixture-memory.ini')
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'acf.zip'),web+':/tmp/acf.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=ACF normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/acf.zip','--activate')
 for plugin in ['markdown','tablepress','contact-form-7','flamingo','wp-members']:
  d('cp',str(b/(plugin+'.zip')),web+':/tmp/'+plugin+'.zip');wp('plugin','install','/tmp/'+plugin+'.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')

 client=module.NormalMarkdownClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()






import re,html,copy,http.cookiejar

def loadtool(name):
 sp=importlib.util.spec_from_file_location(name,b/('product/tools/reconstruct-'+name+'.py'));mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);return mod
mods={k:loadtool(k) for k in ['markdown','tablepress','contact-form','members','acf']}
def clients(url):
 return {k:getattr(m,{'markdown':'NormalMarkdownClient','tablepress':'NormalTablePressClient','contact-form':'NormalContactFormClient','members':'NormalMemberClient','acf':'NormalAcfClient'}[k])(url,'operator','isolated-only-123',True) for k,m in mods.items()}
def finish_onboarding(c):
 url=c.settingsurl;markup=c.request(url)[0].decode();forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',markup,re.S) if 'name="wpmem_onboarding_action"' in x]
 assert len(forms)==1
 f=mods['members'].Form(forms[0],None);p=f.values.copy();p.pop('optin',None);c.request(f.action or url,p)
def attempt(name,fn):
 try:r=fn();results['stages'][name]=r;return r
 except Exception as e:results['stages'][name]={'error':str(e)};return None

sp=importlib.util.spec_from_file_location('construction',b/'product/tools/construction-record.py')
recordmod=importlib.util.module_from_spec(sp);sp.loader.exec_module(recordmod);Record=recordmod.ConstructionRecord
def ref(key,field='id'):return {'ref':key+'.'+field}
def text(*parts):return {'text':list(parts)}

def dispatcher(web,wp,url,c):
 def execute(op,p):
  if op=='rest':
   r=c['markdown'].rest(p['endpoint'],p['body']);return {'id':r['id']}
  if op in ('media','menu','menu-item','acf-definition'):
   path=b/(web+'-input.json');path.write_text(json.dumps({'operation':op,'input':p}))
   d('cp',str(path),web+':/tmp/normal-operation.json')
   d('exec',web,'chown','www-data:www-data','/tmp/normal-operation.json')
   # Same OS actor as normal Apache/PHP requests; root-created upload paths
   # are not a faithful fixture for a normal site construction operation.
   return json.loads(d('exec','-u','www-data',web,'php','/tmp/wp.phar','eval-file','/tmp/normal-operation.php'))
  if op=='table-import':return {'id':c['tablepress'].import_table(p)}
  if op=='table-save':c['tablepress'].save_table(p['id'],p['table']);return {'id':p['id']}
  if op=='markdown-import':return {'id':c['markdown'].import_document(p['raw'].encode(),p['filename'])}
  if op=='markdown-save':c['markdown'].save(p['id'],p['raw'].encode(),p['settings']);return {'id':p['id']}
  if op=='cf7-create':return {'id':c['contact-form'].cf7(payload=p)['id']}
  if op=='member-pages':
   # Only the requested ordinary page controls; no source DB settings copied.
   m=c['members'];f=m.form(m.settingsurl,'updatesettings');v=f.values.copy()
   expected={}
   for k,vv in p.items():expected['wpmem_settings_'+{'login':'logpage','profile':'mspage'}[k]]=str(vv)
   v.update(expected);m.submit(f,v);actual=m.form(m.settingsurl,'updatesettings').values
   assert all(actual.get(k)==v for k,v in expected.items()),{'expected':expected,'actual':{k:actual.get(k) for k in expected}}
   return {'saved':True}
  if op=='member-field':c['members'].save_field(p);return {'saved':True}
  if op=='member-create':return {'id':c['members'].create_member(p)}
  if op=='member-access':c['members'].restriction(p['id'],'page',p['value']);return {'id':p['id']}
  if op=='acf-values':c['acf'].save_values(p['id'],'page',p['values']);return {'id':p['id']}
  if op=='cf7-submit':
   markup=c['markdown'].request('/?page_id='+str(p['page']))[0].decode()
   controls=module.Fields(markup).values
   pairs={k:v for k,v in controls.items() if k.startswith('_wpcf7')};pairs.update(p['values'])
   boundary='----ConstructionReceipt';body=b''
   for k,v in pairs.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode()
   body+=('--'+boundary+'--\r\n').encode()
   request=urllib.request.Request(url+'/?rest_route=/contact-form-7/v1/contact-forms/'+str(p['form'])+'/feedback',body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
   r=json.loads(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request).read())
   assert r['status']=='mail_sent',r
   # Read-only confirmation, no receiver state repair.
   receipts=json.loads(wp('eval',"$a=[];foreach(get_posts(['post_type'=>'flamingo_inbound','posts_per_page'=>-1,'post_status'=>'any']) as $p){$m=new Flamingo_Inbound_Message($p->ID);$a[]=['id'=>$p->ID,'fields'=>$m->fields];}echo wp_json_encode($a);"))
   assert len(receipts)==1,receipts
   # Compare ORIGINAL normal output with REPLAY normal output below. The
   # plugins may transform submitted input; never repair either input or output.
   return {'id':receipts[0]['id'],'status':r['status'],'fields':receipts[0]['fields']}
  raise ValueError('Unknown normal operation: '+op)
 return execute

def use_site(web,wp,url,c,outputs):
 # Credentials are not construction materials; use WordPress's normal reset flow.
 jar=http.cookiejar.CookieJar();reader=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
 lost=url+'/wp-login.php?action=lostpassword';f=mods['members'].Form(reader.open(lost).read().decode(),'lostpasswordform');p=f.values.copy();p['user_login']='technical-reader@example.invalid'
 reader.open(f.action or lost,urllib.parse.urlencode(p).encode()).read()
 mails=json.loads(d('exec',web,'cat','/tmp/member-mail.json'));links=[]
 for m in mails:links+=re.findall(r'https?://[^\s<>]+action=rp[^\s<>]+',m['message'])
 assert links
 response=reader.open(html.unescape(links[-1]));reseturl=response.geturl();f=mods['members'].Form(response.read().decode(),'resetpassform');p=f.values.copy();p.update(pass1='fixture-reset-only-456',pass2='fixture-reset-only-456',pw_weak='on')
 reader.open(f.action or reseturl,urllib.parse.urlencode(p).encode()).read()
 login=url+'/?page_id='+str(outputs['login']['id']);markup=reader.open(login).read().decode();forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',markup,re.S) if 'name="log"' in x];assert len(forms)==1
 f=mods['members'].Form(forms[0],None);p=f.values.copy();p.update(log='technical-reader',pwd='fixture-reset-only-456');reader.open(f.action or login,urllib.parse.urlencode(p).encode()).read()
 dest=url+'/?page_id='+str(outputs['material']['id']);member=reader.open(dest).read().decode();anon=urllib.request.build_opener(urllib.request.ProxyHandler({}));guest=anon.open(dest).read().decode()
 public=anon.open(url+'/?page_id='+str(outputs['public']['id'])).read().decode()
 profile=reader.open(url+'/?page_id='+str(outputs['profile']['id'])+'&a=edit').read().decode()
 receipt=c['markdown'].request('/wp-admin/admin.php?page=flamingo_inbound&post='+str(outputs['receipt']['id'])+'&action=edit')[0].decode()
 checks={'member_login':any('wordpress_logged_in_' in x.name for x in jar),'member_markdown':'TECHNICAL-DOCUMENT' in member,'member_table':'24 V' in member,'guest_blocked':'TECHNICAL-DOCUMENT' not in guest and 'MEMBER-MATERIAL' not in guest,'acf_value':'FORMAL-CAPTION' in public,'image_served':anon.open(outputs['image']['url']).status==200,'profile_field':'Technical Company' in profile,'flamingo_readable':'Combined inquiry' in receipt and 'PLC' in receipt}
 assert all(checks.values()),checks
 return checks

try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 envs=[]
 for label in ['source','target','again']:
  web,wp,url,client=setup(label);cs=clients(url);finish_onboarding(cs['members'])
  d('exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins','/var/www/html/wp-content/themes/acf-normal-fixture')
  d('cp',str(b/'observe.php'),web+':/var/www/html/wp-content/mu-plugins/observer.php')
  d('cp',str(b/'normal-operation.php'),web+':/tmp/normal-operation.php')
  d('exec',web,'chmod','a+r','/tmp/wp.phar','/tmp/normal-operation.php')
  for f in ['style.css','functions.php','index.php']:d('cp',str(b/f),web+':/var/www/html/wp-content/themes/acf-normal-fixture/'+f)
  wp('theme','activate','acf-normal-fixture')
  if label!='source':
   for i in range(7 if label=='target' else 15):client.rest('pages',{'title':'Prepared filler '+str(i),'status':'draft'})
  envs.append((web,wp,url,cs,fingerprint(wp)))
 web,wp,url,c,_=envs[0];record=Record(b/(name+'-source.jsonl'),dispatcher(web,wp,url,c));do=record.execute
 results['versions']=json.loads(wp('plugin','list','--status=active','--fields=name,version','--format=json'))
 # Inputs/references are declared NOW, before the original operation, never derived afterwards.
 do('image','media',{'filename':'diagram.png','title':'Diagram','base64':'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jp1sAAAAASUVORK5CYII='})
 do('category','rest',{'endpoint':'categories','body':{'name':'Technical'}})
 do('public','rest',{'endpoint':'pages','body':{'title':'Public explanation','content':text('PUBLIC-EXPLANATION <img src="',ref('image','url'),'" alt="Diagram"/>'),'status':'draft'}})
 do('article','rest',{'endpoint':'posts','body':{'title':'Article','content':'ARTICLE-MATERIAL','categories':[ref('category')],'status':'publish'}})
 do('menu','menu',{'name':'Technical menu'})
 do('menu-link','menu-item',{'menu':ref('menu'),'item':{'menu-item-object-id':ref('public'),'menu-item-object':'page','menu-item-type':'post_type','menu-item-status':'publish'}})
 do('acf-definition','acf-definition',{'key':'group_combined','title':'Technical fields','fields':[{'key':'field_combined_caption','name':'technical_caption','label':'Caption','type':'text','instructions':'説明を入力'}],'location':[[{'param':'post_type','operator':'==','value':'page'}]],'active':True})
 table={'name':'Technical readings','description':'Public values','data':[['Device','Voltage'],['PLC','24 V']],'options':{'table_head':1,'table_foot':0,'use_datatables':False},'visibility':{'rows':[1,1],'columns':[1,1]}}
 do('table','table-import',table)
 raw=text('# TECHNICAL-DOCUMENT\n\n説明です。\n![Diagram](',ref('image','url'),')\n')
 do('document','markdown-import',{'raw':raw,'filename':'technical.md'})
 docsettings={'title':'Technical document','slug':'technical-document','status':'publish','password':'','date':'2026-11-28 10:00:00','author_destination':1}
 do('document-save','markdown-save',{'id':ref('document'),'raw':raw,'settings':docsettings})
 mail={'subject':'Technical inquiry [your-subject]','sender':'Fixture <sender@example.invalid>','recipient':'operator@example.invalid','body':'Technical inquiry: [probe]','additional_headers':'Reply-To: [your-email]','attachments':'','use_html':False,'exclude_blank':False}
 do('form','cf7-create',{'title':'Technical inquiry','form':'[text* your-name]\n[email* your-email]\n[text your-subject]\n[textarea probe]\n[submit "Send"]','locale':'en_US','mail':mail,'additional_settings':'','context':'save'})
 for key,title,body in [('login','Member login','[wpmem_form login]'),('profile','Member profile','[wpmem_profile]'),('contact','Contact',text('[contact-form-7 id="',ref('form'),'"]')),('material','Member technical material',text('MEMBER-MATERIAL\n[ozeki_markdown_document id="',ref('document'),'"]\n[table id="',ref('table'),'" /]'))]:
  do(key,'rest',{'endpoint':'pages','body':{'title':title,'content':body,'status':'draft'}})
 # WP-Members' ordinary selector lists published pages. Publish these public
 # login/profile pages before selecting them, on BOTH original and replay.
 for key in ['login','profile']:
  do(key+'-publish','rest',{'endpoint':text('pages/',ref(key)),'body':{'status':'publish'}})
 do('member-pages','member-pages',{'login':ref('login'),'profile':ref('profile')})
 do('member-field','member-field',{'0':17,'1':'Company','2':'company','3':'text','4':'y','5':'n','6':'n','profile':True,'placeholder':'Company','pattern':'','title':''})
 do('member-access','member-access',{'id':ref('material'),'value':'1'})
 do('member','member-create',{'user':{'user_login':'technical-reader','user_email':'technical-reader@example.invalid','display_name':'Technical Reader','user_url':''},'meta':{'nickname':['technical-reader'],'first_name':['Technical'],'last_name':['Reader'],'company':['Technical Company']}})
 do('acf-value','acf-values',{'id':ref('public'),'values':{'field_combined_caption':'FORMAL-CAPTION'}})
 for key in ['contact','material','public']:
  do(key+'-publish','rest',{'endpoint':text('pages/',ref(key)),'body':{'status':'publish'}})
 do('receipt','cf7-submit',{'page':ref('contact'),'form':ref('form'),'values':{'your-name':'Fixture Technician','your-email':'technician@example.invalid','your-subject':'Combined inquiry','probe':r'PLC C:\technical\manual 日本語'}})
 results['source_checks']=use_site(web,wp,url,c,record.outputs)
 source_hash=hashlib.sha256(record.path.read_bytes()).hexdigest()
 web,wp,url,c,_=envs[1];target=Record.replay(record.path,b/(name+'-target.jsonl'),dispatcher(web,wp,url,c))
 results['target_checks']=use_site(web,wp,url,c,target.outputs)
 # Record ordinary editing at the time it happens, then replay that extended record.
 target.execute('public-edit','rest',{'endpoint':text('pages/',ref('public')),'body':{'title':'Edited public explanation'}})
 target.execute('public-resave','rest',{'endpoint':text('pages/',ref('public')),'body':{'title':'Edited public explanation'}})
 target.execute('document-resave','markdown-save',{'id':ref('document'),'raw':raw,'settings':docsettings})
 target.execute('table-resave','table-save',{'id':ref('table'),'table':table})
 target.execute('acf-resave','acf-values',{'id':ref('public'),'values':{'field_combined_caption':'FORMAL-CAPTION'}})
 web,wp,url,c,_=envs[2];again=Record.replay(target.path,b/(name+'-again.jsonl'),dispatcher(web,wp,url,c))
 results['again_checks']=use_site(web,wp,url,c,again.outputs)
 results['edited_title_preserved']=c['markdown'].rest('pages/'+str(again.outputs['public']['id'])+'?context=edit')['title']['raw']=='Edited public explanation'
 results['distinct_page_ids']=len({r.outputs['material']['id'] for r in [record,target,again]})==3
 results['plugins_unchanged']=all(fp==fingerprint(wp) for web,wp,url,c,fp in envs)
 results['no_member_initialization']=all(subprocess.run(D+['exec',web,'test','-f','/tmp/member-initializer-used'],capture_output=True).returncode!=0 for web,*_ in envs)
 results['source_record_unchanged']=source_hash==hashlib.sha256(record.path.read_bytes()).hexdigest()
 results['normal_receipt_output_equal']=record.outputs['receipt']['fields']==target.outputs['receipt']['fields']==again.outputs['receipt']['fields']
 results['receipt_input']=record.resolve({'your-name':'Fixture Technician','probe':r'PLC C:\technical\manual 日本語'},record.outputs)
 results['receipt_normal_output']=record.outputs['receipt']['fields']
 results['operation_counts']=[r.sequence for r in [record,target,again]]
 results['records']=[str(r.path) for r in [record,target,again]]
 results['all_checks_passed']=all(results[k] for k in ['edited_title_preserved','distinct_page_ids','plugins_unchanged','no_member_initialization','source_record_unchanged','normal_receipt_output_equal'])
 assert results['all_checks_passed'],results
 results['s3_used']=False
except Exception as e:
 results['error']=str(e)
 import traceback
 results['traceback']=traceback.format_exc()
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
