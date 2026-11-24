<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'properties/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);$a=wp_insert_user(['user_login'=>'fixture-author-a','user_pass'=>wp_generate_password(),'user_email'=>'a@example.invalid','display_name'=>'Fixture Author A','role'=>'author']);$b=wp_insert_user(['user_login'=>'fixture-author-b','user_pass'=>wp_generate_password(),'user_email'=>'b@example.invalid','display_name'=>'Fixture Author B','role'=>'author']);
 $parent=wp_insert_post(['post_type'=>'page','post_title'=>'Prepared parent','post_content'=>'Parent fixture','post_status'=>'publish','post_author'=>$b]);
 $p=wp_insert_post(['post_type'=>'page','post_title'=>'Property fixture','post_content'=>'Unchanged body','post_status'=>'publish','post_author'=>$a,'post_excerpt'=>'Original excerpt','comment_status'=>'open','ping_status'=>'open']);
 file_put_contents('/lab/ids.json',json_encode(['page'=>$p,'parent'=>$parent,'author_b'=>$b]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
$changes=['author'=>['post_author'=>$i['author_b']],'excerpt'=>['post_excerpt'=>'Changed excerpt'],'discussion'=>['comment_status'=>'closed','ping_status'=>'closed'],'parent'=>['post_parent'=>$i['parent']],'order'=>['menu_order'=>17]];
if(isset($changes[$mode])){$r=wp_update_post(['ID'=>$i['page']]+$changes[$mode],true);out(['ok'=>!is_wp_error($r)&&$r>0,'error'=>is_wp_error($r)?$r->get_error_message():null]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 $p=get_post($i['page']);$u=get_userdata($p->post_author);$v=[];foreach(['post_title','post_content','post_excerpt','comment_status','ping_status','post_parent','menu_order','post_status']as $k)$v[$k]=$p->$k;
 $v['author_display_name']=$u?$u->display_name:null;$v['author_nicename']=$u?$u->user_nicename:null;
 out(['properties'=>$v,'actual_author_id'=>$p->post_author,'history_count'=>count((new Plugin())->store()->history()),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'queue'=>count((array)get_option(CommentHistory::PENDING,[]))]);exit;
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

