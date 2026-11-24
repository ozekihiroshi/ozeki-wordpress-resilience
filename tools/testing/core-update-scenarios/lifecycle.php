<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'lifecycle/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
function result($r){out(['ok'=>!is_wp_error($r)&&$r!==false&&$r!==null,'error'=>is_wp_error($r)?$r->get_error_message():null]);}
if($mode==='prepare'){
 cfg(false);$p=wp_insert_post(['post_type'=>'page','post_title'=>'Original parent','post_name'=>'fixture-parent','post_content'=>'Parent unchanged body','post_status'=>'publish']);$c=wp_insert_post(['post_type'=>'page','post_title'=>'Child fixture','post_name'=>'fixture-child','post_content'=>'Child unchanged body','post_status'=>'publish','post_parent'=>$p]);
 wp_insert_comment(['comment_post_ID'=>$p,'comment_author'=>'Fixture','comment_content'=>'Parent comment','comment_approved'=>1]);wp_insert_comment(['comment_post_ID'=>$c,'comment_author'=>'Fixture','comment_content'=>'Child comment','comment_approved'=>1]);
 file_put_contents('/lab/ids.json',json_encode(['parent'=>$p,'child'=>$c]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='private'){result(wp_update_post(['ID'=>$i['parent'],'post_status'=>'private'],true));exit;}
if($mode==='password'){result(wp_update_post(['ID'=>$i['parent'],'post_status'=>'publish','post_password'=>'synthetic-password'],true));exit;}
if($mode==='password-clear'){result(wp_update_post(['ID'=>$i['parent'],'post_status'=>'publish','post_password'=>''],true));exit;}
if($mode==='trash'){result(wp_trash_post($i['parent']));exit;}
if($mode==='untrash'){result(wp_untrash_post($i['parent']));exit;}
if($mode==='delete'){result(wp_delete_post($i['parent'],true));exit;}
if($mode==='recreate'){result(wp_insert_post(['post_type'=>'page','post_title'=>'New parent identity','post_name'=>'fixture-parent','post_content'=>'Replacement body','post_status'=>'publish'],true));exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 global $wpdb;$pages=$wpdb->get_results("SELECT ID,post_title,post_name,post_content,post_status,post_password,post_parent FROM {$wpdb->posts} WHERE post_type='page' ORDER BY ID",ARRAY_A);$comments=$wpdb->get_results("SELECT comment_ID,comment_post_ID,comment_content,comment_approved FROM {$wpdb->comments} ORDER BY comment_ID",ARRAY_A);
 $access=[];wp_set_current_user(0);foreach($pages as $p)$access[$p['ID']]=['public_status'=>$p['post_status']==='publish','password_required'=>post_password_required((int)$p['ID'])];
 out(['pages'=>$pages,'comments'=>$comments,'anonymous_conditions'=>$access,'history_count'=>count((new Plugin())->store()->history()),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'queue'=>count((array)get_option(CommentHistory::PENDING,[]))]);exit;
}
if($mode==='resave'){
 cfg(false);$config=(new Plugin())->config();$config['prefix'].='second/';update_option('ozeki_resilience_m1_config',$config,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/second-ref.json',json_encode($r));
 $config['protect']=true;update_option('ozeki_resilience_m1_config',$config,false);
 $id=$i['page']??$i['post']??$i['child']??$i['front_b'];
 $r=wp_update_post(['ID'=>$id,'post_content'=>get_post_field('post_content',$id).' Re-saved after recovery.'],true);
 if(is_wp_error($r))throw new RuntimeException($r->get_error_message());out(['ok'=>true]);exit;
}
if($mode==='restore-second'){
 cfg(false,'recovery');$config=(new Plugin())->config();$config['prefix'].='second/';update_option('ozeki_resilience_m1_config',$config,false);
 $r=json_decode(file_get_contents('/lab/second-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
throw new RuntimeException('Unknown mode');


