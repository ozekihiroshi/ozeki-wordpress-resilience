<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'menu/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
function item($menu,$id,$title,$url,$order){return wp_update_nav_menu_item($menu,$id,['menu-item-title'=>$title,'menu-item-url'=>$url,'menu-item-type'=>'custom','menu-item-status'=>'publish','menu-item-position'=>$order]);}
if($mode==='prepare'){
 cfg(false);$p=wp_insert_post(['post_title'=>'Control article','post_content'=>'Original control body','post_status'=>'publish']);$menu=wp_create_nav_menu('Synthetic navigation');if(is_wp_error($menu))throw new RuntimeException($menu->get_error_message());
 $a=item($menu,0,'Original A','https://example.invalid/old',1);$b=item($menu,0,'Original B','https://example.invalid/b',2);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$p,'menu'=>$menu,'a'=>$a,'b'=>$b]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='edit-reorder'){$a=item($i['menu'],$i['a'],'Updated A','https://example.invalid/new',2);$b=item($i['menu'],$i['b'],'Original B','https://example.invalid/b',1);out(['ok'=>!is_wp_error($a)&&!is_wp_error($b)]);exit;}
if($mode==='add'){$c=item($i['menu'],0,'Added C','https://example.invalid/c',3);out(['ok'=>!is_wp_error($c)]);exit;}
if($mode==='delete'){out(['ok'=>(bool)wp_delete_post($i['b'],true)]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['post'],'post_content'=>'Edited control body'])]);exit;}
if($mode==='refresh-baseline'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 item($i['menu'],$i['a'],'Cycle label','https://example.invalid/cycle',1);
 out(['ok'=>true]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
if($mode==='delete-menu'){$r=wp_delete_nav_menu($i['menu']);out(['ok'=>!is_wp_error($r)&&$r!==false]);exit;}
if($mode==='state'){
 wp_set_current_user(0);$items=[];foreach(wp_get_nav_menu_items($i['menu'])?:[] as $p)$items[]=['id'=>(int)$p->ID,'title'=>$p->title,'url'=>$p->url,'order'=>(int)$p->menu_order];
 $html=wp_nav_menu(['menu'=>$i['menu'],'echo'=>false,'fallback_cb'=>false]);$text=trim(preg_replace('/\s+/u',' ',wp_strip_all_tags((string)$html)));
 out(['display'=>['items'=>$items,'rendered_text'=>$text,'article_body'=>get_post($i['post'])->post_content],'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
