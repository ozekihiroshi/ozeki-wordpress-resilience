<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'site-options/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);$a=wp_insert_post(['post_type'=>'page','post_title'=>'Front A','post_content'=>'Initial front page','post_status'=>'publish']);$b=wp_insert_post(['post_type'=>'page','post_title'=>'Front B','post_content'=>'Replacement front page','post_status'=>'publish']);
 update_option('show_on_front','page');update_option('page_on_front',$a);update_option('blogname','Original site title');update_option('timezone_string','UTC');update_option('posts_per_page',10);
 file_put_contents('/lab/ids.json',json_encode(['front_b'=>$b]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
$changes=['front-page'=>['page_on_front'=>$i['front_b']],'site-title'=>['blogname'=>'Changed site title'],'timezone'=>['timezone_string'=>'Asia/Tokyo'],'reading'=>['posts_per_page'=>7]];
if(isset($changes[$mode])){foreach($changes[$mode]as $key=>$value){update_option($key,$value);if((string)get_option($key)!==(string)$value)throw new RuntimeException('Fixture update failed');}out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 $v=[];foreach(['show_on_front','page_on_front','blogname','timezone_string','posts_per_page']as $key)$v[$key]=get_option($key);$v['front_title']=get_the_title((int)get_option('page_on_front'));
 out(['properties'=>$v,'history_count'=>count((new Plugin())->store()->history()),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'queue'=>count((array)get_option(CommentHistory::PENDING,[]))]);exit;
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
if($mode==='resume'){(new CommentHistory())->resume();out(['ok'=>true]);exit;}
throw new RuntimeException('Unknown mode');


