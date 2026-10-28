<?php
declare(strict_types=1);
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');

require_once $argv[1].'/src/Store.php';
require_once $argv[1].'/src/CommentHistory.php';
require_once $argv[1].'/src/SiteSnapshot.php';
class CommentMemoryS3 {
 public array $objects=[];public int $n=0;public bool $fail=false;
 function putObject($a){if($this->fail||isset($this->objects[$a['Key']]))throw new RuntimeException('denied');return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
function ok($b,$m){if(!$b)throw new RuntimeException($m);}
$s3=new CommentMemoryS3();$store=new OzekiResilience\M1\Store($s3,['bucket'=>'test','prefix'=>'comments/']);
$data=['tables'=>['posts'=>[['ID'=>'156','comment_count'=>'0']],'comments'=>[],'commentmeta'=>[]]];
$c=['comment_ID'=>'30','comment_post_ID'=>'156','comment_content'=>'テストコメント：本文と記事の関連を保持する。','comment_approved'=>'0','comment_parent'=>'0'];
$a=['post_type'=>'owr_comment','content_format'=>'comment-json','origin_id'=>30,'post_id'=>156,'title'=>'Comment test','status'=>'0'];
foreach(['0','1','spam','trash','1'] as $i=>$status){
 $c['comment_approved']=$status;$c['comment_content'].="\n編集 ".$i;$a['status']=$status;
 $raw=OzekiResilience\M1\Store::json(['schema'=>'owr-comment-1','deleted'=>false,'comment'=>$c]);
 $o=$store->prepare('comment-30','op-'.$i,$raw,$a);ok(str_ends_with($o['source']['key'],'.json'),'complete JSON source');
 $store->commit(['schema'=>'owr-md-history-1','sequence'=>$i+1,'original'=>$o,'attributes'=>$a]);
 OzekiResilience\M1\CommentHistory::replay($data,$store->originalSource($o),$a);
 ok(count($data['tables']['comments'])===1&&$data['tables']['comments'][0]===$c,'edit/moderation replay');
 ok($data['tables']['posts'][0]['comment_count']===($status==='1'?'1':'0'),'comment count');
}
$data['tables']['comments'][]=['comment_ID'=>'31','comment_post_ID'=>'156','comment_parent'=>'30','comment_approved'=>'1'];
$data['tables']['commentmeta'][]=['comment_id'=>'30','meta_key'=>'test'];
$a['status']='deleted';$raw=OzekiResilience\M1\Store::json(['schema'=>'owr-comment-1','deleted'=>true,'comment'=>$c]);
$o=$store->prepare('comment-30','delete',$raw,$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>6,'original'=>$o,'attributes'=>$a]);
OzekiResilience\M1\CommentHistory::replay($data,$raw,$a);
ok(count($data['tables']['comments'])===1&&$data['tables']['comments'][0]['comment_parent']==='0'&&!$data['tables']['commentmeta'],'delete tombstone/reparent');
$s3->fail=true;try{$store->prepare('comment-30','failed',$raw,$a);throw new LogicException('should fail');}catch(RuntimeException $e){}
ok(count($store->history())===6,'failure not formal');
$s3->fail=false;$cp=$store->createCheckpoint();$state=$store->recoveryState($cp['key']);ok($state['through']===6&&$store->originalSource($state['assets']['comment-30']['original'])===$raw,'independent asset checkpoint JSON');
echo "PASS comment addition/edit/moderation/delete/reparent/count, complete JSON, failed original exclusion, independent checkpoint.\n";

// Pending data must retain its destination when configuration is submitted.
require_once $argv[1].'/src/Plugin.php';
class CommentRedirect extends RuntimeException {}
$options=[];
function current_user_can($cap){return true;}
function check_admin_referer($action){}
function get_option($key,$default=false){return $GLOBALS['options'][$key]??$default;}
function update_option($key,$value,$autoload=false){$GLOBALS['options'][$key]=$value;return true;}
function admin_url($path){return $path;}
function wp_safe_redirect($url){throw new CommentRedirect();}
foreach(['owr_m1_pending','owr_m1_comment_pending'] as $pending){
 $options=['owr_m1_config'=>['bucket'=>'original','prefix'=>'existing/'],$pending=>['frozen'=>'payload']];
 $_POST=['operation'=>'configure','bucket'=>'different','prefix'=>'wrong/'];
 try{(new OzekiResilience\M1\Plugin())->action();}catch(CommentRedirect $e){}
 ok($options['owr_m1_config']===['bucket'=>'original','prefix'=>'existing/'],'pending destination unchanged');
 ok($options[$pending]===['frozen'=>'payload'],'pending payload unchanged');
 ok($options['owr_m1_error']==='Resume pending history before changing storage.','pending configuration rejected');
}
echo "PASS pending article/comment history prevents storage reconfiguration.\n";

function sanitize_key($v){return is_scalar($v)?preg_replace("/[^a-z0-9_-]/","",strtolower((string)$v)):"";}
function wp_unslash($v){return is_array($v)?array_map("wp_unslash",$v):stripslashes($v);}
