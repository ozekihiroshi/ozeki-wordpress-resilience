<?php
if (($argv[1]??'')==='setup') define('WP_INSTALLING',true);
require '/var/www/html/wp-load.php';
$mode=$argv[1];
if($mode==='setup'){
 require_once ABSPATH.'wp-admin/includes/upgrade.php';wp_install('Protected save lab','labadmin','lab@example.invalid',false,'',getenv('LAB_ADMIN_PASSWORD'));
 update_option('home','http://127.0.0.1');update_option('siteurl','http://127.0.0.1');
 $ids=[];foreach(['company','services','contact']as$role)$ids[$role]=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>ucfirst($role),'post_name'=>$role,'post_content'=>'<p>Before '.$role.'</p>']);
 $unrelated=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>'Unrelated','post_name'=>'unrelated','post_content'=>'<p>Unrelated</p>']);
 $editor=wp_create_user('labsubscriber','Test-only-pass123!','subscriber@example.invalid');(new WP_User($editor))->set_role('subscriber');
 $job=json_decode(file_get_contents('/lab/assets/job.json'),true);$image=$job['assets'][3];$up=wp_upload_dir();copy($image['path'],$up['path'].'/logo.png');
 $config=['ids'=>$ids,'unrelated'=>$unrelated,'seed'=>$job['assets'],'images'=>['logo'=>['path'=>$up['path'].'/logo.png','url'=>$up['url'].'/logo.png']]];
 global $wpdb;$wpdb->query("CREATE TABLE {$wpdb->posts}_owr_projection (id INT PRIMARY KEY,state LONGTEXT NOT NULL) ENGINE=InnoDB");$wpdb->query("INSERT INTO {$wpdb->posts}_owr_projection VALUES(1,'{}')");
 file_put_contents('/lab/config.json',json_encode($config));echo 'setup';exit;
}
if($mode==='enroll'){owr_test_factory()->enroll();echo 'enrolled';exit;}
if($mode==='snapshot'){
 global $wpdb;$c=json_decode(file_get_contents('/lab/config.json'),true);
 echo json_encode(['pages'=>$wpdb->get_results('SELECT * FROM '.$wpdb->posts.' WHERE ID IN ('.implode(',',$c['ids']).') ORDER BY ID',ARRAY_A), 'state'=>json_decode($wpdb->get_var("SELECT state FROM {$wpdb->posts}_owr_projection WHERE id=1"),true)]);exit;
}
if($mode==='dispatch'){
 wp_set_current_user((int)get_user_by('login','labadmin')->ID);
 $r=new WP_REST_Request('POST','/owr-rbr/v1/save');$r->set_header('Content-Type','application/json');$r->set_body(file_get_contents($argv[2]));$out=rest_do_request($r);echo json_encode(['status'=>$out->get_status(),'data'=>$out->get_data()]);exit;
}
if($mode==='credentials'){
 $u=get_user_by('login',$argv[2]);wp_set_current_user($u->ID);$expiry=time()+3600;$token=WP_Session_Tokens::get_instance($u->ID)->create($expiry);$cookie=wp_generate_auth_cookie($u->ID,$expiry,'logged_in',$token);$_COOKIE[LOGGED_IN_COOKIE]=$cookie;
 echo json_encode(['cookie'=>LOGGED_IN_COOKIE.'='.$cookie,'nonce'=>wp_create_nonce('wp_rest')]);exit;
}
if($mode==='http'){
 $a=json_decode(file_get_contents($argv[2]),true);$ch=curl_init('http://127.0.0.1'.$a['path']);curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_CUSTOMREQUEST=>$a['method'],CURLOPT_TIMEOUT=>30,CURLOPT_HTTPHEADER=>$a['headers']??[],CURLOPT_POSTFIELDS=>$a['body']??null]);$body=curl_exec($ch);echo json_encode(['status'=>curl_getinfo($ch,CURLINFO_HTTP_CODE),'body'=>$body]);exit;
}

