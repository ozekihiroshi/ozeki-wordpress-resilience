from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64,re
b=Path('/tmp/combined-normal-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='combined-normal-'+str(int(time.time()))
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

try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 source,swp,surl,sc=setup('source');target,twp,turl,tc=setup('target');src=clients(surl);dst=clients(turl)
 finish_onboarding(src['members']);finish_onboarding(dst['members']);sb=fingerprint(swp);tb=fingerprint(twp)
 results['versions']=json.loads(swp('plugin','list','--status=active','--fields=name,version','--format=json'))
 for web,wp in [(source,swp),(target,twp)]:
  d('cp',str(b/'material.php'),web+':/tmp/material.php');d('exec',web,'mkdir','-p','/var/www/html/wp-content/themes/acf-normal-fixture')
  for f in ['style.css','functions.php','index.php']:d('cp',str(b/f),web+':/var/www/html/wp-content/themes/acf-normal-fixture/'+f)
  wp('theme','activate','acf-normal-fixture')
 native=json.loads(swp('eval-file','/tmp/material.php','native-source'))
 table={'name':'Technical readings','description':'Public values','data':[['Device','Voltage'],['PLC','24 V']],'options':{'table_head':1,'table_foot':0,'use_datatables':False},'visibility':{'rows':[1,1],'columns':[1,1]}}
 tid=src['tablepress'].import_table(table)
 raw=('# TECHNICAL-DOCUMENT\n\n説明です。\n![Diagram]('+native['url']+')\n').encode()
 doc=src['markdown'].import_document(raw,'technical.md');docitem={'title':'Technical document','slug':'technical-document','status':'publish','password':'','date':'2026-11-28 10:00:00','author_destination':1}
 src['markdown'].save(doc,raw,docitem)
 mail={'subject':'Technical inquiry [your-subject]','sender':'Fixture <sender@example.invalid>','recipient':'operator@example.invalid','body':'Technical inquiry: [probe]','additional_headers':'Reply-To: [your-email]','attachments':'','use_html':False,'exclude_blank':False}
 form=src['contact-form'].cf7(payload={'title':'Technical inquiry','form':'[text* your-name]\n[email* your-email]\n[text your-subject]\n[textarea probe]\n[submit "Send"]','locale':'en_US','mail':mail,'additional_settings':'','context':'save'})['id']
 def page(title,body):return sc.rest('pages',{'title':title,'content':body,'status':'publish'})['id']
 login=page('Member login','[wpmem_form login]');profile=page('Member profile','[wpmem_profile]');contact=page('Contact','[contact-form-7 id="'+str(form)+'"]')
 mixed=page('Member technical material','MEMBER-TECHNICAL-MATERIAL\n[ozeki_markdown_document id="'+str(doc)+'"]\n[table id="'+tid+'" /]')
 cfg=json.loads(swp('option','get','wpmembers_settings','--format=json'));cfg['user_pages']={'login':login,'profile':profile,'register':0}
 src['members'].save_settings({'wpmembers_settings':cfg},{str(login):login,str(profile):profile})
 # Set restriction through the normal editor before exposing the fixture page.
 sc.rest('pages/'+str(mixed),{'status':'draft'});src['members'].restriction(mixed,'page','1');sc.rest('pages/'+str(mixed),{'status':'publish'})
 user={'user':{'user_login':'technical-reader','user_email':'technical-reader@example.invalid','display_name':'Technical Reader','user_url':''},'meta':{'nickname':['technical-reader'],'first_name':['Technical'],'last_name':['Reader']}}
 uid=src['members'].create_member(user,'source-member-only-123')
 src['acf'].save_values(native['page'],'page',{'field_combined_caption':'BASELINE-CAPTION'})
 # Capture genuine CF7 -> Flamingo registration inputs with the existing local Store fixture.
 d('exec',source,'mkdir','-p','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'receipt-fixture.php'),source+':/var/www/html/wp-content/mu-plugins/receipt-fixture.php');swp('option','update','fixture_protect','1')
 markup=sc.request('/?page_id='+str(contact))[0].decode();controls=module.Fields(markup).values
 pairs={k:v for k,v in controls.items() if k.startswith('_wpcf7')};pairs.update({'your-name':'Fixture Technician','your-email':'technician@example.invalid','your-subject':'Combined inquiry','probe':r'PLC C:\technical\manual 日本語'})
 boundary='----CombinedReceipt';body=b''
 for k,v in pairs.items():body+=('--'+boundary+'\r\nContent-Disposition: form-data; name="'+k+'"\r\n\r\n'+v+'\r\n').encode()
 body+=('--'+boundary+'--\r\n').encode();anonymous=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 results['source_receipt']=json.loads(anonymous.open(urllib.request.Request(surl+'/?rest_route=/contact-form-7/v1/contact-forms/'+str(form)+'/feedback',body,headers={'Content-Type':'multipart/form-data; boundary='+boundary}),timeout=30).read())
 swp('option','update','fixture_protect','0')
 # Check the source fixture is usable before preserving it.
 jar=http.cookiejar.CookieJar();reader=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
 markup=reader.open(surl+'/?page_id='+str(login)).read().decode();forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',markup,re.S) if 'name="log"' in x];assert len(forms)==1
 f=mods['members'].Form(forms[0],None);p=f.values.copy();p.update(log='technical-reader',pwd='source-member-only-123');reader.open(f.action or surl+'/?page_id='+str(login),urllib.parse.urlencode(p).encode()).read()
 view=reader.open(surl+'/?page_id='+str(mixed)).read().decode();guest=anonymous.open(surl+'/?page_id='+str(mixed)).read().decode()
 results['source_usable']={'member_login':any('wordpress_logged_in_' in c.name for c in jar),'member_document':'TECHNICAL-DOCUMENT' in view,'member_table':'24 V' in view,'guest_blocked':'MEMBER-TECHNICAL-MATERIAL' not in guest}
 assert all(results['source_usable'].values()),results['source_usable']
 results['source_ids']={**native,'table':tid,'document':doc,'form':form,'login':login,'profile':profile,'contact':contact,'mixed':mixed,'user':uid}
 results['baseline']=json.loads(swp('eval-file','/tmp/material.php','capture'))
 src['acf'].save_values(native['page'],'page',{'field_combined_caption':'FORMAL-CAPTION'})
 plans=json.loads(swp('eval-file','/tmp/material.php','select',str(native['page'])))
 results['plan_summary']={k:{'counts':{n:len(v[n]) for n in ['documents','images','tables','forms','receipts','users','groups','posts','pages'] if n in v},'held':v.get('held',{}),'error':v.get('error')} for k,v in plans.items()}
 before=swp('eval',"echo hash_file('sha256','/tmp/combined-baseline.bin').':'.hash_file('sha256','/tmp/combined-selected.bin');").strip()
 d('cp',source+':/tmp/combined-selected.bin',str(b/(name+'-selected.bin')));d('cp',str(b/(name+'-selected.bin')),target+':/tmp/combined-selected.bin')
 for i in range(40):tc.rest('pages',{'title':'Prepared '+str(i),'content':'Prepared destination','status':'draft'})
 dst['tablepress'].import_table({**table,'name':'Prepared table'})
 results['stages']={};nr=attempt('native',lambda:json.loads(twp('eval-file','/tmp/material.php','native')))
 mapping=(nr or {}).get('result',{}).get('posts',{}) or (nr or {}).get('journal',{}).get('posts',{}) or {}
 mapping={str(k):v for k,v in mapping.items()}
 for key,clientkey in [('markdown','markdown'),('table','tablepress'),('cf7','contact-form')]:
  r=attempt(key,lambda key=key,clientkey=clientkey:dst[clientkey].rebuild(plans[key],b/(name+'-'+key+'.json'),{'1':1}))
  if r:
   for old,new in r.get('pages',{}).items():
    if old in mapping and mapping[old]!=new:raise RuntimeError('Conflicting owner mapping; no correction')
    mapping[old]=new
 results['shared_page_map']=mapping
 attempt('members',lambda:dst['members'].rebuild(plans['members'],mapping,b/(name+'-members.json'),password_reset=True))
 attempt('acf',lambda:dst['acf'].rebuild(plans['acf'],mapping,b/(name+'-acf.json')))
 cfmap=results['stages'].get('cf7',{}).get('forms',{})
 for filename,data in [('fl-plan.json',plans['flamingo']),('cf-map.json',cfmap)]:
  path=b/(name+'-'+filename);path.write_text(json.dumps(data));d('cp',str(path),target+':/tmp/'+filename)
 attempt('flamingo',lambda:json.loads(twp('eval-file','/tmp/material.php','flamingo')))
 # Verify only objects that existing implementations actually created; do not create substitute pages.
 results['independent_checks']={}
 tr=results['stages'].get('table',{}).get('tables',{})
 if tid in tr:
  obj=dst['tablepress'].export_table(tr[tid]);edit={k:obj[k] for k in ['name','description','data','options','visibility']};edit['data'][1][1]='48 V';dst['tablepress'].save_table(tr[tid],edit);dst['tablepress'].save_table(tr[tid],edit)
  results['independent_checks']['table_edit_resave']=dst['tablepress'].export_table(tr[tid])['data'][1][1]=='48 V'
 if str(form) in cfmap:
  new=cfmap[str(form)];obj=dst['contact-form'].inputs(dst['contact-form'].cf7(new));obj['form']+='\n<p>EDITED-FORM</p>';dst['contact-form'].save_form(new,obj);dst['contact-form'].save_form(new,obj)
  results['independent_checks']['cf7_edit_resave']=dst['contact-form'].inputs(dst['contact-form'].cf7(new))==obj
 fr=results['stages'].get('flamingo',{})
 results['independent_checks']['flamingo_readable']=bool(fr.get('receipts'))
 for old,new in fr.get('receipts',{}).items():
  view=tc.request('/wp-admin/admin.php?page=flamingo_inbound&post='+str(new)+'&action=edit')[0].decode();results['independent_checks']['flamingo_readable'] &= 'Combined inquiry' in view and 'PLC' in view
 results['destination_limits']={'public_page_missing':str(native['page']) not in mapping,'member_material_missing':str(mixed) not in mapping,'member_login_not_reached':not results['stages'].get('members',{}).get('users'),'acf_owner_missing':str(native['page']) not in mapping,'no_substitute_pages_or_privacy_bypass':True}
 results['source_material_unchanged']=before==swp('eval',"echo hash_file('sha256','/tmp/combined-baseline.bin').':'.hash_file('sha256','/tmp/combined-selected.bin');").strip()
 results['plugins_unchanged']=sb==fingerprint(swp) and tb==fingerprint(twp)
 results['end_to_end_complete']=False if any(results['destination_limits'][k] for k in ['public_page_missing','member_material_missing','member_login_not_reached','acf_owner_missing']) else True
 results['s3_used']=False
except Exception as e:
 results['harness_error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
