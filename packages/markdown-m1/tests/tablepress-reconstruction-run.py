from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,urllib.error,importlib.util,base64
b=Path('/tmp/tablepress-registration-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='tp-registration-'+str(int(time.time()))
spec=importlib.util.spec_from_file_location('registration',b/'product/tools/reconstruct-tablepress.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
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
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar');d('cp',str(b/'tablepress.zip'),web+':/tmp/tablepress.zip');d('cp',str(b/'product'),web+':/tmp/product')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];url='http://'+ip
 wp('core','install','--url='+url,'--title=TablePress normal registration','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email');wp('rewrite','structure','');wp('option','update','blog_public','0');wp('plugin','install','/tmp/tablepress.zip','--activate')
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content')
 client=module.NormalTablePressClient(url,'operator','isolated-only-123',True)
 return web,wp,url,client

def fingerprint(wp):return wp('eval',"$root=WP_PLUGIN_DIR.'/tablepress/';$a=[];foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($root,FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$a[substr($f->getPathname(),strlen($root))]=hash_file('sha256',$f->getPathname());ksort($a);echo json_encode($a);").strip()
try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net));db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 src,swp,surl,source=setup('source');sf=fingerprint(swp)
 results['wordpress']=swp('core','version').strip();results['tablepress']=swp('plugin','get','tablepress','--field=version').strip()
 logical={'name':'技術表 "A" & B','description':'設備の説明 1 < 2','data':[['機器','電圧','備考'],['PLC','24 V','0'],['HIDDEN-ROW-792','12 V',''],['ZERO','0','日本語 & C:\\docs']],'options':{'table_head':1,'table_foot':0,'use_datatables':False,'print_name':True,'print_description':True},'visibility':{'rows':[1,1,0,1],'columns':[1,1,0]}}
 main=source.import_table(logical);unedited=source.import_table({**logical,'name':'UNEDITED'});deleted=source.import_table({**logical,'name':'DELETED'})
 page=source.rest('pages',{'title':'Table page','content':'<!-- wp:shortcode -->[table id="'+main+'" /]<!-- /wp:shortcode -->\n[table id='+unedited+' /]','status':'publish'})['id']
 private=source.rest('pages',{'title':'Private table page','content':'[table id='+main+' /]','status':'private'})['id']
 deletedpage=source.rest('pages',{'title':'Removed table','content':'[table id='+deleted+' /]','status':'publish'})['id']
 escaped=source.rest('pages',{'title':'Escaped example','content':'<p>&#91;table id='+main+' /]</p>','status':'publish'})['id']
 draft=source.rest('pages',{'title':'Draft','content':'[table id='+main+' /]','status':'draft'})['id']
 results['baseline']=json.loads(swp('eval-file','/tmp/product/tests/tablepress-reconstruction.php','capture'))
 before_edit=source.export_table(main);edit={k:before_edit[k] for k in ['name','description','data','options','visibility']};edit['data'][1][1]='FORMAL-48 V';source.save_table(main,edit)
 added=source.import_table({**logical,'name':'AFTER-BASELINE'})
 results['history']=json.loads(swp('eval-file','/tmp/product/tests/tablepress-reconstruction.php','history','table:'+main,'delete:'+deleted,'table:'+added))
 before=swp('eval',"echo hash_file('sha256','/tmp/tp-materials.bin');").strip()
 initial=json.loads(swp('eval-file','/tmp/product/tests/tablepress-reconstruction.php','plan','0'));plan=json.loads(swp('eval-file','/tmp/product/tests/tablepress-reconstruction.php','plan','3'))
 checks={'baseline_and_history':next(x for x in initial['tables'] if x['origin_id']==main)['table']['data'][1][1]=='24 V' and next(x for x in plan['tables'] if x['origin_id']==main)['table']['data'][1][1]=='FORMAL-48 V','deleted_removed':all(x['origin_id']!=deleted for x in plan['tables'])}
 target,twp,turl,client=setup('target');tf=fingerprint(twp)
 prepared=client.import_table({**logical,'name':'PREPARED'});prepared_before=client.export_table(prepared)
 for _ in range(4):client.import_table({**logical,'name':'PREPARED-OTHER'})
 twp('eval',"for($i=0;$i<20;$i++)wp_insert_post(['post_title'=>'Prepared '.$i,'post_status'=>'draft']);update_option('prepared_setting','keep');")
 settings=twp('option','get','tablepress_plugin_options').strip()
 report=client.rebuild(plan,b/('journal-'+name+'.json'),{'1':1});results['report']=report
 new=report['tables'][main];newpage=report['pages'][str(page)];anon=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def view(pid):
  try:return anon.open(turl+'/?page_id='+str(pid),timeout=30).read().decode()
  except urllib.error.HTTPError as e:
   if e.code in (403,404):return ''
   raise
 rendered=view(newpage)
 checks.update(new_table_ids=all(k!=v for k,v in report['tables'].items()),new_page_ids=all(int(k)!=v for k,v in report['pages'].items()),formal_values=client.export_table(new)['data']==edit['data'],unedited_values=client.export_table(report['tables'][unedited])['data']==logical['data'],new_table_values=client.export_table(report['tables'][added])['data']==logical['data'],display='<table' in rendered and 'FORMAL-48 V' in rendered and 'UNEDITED' in rendered,visibility='HIDDEN-ROW-792' not in rendered and 'C:\\docs' not in rendered,private_not_public='FORMAL-48 V' not in view(report['pages'][str(private)]),missing_table_page_held='page:'+str(deletedpage) in report['held'],draft_excluded='page:'+str(draft) in report['excluded'],escaped_not_enabled=str(escaped) not in report['pages'])
 actual=client.export_table(new);again={k:actual[k] for k in ['name','description','data','options','visibility']};again['data'][1][1]='EDITED-72 V';again['data'].append(['ADDED-ROW','6 V','']);again['visibility']['rows'].append(1);client.save_table(new,again);client.save_table(new,again)
 checks['edit_and_resave']=client.export_table(new)['data']==again['data'] and 'EDITED-72 V' in view(newpage) and 'ADDED-ROW' in view(newpage)
 checks['escaped_explicitly_held']='page:'+str(escaped) in report['held']
 body=client.rest('pages/'+str(newpage)+'?context=edit')['content']['raw']+'\n<p>PAGE-EDIT</p>';client.rest('pages/'+str(newpage),{'content':body});checks['page_edit_resave']='PAGE-EDIT' in view(newpage) and 'EDITED-72 V' in view(newpage)
 checks['prepared_table_unchanged']=client.export_table(prepared)==prepared_before;checks['prepared_settings_unchanged']=twp('option','get','tablepress_plugin_options').strip()==settings and twp('option','get','prepared_setting').strip()=='keep'
 checks['source_unchanged']=before==swp('eval',"echo hash_file('sha256','/tmp/tp-materials.bin');").strip() and plan['input_unchanged'] and source.export_table(main)['data']==edit['data']
 checks['plugins_unchanged']=sf==fingerprint(swp) and tf==fingerprint(twp)
 # Known incompleteness must be rejected before import, not silently truncated or sanitized.
 rejected={}
 for key in ['missing_visibility','unknown_option','custom_commands','html_cell','shortcode_cell']:
  t=json.loads(json.dumps(logical))
  if key=='missing_visibility':del t['visibility']
  elif key=='unknown_option':t['options']['extension_magic']=True
  elif key=='custom_commands':t['options']['datatables_custom_commands']='alert(1)'
  elif key=='html_cell':t['data'][1][0]='<script>alert(1)</script>'
  else:t['data'][1][0]='[contact-form-7 id="1"]'
  try:module.import_input(t);rejected[key]=False
  except module.Unsupported:rejected[key]=True
 checks['unsupported_held_without_conversion']=all(rejected.values());results['negative_checks']=rejected
 results['checks']=checks;results['s3_used']=False;results['all_checks_passed']=all(checks.values());assert results['all_checks_passed'],json.dumps(checks)
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[:1500]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
