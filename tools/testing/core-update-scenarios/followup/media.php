<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,CommentHistory,AttachmentHistory};
if(!str_starts_with(home_url(),'http://owr-hypothesis-'))throw new RuntimeException('Isolation required');
wp_set_current_user(1);$mode=$argv[1];
function cfg($protect=true,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','owner'=>'','prefix'=>'media/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
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

if($mode==='prepare'){
 cfg(false);$p=wp_insert_post(['post_title'=>'Media deletion fixture','post_content'=>'Synthetic article','post_status'=>'publish']);
 $u=wp_upload_dir();wp_mkdir_p($u['basedir']);$f=$u['basedir'].'/fixture.png';file_put_contents($f,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='));
 $a=wp_insert_attachment(['post_title'=>'Synthetic image','post_excerpt'=>'Original caption','post_status'=>'inherit','post_mime_type'=>'image/png'],$f,$p);wp_update_attachment_metadata($a,['width'=>1,'height'=>1,'file'=>'fixture.png','sizes'=>[]]);update_post_meta($a,'_wp_attachment_image_alt','Original alternative');set_post_thumbnail($p,$a);
 wp_update_post(['ID'=>$p,'post_content'=>'Synthetic article <img class="wp-image-'.$a.'" src="'.esc_url(wp_get_attachment_url($a)).'" alt="Inline alternative">']);
 $c=wp_insert_comment(['comment_post_ID'=>$a,'comment_author'=>'Synthetic visitor','comment_content'=>'Image comment','comment_approved'=>1]);
 file_put_contents('/lab/ids.json',json_encode(['post'=>$p,'attachment'=>$a,'comment'=>$c]));$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/ref.json',json_encode($r));cfg();out(['prepared'=>true]);exit;
}
$i=json_decode(file_get_contents('/lab/ids.json'),true);
if($mode==='metadata'){wp_update_post(['ID'=>$i['attachment'],'post_excerpt'=>'Updated caption']);update_post_meta($i['attachment'],'_wp_attachment_image_alt','Updated alternative');out(['ok'=>true]);exit;}
if($mode==='delete'){out(['ok'=>(bool)wp_delete_attachment($i['attachment'],true)]);exit;}
if($mode==='save'){out(['ok'=>(bool)wp_update_post(['ID'=>$i['post'],'post_title'=>'Media deletion fixture updated'])]);exit;}
if($mode==='restore'){
 cfg(false,'recovery');$r=json_decode(file_get_contents('/lab/ref.json'),true);try{$x=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');out(['success'=>true,'through'=>$x['through']]);}catch(Throwable $e){out(['success'=>false,'error'=>$e->getMessage()]);}exit;
}
if($mode==='state'){
 global $wpdb;$a=get_post($i['attachment']);$p=get_post($i['post']);$u=wp_upload_dir();
 out(['attachment'=>$a?['id'=>$a->ID,'caption'=>$a->post_excerpt,'alt'=>get_post_meta($a->ID,'_wp_attachment_image_alt',true)]:null,'file_exists'=>is_file($u['basedir'].'/fixture.png'),'thumbnail'=>(int)get_post_thumbnail_id($i['post']),'comments'=>$wpdb->get_results($wpdb->prepare("SELECT comment_ID,comment_post_ID,comment_content FROM {$wpdb->comments} WHERE comment_post_ID=%d ORDER BY comment_ID",$i['attachment']),ARRAY_A),'post_title'=>$p?$p->post_title:null,'history_count'=>count((new Plugin())->store()->history()),'pending'=>count((array)get_option(CommentHistory::PENDING,[])),'attachment_pending'=>get_option(AttachmentHistory::PENDING,[]),'errors'=>get_option(AttachmentHistory::ERRORS,[])]);exit;
}
throw new RuntimeException('Unknown mode');
