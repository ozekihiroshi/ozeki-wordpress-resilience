<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'comments/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function out($v){echo json_encode($v,JSON_THROW_ON_ERROR);}

if($mode==='cycle-save'){
 cfg(false);$c=(new Plugin())->config();$c['prefix']='cycle/';$c['setup_role']='source';update_option('ozeki_resilience_m1_config',$c,false);
 $r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/cycle-ref.json',json_encode($r));
 $c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);
 $ids=json_decode(file_get_contents('/lab/ids.json'),true);$id=$ids['protected']??$ids['page']??$ids['post'];$p=get_post($id);
 $body=preg_replace('~http://owr-hypothesis-[^/]+/wp-content/uploads/~',wp_upload_dir()['baseurl'].'/',$p->post_content);
 $r=wp_update_post(['ID'=>$id,'post_content'=>$body."\nCycle edit"],true);out(['success'=>!is_wp_error($r)&&$r!==0]);exit;
}
if($mode==='cycle-restore'){
 cfg(false,'recovery');$c=(new Plugin())->config();$c['prefix']='cycle/';update_option('ozeki_resilience_m1_config',$c,false);
 $r=json_decode(file_get_contents('/lab/cycle-ref.json'),true);$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);exit;
}

if(in_array($mode,['prepare','prepare-stale'],true)){
 cfg(false);$p=wp_insert_post(['post_type'=>'post','post_title'=>'Comment lifecycle fixture','post_content'=>'Synthetic public article','post_status'=>'publish','comment_status'=>'open']);
 $c=wp_insert_comment(['comment_post_ID'=>$p,'comment_content'=>'Approved parent','comment_author'=>'Synthetic author','comment_approved'=>1]);
 $r=wp_insert_comment(['comment_post_ID'=>$p,'comment_content'=>'Approved reply','comment_author'=>'Synthetic reply','comment_approved'=>1,'comment_parent'=>$c]);
 if($mode==='prepare-stale')wp_trash_comment($c);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$p,'comment'=>$c,'reply'=>$r]));$ref=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($ref));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='hold'){out(['ok'=>(bool)wp_set_comment_status($i['comment'],'hold')]);exit;}
if(in_array($mode,['trash','untrash','spam','unspam','delete'],true)){
 $f=['trash'=>'wp_trash_comment','untrash'=>'wp_untrash_comment','spam'=>'wp_spam_comment','unspam'=>'wp_unspam_comment','delete'=>'wp_delete_comment'][$mode];$r=$mode==='delete'?$f($i['comment'],true):$f($i['comment']);out(['ok'=>(bool)$r]);exit;
}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='resume'){(new CommentHistory())->resume();\OzekiResilience\M1\CoreStateHistory::flush();out(['success'=>true]);exit;}
if($mode==='state'){
 global $wpdb;$rows=$wpdb->get_results($wpdb->prepare("SELECT comment_ID,comment_content,comment_approved,comment_parent FROM {$wpdb->comments} WHERE comment_post_ID=%d ORDER BY comment_ID",$i['post']),ARRAY_A);
 $meta=get_comment_meta($i['comment']);$meta=array_intersect_key($meta,array_flip(['_wp_trash_meta_status','_wp_trash_meta_time','_wp_trash_meta_comments_status']));
 out(['comments'=>$rows,'transition_meta'=>$meta,'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'error'=>get_option('ozeki_resilience_m1_comment_error',false)]);exit;
}
throw new RuntimeException('Unknown mode');
