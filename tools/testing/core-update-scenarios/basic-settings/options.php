<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
const BEFORE=['blogdescription'=>'Original description','category_base'=>'category','tag_base'=>'tag','date_format'=>'Y-m-d','time_format'=>'H:i','start_of_week'=>1,'posts_per_rss'=>10,'default_comment_status'=>'open','default_ping_status'=>'open'];
const AFTER=['blogdescription'=>'Changed description','category_base'=>'topics','tag_base'=>'labels','date_format'=>'d/m/Y','time_format'=>'g:i a','start_of_week'=>0,'posts_per_rss'=>5,'default_comment_status'=>'closed','default_ping_status'=>'closed'];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'options/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);foreach(BEFORE as $k=>$v)update_option($k,$v);update_option('permalink_structure','/%postname%/');
 $p=wp_insert_post(['post_title'=>'Control article','post_name'=>'fixture-article','post_content'=>'Original control body','post_status'=>'publish','post_date'=>'2026-11-20 15:04:00']);
 $c=wp_insert_term('Fixture category','category',['slug'=>'fixture-category']);$t=wp_insert_term('Fixture tag','post_tag',['slug'=>'fixture-tag']);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$p,'category'=>$c['term_id'],'tag'=>$t['term_id']]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='change'){foreach(AFTER as $k=>$v)update_option($k,$v);out(['ok'=>true]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['post'],'post_content'=>'Edited control body'])]);exit;}
if($mode==='refresh-baseline'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 foreach(BEFORE as $k=>$v)update_option($k,$v);out(['ok'=>true]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
if($mode==='state'){
 wp_set_current_user(0);$values=[];foreach(BEFORE as $k=>$v)$values[$k]=(string)get_option($k);
 out(['display'=>['options'=>$values,'description'=>get_bloginfo('description'),'date'=>get_the_date('', $i['post']),'time'=>get_the_time('', $i['post']),'category_path'=>wp_parse_url(get_category_link($i['category']),PHP_URL_PATH),'tag_path'=>wp_parse_url(get_tag_link($i['tag']),PHP_URL_PATH),'article_body'=>get_post($i['post'])->post_content],'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
