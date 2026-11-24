<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'taxonomy/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}
function ids(){return json_decode(file_get_contents('/lab/ids.json'),true);}
function result($r){out(['ok'=>!is_wp_error($r)&&$r!==false,'error'=>is_wp_error($r)?$r->get_error_message():null]);}
if($mode==='prepare'){
 cfg(false);$a=wp_insert_term('Grandparent A','category',['slug'=>'grandparent-a']);$b=wp_insert_term('Grandparent B','category',['slug'=>'grandparent-b']);$p=wp_insert_term('Parent before','category',['slug'=>'parent','parent'=>$a['term_id']]);$c=wp_insert_term('Child','category',['slug'=>'child','parent'=>$p['term_id']]);$t=wp_insert_term('Tag before','post_tag',['slug'=>'tag-before','description'=>'Description before']);
 $post=wp_insert_post(['post_title'=>'Synthetic hierarchy','post_content'=>'Unchanged explanation','post_status'=>'publish','post_category'=>[$c['term_id']]]);wp_set_post_tags($post,[$t['term_id']]);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$post,'a'=>$a['term_id'],'b'=>$b['term_id'],'parent'=>$p['term_id'],'child'=>$c['term_id'],'tag'=>$t['term_id']]));
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=ids();
if($mode==='tag-name'){result(wp_update_term($i['tag'],'post_tag',['name'=>'Tag renamed']));exit;}
if($mode==='tag-slug'){result(wp_update_term($i['tag'],'post_tag',['slug'=>'tag-renamed']));exit;}
if($mode==='tag-description'){result(wp_update_term($i['tag'],'post_tag',['description'=>'Description changed']));exit;}
if($mode==='ancestor-name'){result(wp_update_term($i['parent'],'category',['name'=>'Parent renamed']));exit;}
if($mode==='ancestor-parent'){result(wp_update_term($i['parent'],'category',['parent'=>$i['b']]));exit;}
if($mode==='delete-tag'){result(wp_delete_term($i['tag'],'post_tag'));exit;}
if($mode==='delete-child'){result(wp_delete_term($i['child'],'category'));exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);
 try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 $terms=[];foreach(get_terms(['taxonomy'=>['category','post_tag'],'hide_empty'=>false,'orderby'=>'term_id','order'=>'ASC'])as $t)$terms[]=['id'=>$t->term_id,'taxonomy'=>$t->taxonomy,'name'=>$t->name,'slug'=>$t->slug,'description'=>$t->description,'parent'=>$t->parent,'count'=>$t->count];
 $assigned=[];foreach(['category','post_tag']as $tax)$assigned[$tax]=wp_get_object_terms($i['post'],$tax,['fields'=>'ids','orderby'=>'term_id']);
 out(['content'=>get_post_field('post_content',$i['post']),'terms'=>$terms,'assigned'=>$assigned,'history_count'=>count((new Plugin())->store()->history()),'pending'=>(bool)get_option('ozeki_resilience_m1_pending'),'queue'=>count((array)get_option(CommentHistory::PENDING,[]))]);exit;
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

