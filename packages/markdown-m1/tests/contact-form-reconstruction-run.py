from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64
b=Path('/tmp/cf7-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='cf7-registration-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-contact-form.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'contact-form-7.zip'),web+':/tmp/contact-form-7.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=CF7 normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/contact-form-7.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')
 client=module.NormalContactFormClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/contact-form-7/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()

try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 src,swp,surl,source=setup('source');sf=fingerprint(swp)
 results['wordpress']=swp('core','version').strip();results['cf7']=swp('plugin','get','contact-form-7','--field=version').strip()
 mail={'subject':'技術問い合わせ [equipment-code]','sender':'Fixture <sender@example.invalid>','recipient':'operator@example.invalid','body':'設備: [equipment-code]\n連絡先: [reply-address]\n本文: [details]','additional_headers':'Reply-To: [reply-address]','attachments':'','use_html':False,'exclude_blank':False}
 item={'title':'技術問い合わせ A & B','locale':'en_US','form':'<label>設備 [text* equipment-code]</label>\n<label>連絡先 [email* reply-address]</label>\n<label>種別 [select purpose "PLC" "太陽光"]</label>\n<label>説明 [textarea details]</label>\n[submit "確認"]','mail':mail,'mail_2':{**mail,'active':False},'messages':{'mail_sent_ok':'受付しました。'},'additional_settings':'demo_mode: on'}
 def add(**changes):return source.cf7(payload={**item,**changes,'context':'save'})['id']
 main=add();baseline=add(title='BASELINE-ONLY');restricted=add(title='RESTRICTED',additional_settings='demo_mode: on\nsubscribers_only: true');deleted=add(title='DELETED')
 # Explicit invalid recipient exercises CF7's own configuration-warning path.
 warning=add(title='MAIL-SETUP-REQUIRED',additional_settings='',mail={**mail,'recipient':'not-an-address'})
 sourcehash=swp('post','meta','get',str(main),'_hash').strip()
 page=source.rest('pages',{'title':'Forms','content':'<!-- wp:shortcode -->[contact-form-7 id="'+sourcehash+'" title="技術問い合わせ"]<!-- /wp:shortcode -->\n[contact-form-7 id='+str(baseline)+']','status':'publish'})['id']
 restrictedpage=source.rest('pages',{'title':'Restricted form','content':'[contact-form-7 id='+str(restricted)+']','status':'publish'})['id']
 deletedpage=source.rest('pages',{'title':'Removed form','content':'[contact-form-7 id='+str(deleted)+']','status':'publish'})['id']
 warningpage=source.rest('pages',{'title':'Needs preparation','content':'[contact-form-7 id='+str(warning)+']','status':'publish'})['id']
 results['baseline']=json.loads(swp('eval-file','/tmp/product/tests/contact-form-reconstruction.php','capture'))
 latest=source.inputs(source.cf7(main));latest['form']+='\n<label>正式追記 [text formal-field]</label>';source.save_form(main,latest);added=add(title='AFTER-BASELINE')
 results['history']=json.loads(swp('eval-file','/tmp/product/tests/contact-form-reconstruction.php','history','form:'+str(main),'delete:'+str(deleted),'form:'+str(added)))
 before=swp('eval',"echo hash_file('sha256','/tmp/cf7-materials.bin');").strip()
 initial=json.loads(swp('eval-file','/tmp/product/tests/contact-form-reconstruction.php','plan','0'));plan=json.loads(swp('eval-file','/tmp/product/tests/contact-form-reconstruction.php','plan','3'))
 checks={'baseline_and_history':'formal-field' not in next(x for x in initial['forms'] if x['origin_id']==str(main))['input']['form'] and 'formal-field' in next(x for x in plan['forms'] if x['origin_id']==str(main))['input']['form'],'deleted_removed':all(x['origin_id']!=str(deleted) for x in plan['forms'])}
 target,twp,turl,client=setup('target');tf=fingerprint(twp)
 twp('eval',"for($i=0;$i<20;$i++)wp_insert_post(['post_title'=>'Prepared '.$i,'post_status'=>'draft']);update_option('prepared_setting','keep');")
 prepared=client.cf7(payload={**item,'title':'PREPARED','context':'save'})['id'];prepared_before=client.cf7(prepared)
 settings=twp('option','get','wpcf7','--format=json').strip()
 report=client.rebuild(plan,b/('journal-'+name+'.json'),{'1':1});results['report']=report
 new=report['forms'][str(main)];pid=report['pages'][str(page)];anon=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def view(pid):return anon.open(turl+'/?page_id='+str(pid),timeout=30).read().decode()
 rendered=view(pid);private=view(report['pages'][str(restrictedpage)])
 checks.update(new_ids=all(int(k)!=v for k,v in report['forms'].items()),new_hash=twp('post','meta','get',str(new),'_hash').strip()!=sourcehash,hash_and_numeric_embed='<form' in rendered and 'formal-field' in rendered and 'purpose' in rendered,form_exact=client.inputs(client.cf7(new))['form']==latest['form'],unedited_form=client.inputs(client.cf7(report['forms'][str(baseline)]))['form']==item['form'],added_form=str(added) in report['forms'],restricted_anonymous='name="equipment-code"' not in private,restricted_authenticated='name="equipment-code"' in client.request('/?page_id='+str(report['pages'][str(restrictedpage)]))[0].decode(),deleted_page_held='page:'+str(deletedpage) in report['held'],warning_not_linked='page:'+str(warningpage) in report['held'] and str(warning) in report['config_errors'])
 edited=client.inputs(client.cf7(new));edited['form']+='\n<p>NORMAL-EDIT</p>';edited['messages']['mail_sent_ok']='通常の編集で変更';client.save_form(new,edited);client.save_form(new,edited)
 checks['edit_resave']=client.inputs(client.cf7(new))==edited and 'NORMAL-EDIT' in view(pid)
 raw=client.rest('pages/'+str(pid)+'?context=edit')['content']['raw']+'\n<p>PAGE-EDIT</p>';client.rest('pages/'+str(pid),{'content':raw});checks['page_edit_resave']='PAGE-EDIT' in view(pid) and 'NORMAL-EDIT' in view(pid)
 checks['prepared_form_unchanged']=client.cf7(prepared)==prepared_before;checks['prepared_setting_unchanged']=twp('option','get','prepared_setting').strip()=='keep' and twp('option','get','wpcf7','--format=json').strip()==settings
 checks['source_material_unchanged']=before==swp('eval',"echo hash_file('sha256','/tmp/cf7-materials.bin');").strip() and plan['input_unchanged'];checks['plugins_unchanged']=sf==fingerprint(swp) and tf==fingerprint(twp)
 # Partial old message maps are normal inputs; CF7 supplies defaults, never overwrite supplied values.
 legacy=client.cf7(payload={**item,'context':'save'});defaults=client.verify(legacy['id'],item);checks['normal_defaults_reported']=bool(defaults.get('messages')) and defaults.get('mail')=={'active':True};results['default_added_message_count']=len(defaults.get('messages',{}))
 negatives={}
 for kind in ['missing_mail','attachments','unknown_tag','event_handler','additional_script']:
  v=json.loads(json.dumps(item))
  if kind=='missing_mail':del v['mail']
  elif kind=='attachments':v['mail']['attachments']='/old/private.pdf'
  elif kind=='unknown_tag':v['form']+='\n[foreign-command]'
  elif kind=='event_handler':v['form']='<p onclick="alert(1)">bad</p>'
  else:v['additional_settings']='on_sent_ok: alert(1)'
  try:module.validate(v);negatives[kind]=False
  except module.Unsupported:negatives[kind]=True
 checks['unsupported_held']=all(negatives.values());results['negative_checks']=negatives;results['checks']=checks;results['s3_used']=False;results['mail_submitted']=False;results['all_checks_passed']=all(checks.values());assert results['all_checks_passed'],json.dumps(checks)
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
