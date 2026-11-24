<?php
namespace OzekiResilience\M1 {
 class Plugin {function store(){return null;}function mediaForBody($s,$store,$base,&$resources){$resources=[];return [];}}
 class CommentHistory {function enqueue($asset,$source,$attrs,$resources){$GLOBALS['captured']=compact('asset','source','attrs');}}
 class ReferenceContext {static function capture(){return [];}}
}
namespace {
 define('ABSPATH',__DIR__.'/');require __DIR__.'/../src/UpdateContract.php';require __DIR__.'/../src/CoreStateHistory.php';
 $post=(object)['ID'=>10,'post_type'=>'post','post_content'=>'Published by core','post_title'=>'Title','post_name'=>'title','post_status'=>'publish','post_date'=>'2026-11-24 00:00:00','post_date_gmt'=>'2026-11-24 00:00:00','post_excerpt'=>'','post_parent'=>'0','menu_order'=>'0','comment_status'=>'closed','ping_status'=>'closed','post_password'=>'','post_author'=>'0'];
 $identity='known';$persist=true;
 function get_post($id){return $GLOBALS['post'];}
 function get_post_meta($id,$key,$single){return $GLOBALS['identity'];}
 function update_post_meta($id,$key,$value){if($GLOBALS['persist'])$GLOBALS['identity']=$value;}
 function wp_generate_uuid4(){return 'synthetic-id';}
 function get_permalink($id){return 'https://fixture.invalid/?p='.$id;}
 function get_userdata($id){return false;}
 $method=new ReflectionMethod(OzekiResilience\M1\CoreStateHistory::class,'captureScheduled');$method->setAccessible(true);$method->invoke(null,10);
 if($captured['source']!==$post->post_content||$captured['attrs']['status']!=='publish')throw new RuntimeException('Scheduled operation not captured');
 foreach(['invalid-source','identity-write-failure'] as $case){$post->post_content=$case==='invalid-source'?"bad\0text":'Valid';$identity='';$persist=false;$rejected=false;try{$method->invoke(null,10);}catch(RuntimeException $e){$rejected=true;}if(!$rejected)throw new RuntimeException('Invalid scheduled capture accepted');}
 echo "PASS scheduled capture without editor identity, invalid source and identity persistence failure\n";
}
