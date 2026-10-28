"""Actual wp-load and HTTP regression in the caller's disposable Docker WordPress."""
import subprocess,json,hashlib

def verify(web,lab,wp):
 def run(*a):
  p=subprocess.run(a,capture_output=True,text=True,timeout=120)
  return p
 def php(code):
  p=run('docker','exec',web,'php','-r',code)
  assert p.returncode==0,p.stderr+p.stdout
  return p.stdout
 mu=r"""<?php
add_action('plugins_loaded',function(){
 if(!file_exists('/lab/startup-fault'))return;
 global $wpdb;
 if(trim(file_get_contents('/lab/startup-fault'))==='lock'){
  $db=new mysqli(DB_HOST,DB_USER,DB_PASSWORD,DB_NAME);
  $key='ozeki-resilience-identifiers-'.substr(hash('sha256',$wpdb->prefix),0,24);
  $stmt=$db->prepare('SELECT GET_LOCK(?,0)');$stmt->bind_param('s',$key);$stmt->execute();
  if($stmt->get_result()->fetch_row()[0]!=1)throw new RuntimeException('Fixture lock was not acquired');
  $GLOBALS['ozeki_resilience_fixture_lock']=$db;return;
 }
 $GLOBALS['ozeki_resilience_fixture_postmeta']=$wpdb->postmeta;
 $wpdb->postmeta=$wpdb->prefix.'missing_startup_fixture';
},-200);
add_action('plugins_loaded',function(){
 if(isset($GLOBALS['ozeki_resilience_fixture_lock']))$GLOBALS['ozeki_resilience_fixture_lock']->close();
 if(isset($GLOBALS['ozeki_resilience_fixture_postmeta'])){global $wpdb;$wpdb->postmeta=$GLOBALS['ozeki_resilience_fixture_postmeta'];}
},-90);
add_filter('wp_die_handler',function($handler){return function($message,$title,$args)use($handler){file_put_contents('/lab/startup-block-trace.json',json_encode(debug_backtrace(DEBUG_BACKTRACE_IGNORE_ARGS)));call_user_func($handler,$message,$title,$args);};});
add_filter('pre_determine_locale',function($locale){return file_exists('/lab/startup-ja')?'ja':$locale;});
"""
 import base64
 wp(web,'eval',"file_put_contents(ABSPATH.'wp-content/mu-plugins/startup-fixture.php',base64_decode('"+base64.b64encode(mu.encode()).decode()+"'));")
 wp(web,'eval',"$c=get_option('ozeki_resilience_m1_config');$c['protect']=true;update_option('ozeki_resilience_m1_config',$c);")
 wp(web,'eval',"update_option('ozeki_resilience_m1_pending',['fixture'=>'retain pending content']);update_option('ozeki_resilience_m1_comment_pending',[['fixture'=>'retain pending related data']]);")
 # Use an already protected site; a failed upgrade must not quietly disable protection.
 before=wp(web,'eval',"global $wpdb;echo wp_json_encode(['posts'=>$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),'meta'=>$wpdb->get_results('SELECT * FROM '.$wpdb->postmeta,ARRAY_A),'config'=>get_option('ozeki_resilience_m1_config'),'pending'=>get_option('ozeki_resilience_m1_pending'),'related'=>get_option('ozeki_resilience_m1_comment_pending')]);")
 wp(web,'eval',"delete_option('ozeki_resilience_identifiers_v1');")
 (lab/'startup-fault').write_text('1')
 # No catch around wp-load: this is the missing regression from the previous candidate.
 out=php("require '/var/www/html/wp-load.php';echo OzekiResilience\\M1\\Startup::ready()?'BAD':'READ_ONLY_BOOT_OK';")
 assert out=='READ_ONLY_BOOT_OK',out
 def http(path,method='GET',data=None,cookies=False):
  a=['docker','exec',web,'curl','-sS','-w','\n%{http_code}','--max-time','30','-X',method]
  if cookies:a+=['-b','/tmp/startup-cookies','-c','/tmp/startup-cookies']
  if data is not None:a+=['--data',data]
  a+=['http://'+web+path]
  p=run(*a);assert p.returncode==0,p.stderr
  body,status=p.stdout.rsplit('\n',1)
  return body,int(status)
 body,status=http('/');assert status==200 and 'Save settings' in body,(status,body[:300])
 body,status=http('/wp-login.php');assert status==200
 # Core checks credentials. Host header must match WordPress's configured site host for cookies.
 run('docker','exec',web,'curl','-sS','-c','/tmp/startup-cookies','http://'+web+'/wp-login.php')
 p=run('docker','exec',web,'curl','-sS','-c','/tmp/startup-cookies','-b','/tmp/startup-cookies','--data','log=operator&pwd=lab-only-password&wp-submit=Log+In&testcookie=1','-w','\n%{http_code}','http://'+web+'/wp-login.php')
 assert p.stdout.endswith('302'),p.stdout[-500:]
 def admin(locale):
  if locale=='ja':(lab/'startup-ja').write_text('1')
  else:(lab/'startup-ja').unlink(missing_ok=True)
  p=run('docker','exec',web,'curl','-sS','-b','/tmp/startup-cookies','-w','\n%{http_code}','http://'+web+'/wp-admin/tools.php?page=ozeki-resilience')
  body,status=p.stdout.rsplit('\n',1);assert status=='200',(status,body[-300:])
  assert ('再試行' if locale=='ja' else 'Retry') in body
  assert ('保存を一時停止' if locale=='ja' else 'Saving is temporarily paused') in body
 for locale in ['en','ja']:admin(locale)
 (lab/'startup-ja').unlink(missing_ok=True)
 for path in ['/wp-comments-post.php','/wp-admin/admin-ajax.php','/wp-admin/admin-post.php','/?rest_route=/wp/v2/posts','/?rest_route=/contact-form-7/v1/contact-forms/1/feedback']:
  body,status=http(path,'POST','content=must-not-save');assert status==503,(path,status,body[:200])
 # REST method overrides still hit the REST guard; GET itself remains readable.
 body,status=http('/?rest_route=/wp/v2/posts&_method=POST');assert status==503,(status,body[:300])
 failed=run('docker','exec',web,'php','/lab/wp','post','create','--post_title=Blocked write','--post_status=publish','--allow-root')
 assert failed.returncode!=0,failed.stdout
 after=wp(web,'eval',"global $wpdb;echo wp_json_encode(['posts'=>$wpdb->get_results('SELECT * FROM '.$wpdb->posts,ARRAY_A),'meta'=>$wpdb->get_results('SELECT * FROM '.$wpdb->postmeta,ARRAY_A),'config'=>get_option('ozeki_resilience_m1_config'),'pending'=>get_option('ozeki_resilience_m1_pending'),'related'=>get_option('ozeki_resilience_m1_comment_pending')]);")
 assert json.loads(before)==json.loads(after),'Content/config/queue changed during failed startup'
 (lab/'startup-fault').write_text('lock')
 assert php("require '/var/www/html/wp-load.php';echo OzekiResilience\\M1\\Startup::ready()?'BAD':'LOCK_BUSY_CONTAINED';")=='LOCK_BUSY_CONTAINED'
 body,status=http('/');assert status==200
 (lab/'startup-fault').unlink()
 assert php("require '/var/www/html/wp-load.php';echo OzekiResilience\\M1\\Startup::ready()?'READY':'BAD';")=='READY'
 assert '1'==wp(web,'eval',"echo get_option('ozeki_resilience_identifiers_v1');").strip()
 wp(web,'eval',"delete_option('ozeki_resilience_m1_pending');delete_option('ozeki_resilience_m1_comment_pending');") # Remove only the synthetic sentinels after equality was proved.
 # Protection was never switched off. A normal save must create confirmed history again.
 n=int(wp(web,'eval',"echo count((new OzekiResilience\\M1\\Plugin())->store()->history());"))
 wp(web,'eval',"wp_set_current_user(1);wp_insert_post(['post_title'=>'After migration retry','post_status'=>'publish','post_content'=>'protected again']);")
 assert int(wp(web,'eval',"echo count((new OzekiResilience\\M1\\Plugin())->store()->history());"))>n
 print('PASS actual bootstrap failure: public/login/admin available, en/ja retry, writes blocked without content loss, retry resumes protection',flush=True)
 return {'actual_wp_load_failure_contained':True,'lock_contention_contained':True,'public_http_200':True,'admin_login_and_retry_page':True,'ja_en_notice':True,'post_ajax_rest_comments_cf7_http_503':True,'rest_method_override_blocked':True,'cli_post_write_blocked':True,'content_settings_queue_unchanged':True,'retry_resumes_confirmed_saving':True}
