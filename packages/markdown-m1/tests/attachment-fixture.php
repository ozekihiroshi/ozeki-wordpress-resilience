<?php
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,MediaAccess,AttachmentHistory};
if(!str_starts_with(home_url(),'http://owr-coexist-'))throw new RuntimeException('Isolated site required');
wp_set_current_user(1);$mode=$argv[1];
function cfgA($prefix,$protect=false,$role='source'){update_option('ozeki_resilience_m1_config',['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>$prefix.'/','protect'=>$protect,'setup_role'=>$role,'gfs'=>[],'cleanup_enabled'=>false],false);}
function outA($v){echo wp_json_encode($v,JSON_THROW_ON_ERROR);}
function stateA(){global $wpdb;$rows=$wpdb->get_results("SELECT ID,post_title,post_mime_type FROM {$wpdb->posts} WHERE post_type='attachment' ORDER BY ID",ARRAY_A);$rules=MediaAccess::current();$files=[];foreach($rules as $p=>$r){$f=wp_upload_dir()['basedir'].'/'.substr($p,8);$bytes=MediaAccess::heldBody($p);$files[$p]=['state'=>$r['state'],'public'=>is_file($f),'hash'=>is_file($f)?hash_file('sha256',$f):($bytes===null?null:hash('sha256',$bytes))];}return ['attachments'=>$rows,'files'=>$files,'pending'=>(bool)get_option('ozeki_resilience_attachment_pending'),'queue'=>(bool)get_option('ozeki_resilience_m1_comment_pending'),'errors'=>get_option('ozeki_resilience_attachment_errors',[])];}
if($mode==='baseline'){cfgA($argv[2]);$r=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);file_put_contents('/lab/'.$argv[2].'-ref.json',wp_json_encode($r));outA($r);exit;}
if($mode==='restore'||$mode==='reject'){
 cfgA($argv[2],false,'recovery');$r=json_decode(file_get_contents('/lab/'.$argv[2].'-ref.json'),true);$before=stateA();
 try{$r=(new SiteSnapshot((new Plugin())->store()))->restore($r['manifest'],true,'/tmp/recovery-work');if($mode==='reject')throw new LogicException('Old reader accepted new data');outA(['restored'=>true,'through'=>$r['through'],'missing'=>count($r['application_report']['missing_originals']??[])]);}
 catch(RuntimeException $e){if($mode!=='reject')throw $e;outA(['rejected'=>true,'reason'=>$e->getMessage(),'unchanged'=>$before===stateA()]);}exit;
}
if($mode==='add'){
 cfgA($argv[2],true);require_once ABSPATH.'wp-admin/includes/file.php';require_once ABSPATH.'wp-admin/includes/image.php';
 foreach(['public','held'] as $kind){
  $tmp=tempnam('/tmp','pdf');copy('/lab/manual.pdf',$tmp);$file=['name'=>$kind.'-manual.pdf','tmp_name'=>$tmp,'error'=>0,'size'=>filesize($tmp)];$upload=wp_handle_sideload($file,['test_form'=>false]);
  if(isset($upload['error']))throw new RuntimeException($upload['error']);
  $id=wp_insert_attachment(['post_title'=>$kind.' manual','post_status'=>'inherit','post_mime_type'=>'application/pdf'],$upload['file']);
  $meta=wp_generate_attachment_metadata($id,$upload['file']);wp_update_attachment_metadata($id,$meta);
  if($kind==='held')update_post_meta($id,'_test_private_condition','yes');
 }
 outA(['added'=>true]);exit;
}
if($mode==='state'){outA(stateA());exit;}
if($mode==='touch'){cfgA($argv[2],true);global $wpdb;$id=(int)$wpdb->get_var("SELECT ID FROM {$wpdb->posts} WHERE post_type='attachment' ORDER BY ID LIMIT 1");wp_update_post(['ID'=>$id,'post_title'=>'Retry confirmation']);outA(['touched'=>true]);exit;}
if($mode==='resume'){cfgA($argv[2],true);(new OzekiResilience\M1\CommentHistory())->resume();outA(['resumed'=>true]);exit;}
if($mode==='index'){
 cfgA($argv[2]);$r=(new Plugin())->store()->createCheckpoint();file_put_contents('/lab/index-ref.json',wp_json_encode($r));outA(['saved'=>true]);exit;
}
if($mode==='reject-index'){
 cfgA($argv[2],false,'recovery');$r=json_decode(file_get_contents('/lab/index-ref.json'),true);
 try{(new Plugin())->store()->snapshot($r['key']);outA(['rejected'=>false]);}catch(RuntimeException $e){outA(['rejected'=>true,'reason'=>$e->getMessage()]);}exit;
}
if($mode==='resave'){
 cfgA($argv[2],true);global $wpdb;$id=(int)$wpdb->get_var("SELECT ID FROM {$wpdb->posts} WHERE post_type='attachment' ORDER BY ID LIMIT 1");wp_update_post(['ID'=>$id,'post_title'=>'Resaved manual']);
 $article=wp_insert_post(['post_type'=>'post','post_status'=>'publish','post_title'=>'PDF block usage','post_content'=>'<!-- wp:file {"id":'.$id.'} --><a href="'.wp_get_attachment_url($id).'">Manual</a><!-- /wp:file -->'],true);if(is_wp_error($article))throw new RuntimeException('PDF article save failed');outA(['resaved'=>true,'article'=>$article]);exit;
}
if($mode==='missing'){
 cfgA($argv[2],true);$u=wp_upload_dir();$f=$u['basedir'].'/missing.pdf';file_put_contents($f,file_get_contents('/lab/manual.pdf'));$id=wp_insert_attachment(['post_title'=>'Missing original','post_status'=>'inherit','post_mime_type'=>'application/pdf'],$f);wp_update_attachment_metadata($id,[]);unlink($f);file_put_contents('/lab/missing-id',strval($id));outA(['missing'=>true]);exit;
}
if($mode==='reject-incomplete'){
 try{(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);outA(['rejected'=>false]);}catch(RuntimeException $e){outA(['rejected'=>true,'reason'=>$e->getMessage()]);}exit;
}
if($mode==='repair'){
 cfgA($argv[2],true);$id=(int)file_get_contents('/lab/missing-id');$f=get_attached_file($id);file_put_contents($f,file_get_contents('/lab/manual.pdf'));outA(['repaired'=>true]);exit;
}
throw new RuntimeException('Unknown test operation');
