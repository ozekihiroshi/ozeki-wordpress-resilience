<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,CoreStateHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'refs/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
if($mode==='prepare'){
 cfg(false);$ids=[];
 foreach(['a','b'] as $n){$c=wp_insert_term('Category '.$n,'category',['slug'=>'category-'.$n]);$ids['category_'.$n]=$c['term_id'];$ids['page_'.$n]=wp_insert_post(['post_type'=>'page','post_title'=>'Privacy '.$n,'post_name'=>'privacy-'.$n,'post_content'=>'Privacy fixture '.$n,'post_status'=>'publish']);}
 $ids['post']=wp_insert_post(['post_title'=>'Control article','post_content'=>'Original body','post_status'=>'publish']);
 update_option('default_category',$ids['category_a']);update_option('wp_page_for_privacy_policy',$ids['page_a']);
 file_put_contents('/lab/ids.json',json_encode($ids));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='change'){update_option('default_category',$i['category_b']);update_option('wp_page_for_privacy_policy',$i['page_b']);out(['ok'=>true]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['post'],'post_content'=>'Edited body'])]);exit;}
if($mode==='refresh-baseline'){$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));out(['ok'=>true]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='unset'){update_option('default_category',0);update_option('wp_page_for_privacy_policy',0);out(['ok'=>true]);exit;}
if($mode==='new-target'){
 $c=wp_insert_term('Category c','category',['slug'=>'category-c']);$i['category_c']=$c['term_id'];$i['page_c']=wp_insert_post(['post_type'=>'page','post_title'=>'Privacy c','post_content'=>'New privacy fixture','post_status'=>'publish']);file_put_contents('/lab/ids.json',json_encode($i));
 update_option('default_category',$i['category_c']);update_option('wp_page_for_privacy_policy',$i['page_c']);out(['ok'=>true]);exit;
}
if($mode==='protected-delete'){$r=wp_delete_term($i['category_c'],'category');out(['ok'=>$r===0&&(bool)term_exists($i['category_c'],'category'),'wordpress_result'=>$r]);exit;}
if($mode==='delete-target'){
 update_option('default_category',$i['category_a']);$r=wp_delete_term($i['category_c'],'category');$p=wp_delete_post($i['page_c'],true);out(['ok'=>$r===true&&(bool)$p]);exit;
}
if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));$c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 update_option('default_category',$i['category_b']);update_option('wp_page_for_privacy_policy',$i['page_b']);$i['cycle_post']=wp_insert_post(['post_title'=>'Post after recovery','post_content'=>'Default category check','post_status'=>'publish']);file_put_contents('/lab/ids.json',json_encode($i));out(['ok'=>(bool)$i['cycle_post']]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}
if($mode==='state'){
 wp_set_current_user(0);$category=get_term((int)get_option('default_category'),'category');$url=get_privacy_policy_url();
 out(['display'=>['category_id'=>(int)get_option('default_category'),'category_name'=>is_wp_error($category)||!$category?null:$category->name,'privacy_id'=>(int)get_option('wp_page_for_privacy_policy'),'privacy_url'=>str_replace(home_url(),'SITE',$url),'privacy_title'=>get_the_title((int)get_option('wp_page_for_privacy_policy')),'deleted_category_exists'=>isset($i['category_c'])?(bool)term_exists($i['category_c'],'category'):false,'deleted_page_exists'=>isset($i['page_c'])?(bool)get_post($i['page_c']):false,'new_post_categories'=>isset($i['cycle_post'])?array_map('intval',wp_get_post_categories($i['cycle_post'])):[],'both_pages_present'=>(bool)(get_post($i['page_a'])&&get_post($i['page_b'])),'article_body'=>get_post($i['post'])->post_content],'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'core_pending'=>(bool)get_option(CoreStateHistory::PENDING),'error'=>get_option('ozeki_resilience_m1_capture_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
