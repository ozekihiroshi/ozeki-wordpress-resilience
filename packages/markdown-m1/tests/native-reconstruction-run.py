from pathlib import Path
import subprocess,time,json,hashlib,urllib.request,urllib.parse,http.cookiejar,re,html,zipfile
b=Path('/tmp/native-wordpress-implementation-20261128');old=Path('/tmp/owr-community-rc23-roundtrip-20261128')
D=['/srv/dm-laravel-clone-20261116/docker/docker','-H','unix:///srv/dm-laravel-clone-20261116/docker.sock'];made=[];results={};start=time.monotonic();name='wp-native-'+str(int(time.time()))
def d(*a):
 p=subprocess.run(D+list(a),capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError(p.stderr[:1800]+p.stdout[-800:])
 return p.stdout
try:
 net=name+'-net';d('network','create','--internal',net);made.append(('network',net))
 db=name+'-db';d('run','-d','--name',db,'--network',net,'--memory','512m','--tmpfs','/var/lib/mysql','-e','MARIADB_ROOT_PASSWORD=fixture','-e','MARIADB_DATABASE=fixture','-e','MARIADB_USER=fixture','-e','MARIADB_PASSWORD=fixture','mariadb:10.11');made.append(('container',db))
 for _ in range(60):
  if subprocess.run(D+['exec',db,'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True).returncode==0:break
  time.sleep(1)
 web=name+'-web';vol=web+'-vol';d('volume','create',vol);made.append(('volume',vol))
 d('run','-d','--name',web,'--network',net,'--memory','512m','-v',vol+':/var/www/html','-e','WORDPRESS_DB_HOST='+db,'-e','WORDPRESS_DB_NAME=fixture','-e','WORDPRESS_DB_USER=fixture','-e','WORDPRESS_DB_PASSWORD=fixture','-e',"WORDPRESS_CONFIG_EXTRA=define('DISABLE_WP_CRON',true);define('AUTOMATIC_UPDATER_DISABLED',true);define('WP_HTTP_BLOCK_EXTERNAL',true);",'wordpress:php8.3-apache');made.append(('container',web))
 for _ in range(60):
  if subprocess.run(D+['exec',web,'test','-f','/var/www/html/wp-config.php'],capture_output=True).returncode==0:break
  time.sleep(1)
 d('exec',web,'sh','-c','echo memory_limit=256M > /usr/local/etc/php/conf.d/fixture-memory.ini')
 d('cp',str(old/'core/wordpress')+'/.',web+':/var/www/html/');d('cp',str(old/'wp.phar'),web+':/tmp/wp.phar')
 def wp(*a):return d('exec',web,'php','/tmp/wp.phar','--allow-root',*a)
 d('exec',web,'chown','-R','www-data:www-data','/var/www/html')
 ip=json.loads(d('inspect',web))[0]['NetworkSettings']['Networks'][net]['IPAddress'];base='http://'+ip
 wp('core','install','--url='+base,'--title=Native rebuild fixture','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email')
 wp('rewrite','structure','');wp('theme','activate','twentytwentyfive');wp('option','update','blog_public','0')
 results['wordpress']=wp('core','version').strip();results['theme']=wp('theme','list','--status=active','--field=name').strip();results['active_plugins']=json.loads(wp('option','get','active_plugins','--format=json'))
 d('cp',str(b/'product'),web+':/tmp/product')
 results['runs']=[]
 def fresh(prefix):
  wp('config','set','table_prefix',prefix,'--type=variable')
  wp('core','install','--url='+base,'--title=Native fixture','--admin_user=operator','--admin_password=isolated-only-123','--admin_email=operator@example.invalid','--skip-email')
  wp('rewrite','structure','');wp('option','update','blog_public','0');wp('option','update','upload_path','wp-content/uploads/'+prefix)
 for size in [10,100]:
  fresh('src'+str(size)+'_');wp('option','update','home','http://source.invalid');wp('option','update','siteurl','http://source.invalid')
  results['source_'+str(size)]=json.loads(wp('eval-file','/tmp/product/tests/native-reconstruction.php','source',str(size)))
  for repeat in range(3):
   for method in ['native','legacy']:
    fresh(method+str(size)+'r'+str(repeat)+'_')
    applied=json.loads(wp('eval-file','/tmp/product/tests/native-reconstruction.php','apply',str(size),method))
    if method=='native':
     verified=json.loads(wp('eval-file','/tmp/product/tests/native-reconstruction.php','verify'));applied['verified']=verified
     if not all(verified['checks'].values()):raise RuntimeError('native state failed: '+json.dumps({'verified':verified,'held':applied['result'].get('held')}))
     d('exec',web,'chown','-R','www-data:www-data','/var/www/html/wp-content/uploads')
     anon=urllib.request.build_opener(urllib.request.ProxyHandler({}));op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
     def get(path):return anon.open(base+path,timeout=30).read().decode()
     applied['http_display']='FORMAL-APPEND' in get('/?p='+str(verified['article'])) and 'CONTENT-child' in get('/?page_id='+str(verified['child'])) and 'CONTENT-home' in get('/')
     applied['navigation_display']='Native child navigation' in get('/')
     applied['password_protected']='CONTENT-password' not in get('/?page_id='+str(verified['password']))
     applied['image_http']=hashlib.sha256(anon.open(verified['image_url']).read()).hexdigest()
     op.open(base+'/wp-login.php').read();op.open(base+'/wp-login.php',urllib.parse.urlencode({'log':'operator','pwd':'isolated-only-123','wp-submit':'Log In','testcookie':'1','redirect_to':base+'/wp-admin/'}).encode()).read()
     nonce=op.open(base+'/wp-admin/admin-ajax.php?action=rest-nonce').read().decode().strip()
     def rest(path,data=None):
      req=urllib.request.Request(base+'/?rest_route='+urllib.parse.quote('/wp/v2/'+path,safe='/&=?'),data=json.dumps(data).encode() if data is not None else None,headers={'X-WP-Nonce':nonce,'Content-Type':'application/json'})
      return json.loads(op.open(req,timeout=30).read())
     article=str(verified['article']);before=rest('posts/'+article+'&context=edit')['content']['raw'];edited=before+'\n<!-- wp:paragraph --><p>REST-EDITED</p><!-- /wp:paragraph -->'
     rest('posts/'+article,{'content':edited});after=rest('posts/'+article+'&context=edit')['content']['raw'];rest('posts/'+article,{'content':after})
     applied['rest_edit_resave']=after==edited and 'REST-EDITED' in get('/?p='+article)
     child=str(verified['child']);child_body=rest('pages/'+child+'&context=edit')['content']['raw']+'<!-- wp:paragraph --><p>CHILD-EDITED</p><!-- /wp:paragraph -->';rest('pages/'+child,{'content':child_body});rest('pages/'+child,{'content':rest('pages/'+child+'&context=edit')['content']['raw']});applied['page_edit_resave']='CHILD-EDITED' in get('/?page_id='+child)
     nav=str(verified['navigation']);nav_body=rest('navigation/'+nav+'&context=edit')['content']['raw'].replace('Native child navigation','Edited child navigation');rest('navigation/'+nav,{'content':nav_body});applied['navigation_edit']='Edited child navigation' in get('/')
     applied['relations_after']=json.loads(wp('eval-file','/tmp/product/tests/native-reconstruction.php','verify'))['checks']
     applied['menu_html']=wp('eval','echo wp_nav_menu(["menu"=>'+str(verified['menu'])+',"echo"=>false]);')
     applied['menu_display']='Child menu' in applied.pop('menu_html')
    results['runs'].append({'size':size,'repeat':repeat,**applied})
 results['all_checks_passed']=all(x['source_unchanged'] and (x['method']=='legacy' or (x['prepared_page_preserved'] and x['prepared_setting_preserved'] and x['http_display'] and x['rest_edit_resave'] and x['menu_display'] and x['navigation_display'] and x['navigation_edit'] and x['page_edit_resave'] and x['password_protected'] and all(x['relations_after'].values()))) for x in results['runs'])
 results['s3_used']=False
except Exception as e:
 results['error']=str(e)
 if hasattr(e,'read'):results['http_error']=e.read().decode(errors='replace')[-1500:]
finally:
 errors=[]
 for kind,n in reversed(made):
  try:d(kind,'rm',*(['-f'] if kind=='container' else []),n)
  except Exception as e:errors.append(str(e))
 results['cleanup_errors']=errors;results['elapsed_seconds']=round(time.monotonic()-start,2);(b/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps({'error':results.get('error'),'all_checks_passed':results.get('all_checks_passed'),'runs':len(results.get('runs',[])),'elapsed_seconds':results['elapsed_seconds'],'cleanup_errors':errors},ensure_ascii=False))
