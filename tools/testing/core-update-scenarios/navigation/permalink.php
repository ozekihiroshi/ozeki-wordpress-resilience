<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'permalink/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);update_option('permalink_structure','/%year%/%monthnum%/%postname%/');
 $p=wp_insert_post(['post_title'=>'Control article','post_name'=>'fixture-article','post_content'=>'Original control body','post_status'=>'publish','post_date'=>'2026-11-20 12:00:00']);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$p]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='change'){out(['ok'=>update_option('permalink_structure','/articles/%postname%/')]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['post'],'post_content'=>'Edited control body'])]);exit;}
if($mode==='refresh-baseline'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 update_option('permalink_structure','/library/%postname%/');
 out(['ok'=>true]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
if($mode==='state'){
 wp_set_current_user(0);$url=get_permalink($i['post']);
 out(['display'=>['permalink_structure'=>get_option('permalink_structure'),'article_path'=>wp_parse_url($url,PHP_URL_PATH),'article_body'=>get_post($i['post'])->post_content],'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
