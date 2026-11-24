<?php
$_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{MediaAccess,Plugin,SetupReadiness,SiteSnapshot};
if(!str_contains(home_url(),'isolated-review'))throw new RuntimeException('Not isolated');
wp_set_current_user(1);$prefix='media-'.bin2hex(random_bytes(6)).'/';
$c=['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>$prefix,'protect'=>false,'setup_role'=>'source','setup_version'=>1,'terms_version'=>SetupReadiness::TERMS,'gfs'=>[],'cleanup_enabled'=>false];update_option('ozeki_resilience_m1_config',$c,false);
$ids=[];$png=base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=');
for($i=0;$i<20;$i++){$file=wp_upload_dir()['path'].'/review-'.bin2hex(random_bytes(5)).'.png';file_put_contents($file,$png);$id=wp_insert_attachment(['post_title'=>'Image '.$i,'post_mime_type'=>'image/png','post_status'=>'inherit'],$file);update_attached_file($id,$file);$ids[]=$id;}
(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);$c['protect']=true;update_option('ozeki_resilience_m1_config',$c,false);MediaAccess::record();
file_put_contents('/lab/setup-commands.log','');MediaAccess::record();$noop=file_get_contents('/lab/setup-commands.log');
if($noop!=='')throw new RuntimeException('No-op media capture sent SDK requests');
update_post_meta($ids[0],'_review_private','yes');MediaAccess::record();
$rules=MediaAccess::current();$path='uploads/'.get_post_meta($ids[0],'_wp_attached_file',true);
if(($rules[$path]['state']??'')!=='held'||get_option('ozeki_resilience_attachment_pending')||get_option('ozeki_resilience_m1_comment_pending'))throw new RuntimeException('Access change not preserved');
$count=substr_count(file_get_contents('/lab/setup-commands.log'),'PutObject');
file_put_contents('/lab/control.json',json_encode(['fail'=>'history']));update_post_meta($ids[1],'_review_private','yes');MediaAccess::record();
if(!get_option('ozeki_resilience_m1_comment_pending'))throw new RuntimeException('Interrupted history disappeared');
file_put_contents('/lab/control.json','{}');(new OzekiResilience\M1\CommentHistory())->resume();MediaAccess::record();
if(get_option('ozeki_resilience_m1_comment_pending'))throw new RuntimeException('History retry did not finish');
echo json_encode(['new_fixture_attachments'=>20,'total_attachments'=>count(get_posts(['post_type'=>'attachment','post_status'=>'any','numberposts'=>-1,'fields'=>'ids'])),'no_op_sdk_requests'=>0,'one_access_change_preserved'=>true,'change_put_requests'=>$count,'history_failure_retry'=>true]).PHP_EOL;
$c['protect']=false;update_option('ozeki_resilience_m1_config',$c,false);
