<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'sticky/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);$a=wp_insert_post(['post_title'=>'Older fixture','post_content'=>'Older article','post_status'=>'publish','post_date'=>'2026-01-01 12:00:00','post_date_gmt'=>'2026-01-01 12:00:00']);
 $b=wp_insert_post(['post_title'=>'Newer fixture','post_content'=>'Newer article','post_status'=>'publish','post_date'=>'2026-02-01 12:00:00','post_date_gmt'=>'2026-02-01 12:00:00']);stick_post($a);
 file_put_contents('/lab/ids.json',json_encode(['older'=>$a,'newer'=>$b]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='unstick'){unstick_post($i['older']);out(['ok'=>!is_sticky($i['older'])]);exit;}
if($mode==='stick'){stick_post($i['newer']);out(['ok'=>is_sticky($i['newer'])]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['newer'],'post_content'=>'Edited newer article'])]);exit;}
if($mode==='refresh-baseline'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 unstick_post($i['newer']);stick_post($i['older']);
 out(['ok'=>true]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
if($mode==='state'){
 wp_set_current_user(0);$q=new WP_Query(['posts_per_page'=>100]);$order=[];foreach($q->posts as $p)if(in_array((int)$p->ID,$i,true))$order[]=(int)$p->ID;
 out(['display'=>['sticky_ids'=>array_values(array_map('intval',(array)get_option('sticky_posts',[]))),'older_sticky'=>is_sticky($i['older']),'newer_sticky'=>is_sticky($i['newer']),'home_order'=>$order,'newer_body'=>get_post($i['newer'])->post_content],'query_is_home'=>$q->is_home(),'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
