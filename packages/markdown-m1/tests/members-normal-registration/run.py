from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64,re
b=Path('/tmp/members-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='fl-contract-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-members.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'wp-members.zip'),web+':/tmp/wp-members.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=CF7 normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/wp-members.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')

 client=module.NormalMemberClient(url,'operator','isolated-only-123',True)
 # Fixture preparation only: complete the plugin's ordinary onboarding before observation.
 markup=client.request(client.settingsurl)[0].decode()
 forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',markup,re.S) if 'name="wpmem_onboarding_action"' in x]
 assert len(forms)==1,'Expected ordinary onboarding form'
 form=module.Form(forms[0],None);payload=form.values.copy();payload.pop('optin',None)
 client.request(form.action or client.settingsurl,payload)
 prepared=json.loads(wp('option','get','wpmembers_settings','--format=json'))
 assert prepared['install_state'].startswith('install_complete_'),prepared['install_state']
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/wp-members/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()




try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 source,swp,surl,sc=setup('source');target,twp,turl,tc=setup('target');sb=fingerprint(swp);tb=fingerprint(twp)
 for web in [source,target]:
  d('exec',web,'mkdir','-p','/var/www/html/wp-content/mu-plugins');d('cp',str(b/'observe.php'),web+':/var/www/html/wp-content/mu-plugins/member-observer.php');d('cp',str(b/'capture.php'),web+':/tmp/capture.php')
 def settings(wp):return json.loads(wp('option','get','wpmembers_settings','--format=json'))
 prepared=settings(twp)
 company={'0':17,'1':'Company / affiliation','2':'company','3':'text','4':'y','5':'n','6':'n','profile':True,'placeholder':'Company','pattern':'','title':''}
 results['source_field']=sc.save_field(company)
 def page(c,title,body,status='draft'):return c.rest('pages',{'title':title,'content':body,'status':status})['id']
 sl=page(sc,'Member login','[wpmem_form login]','publish');sp=page(sc,'Member profile','[wpmem_profile]','publish');sr=page(sc,'Member explanation','MEMBER-MATERIAL-791');su=page(sc,'Public explanation','PUBLIC-MATERIAL-793')
 initial=settings(swp);initial['user_pages']={'login':sl,'profile':sp,'register':0}
 # Apply ordinary options and access before publishing the source material.
 sc.save_settings({'wpmembers_settings':initial},{str(sl):sl,str(sp):sp})
 sc.restriction(sr,'page','1')
 for pid in [sl,sp,sr,su]:sc.rest('pages/'+str(pid),{'status':'publish'})
 item={'origin_id':'synthetic','user':{'user_login':'fixture-reader','user_email':'fixture-reader@example.invalid','display_name':'Fixture Reader','user_url':''},'meta':{'nickname':['fixture-reader'],'first_name':['Fixture'],'last_name':['Reader'],'company':['SYNTHETIC-COMPANY-OLD']}}
 uid=sc.create_member(item,'source-reader-only-123');results['source_user']=uid
 baseline=json.loads(swp('eval-file','/tmp/capture.php','baseline'))
 item['meta']['company']=['SYNTHETIC-COMPANY-NEW'];sc.save_profile(uid,item)
 captured=json.loads(swp('eval-file','/tmp/capture.php','plan'));plan=captured['plan'];results['material']={'baseline':baseline,'hash_in_original':captured['raw_hash_present'],'original_unchanged':captured['unchanged'],'through':plan['through'],'users':len(plan['users'])}
 assert plan['users'][0]['meta']['company']==['SYNTHETIC-COMPANY-NEW'] and 'user_pass' not in plan['users'][0]['user']
 for i in range(5):page(tc,'Target filler '+str(i),'filler')
 mapping={str(sl):page(tc,'Member login','[wpmem_form login]','publish'),str(sp):page(tc,'Member profile','[wpmem_profile]','publish'),str(sr):page(tc,'Member explanation','MEMBER-MATERIAL-791'),str(su):page(tc,'Public explanation','PUBLIC-MATERIAL-793')}
 # Remove unrelated default sample posts from the selected scope, without modifying originals.
 selected={**plan,'restrictions':[x for x in plan['restrictions'] if x['origin_id'] in mapping]}
 no_password=tc.rebuild(selected,mapping,b/(name+'-no-password.json'));results['no_password']=no_password
 assert not no_password['users'] and ('user:'+str(uid)) in no_password['held']
 twp('user','create','target-prepared-user','target-prepared@example.invalid','--role=subscriber','--user_pass=isolated-prepared-123')
 actual=tc.rebuild(selected,mapping,b/(name+'-rebuild.json'),password_reset=True);results['rebuild']=actual
 assert str(uid) in actual['users'],actual
 newuid=actual['users'][str(uid)];assert newuid!=uid and int(mapping[str(sr)])!=sr
 for oldid,pid in mapping.items():
  assert tc.rest('pages/'+str(pid)+'?context=edit')['status']==('publish' if oldid in (str(sl),str(sp)) else 'draft')
  tc.rest('pages/'+str(pid),{'status':'publish'})
 import http.cookiejar,re,html
 anon=urllib.request.build_opener(urllib.request.ProxyHandler({}));jar=http.cookiejar.CookieJar();reader=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
 # Member sets a new password through core's actual emailed reset link.
 lost=turl+'/wp-login.php?action=lostpassword';f=module.Form(reader.open(lost).read().decode(),'lostpasswordform');data=f.values.copy();data['user_login']='fixture-reader@example.invalid'
 reader.open(f.action or lost,urllib.parse.urlencode(data).encode()).read()
 mail=json.loads(d('exec',target,'cat','/tmp/member-mail.json'))
 links=[]
 for m in mail:
  links+=re.findall(r'https?://[^\s<>]+action=rp[^\s<>]+',m['message'])
 assert links,'No normal password reset email link'
 link=html.unescape(links[-1]);assert link.startswith(turl+'/')
 response=reader.open(link);reseturl=response.geturl();form=module.Form(response.read().decode(),'resetpassform');p=form.values.copy();p.update(pass1='target-reader-only-456',pass2='target-reader-only-456',pw_weak='on')
 reader.open(form.action or reseturl,urllib.parse.urlencode(p).encode()).read()
 results['password_reset']={'standard_email_link':True,'external_mail_sent':False,'new_password_set_through_standard_form':True}
 def login(password):
  pageurl=turl+'/?page_id='+str(mapping[str(sl)]);markup=reader.open(pageurl).read().decode();forms=[x for x in re.findall(r'<form\b[^>]*>.*?</form>',markup,re.S) if 'name="log"' in x];assert len(forms)==1,'WP-Members login form missing';form=module.Form(forms[0],None);payload=form.values.copy();payload.update(log='fixture-reader',pwd=password);reader.open(form.action or pageurl,urllib.parse.urlencode(payload).encode()).read()
 login('source-reader-only-123');old_rejected=not any('wordpress_logged_in_' in c.name for c in jar)
 login('target-reader-only-456');assert any('wordpress_logged_in_' in c.name for c in jar)
 dest=turl+'/?page_id='+str(mapping[str(sr)]);member=reader.open(dest).read().decode();guest=anon.open(dest).read().decode();public=anon.open(turl+'/?page_id='+str(mapping[str(su)])).read().decode();profile=reader.open(turl+'/?page_id='+str(mapping[str(sp)])+'&a=edit').read().decode()
 assert 'MEMBER-MATERIAL-791' in member and 'MEMBER-MATERIAL-791' not in guest and 'PUBLIC-MATERIAL-793' in public and 'SYNTHETIC-COMPANY-NEW' in profile
 # Read-back only, no settings/user meta repair.
 target_fields=json.loads(twp('option','get','wpmembers_fields','--format=json'));source_fields=json.loads(swp('option','get','wpmembers_fields','--format=json'))
 source_company=next(x for x in source_fields if (x.get('2') if isinstance(x,dict) else x[2])=='company');target_company=next(x for x in target_fields if (x.get('2') if isinstance(x,dict) else x[2])=='company')
 after=settings(twp)
 results['checks']={'password_not_restored':old_rejected,'new_password_login':True,'saved_company_from_history':True,'member_allowed':True,'guest_denied':True,'public_visible':True,'profile_edit_visible':True,'company_definition_equal':source_company==target_company,'prepared_versions_retained':prepared['version']==after['version'] and prepared['db_version']==after['db_version'],'plugins_unchanged':sb==fingerprint(swp) and tb==fingerprint(twp),'source_material_unchanged':captured['baseline_sha256']==swp('eval',"echo hash_file('sha256','/tmp/member-material.json');").strip()}
 for web in [source,target]:
  results['checks'][web+'-no-initializer']=subprocess.run(D+['exec',web,'test','-f','/tmp/member-initializer-used'],capture_output=True).returncode!=0
 results['all_checks_passed']=all(results['checks'].values());assert results['all_checks_passed'],results['checks']
 results['s3_used']=False;results['plugin_version']=twp('plugin','get','wp-members','--field=version').strip()
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
