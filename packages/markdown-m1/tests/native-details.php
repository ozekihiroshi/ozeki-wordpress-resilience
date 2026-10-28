<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/NativeHistory.php';
use OzekiResilience\M1\NativeHistory;
function ok($v,$m){if(!$v)throw new RuntimeException($m);}
$d=['tables'=>['posts'=>[['ID'=>'10','post_type'=>'post','post_status'=>'publish','post_parent'=>'0'],['ID'=>'11','post_type'=>'post','post_status'=>'publish','post_parent'=>'0'],['ID'=>'20','post_type'=>'attachment','post_status'=>'inherit','post_parent'=>'10','post_mime_type'=>'image/png']],'postmeta'=>[],'terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[],'comments'=>[['comment_ID'=>'1','comment_post_ID'=>'10']],'commentmeta'=>[['comment_id'=>'1']]]];$files=['posts/10.html'=>'old'];
$v=['schema'=>'owr-native-state-1','id'=>10,'type'=>'post','deleted'=>false,'thumbnail'=>20,'terms'=>[['term_id'=>'2','term_taxonomy_id'=>'2','taxonomy'=>'category','name'=>'Trial','slug'=>'trial','term_group'=>'0','description'=>'','parent'=>'0']],'assigned'=>['2']];
NativeHistory::replay($d,$files,json_encode($v),['origin_id'=>10]);ok($d['tables']['postmeta'][0]['meta_value']==='20','Thumbnail');ok(count($d['tables']['term_relationships'])===1,'Assigned');ok($d['tables']['term_taxonomy'][0]['count']==='1','Count');
$v['thumbnail']=0;$v['terms']=[];$v['assigned']=[];NativeHistory::replay($d,$files,json_encode($v),['origin_id'=>10]);ok(!$d['tables']['postmeta']&&!$d['tables']['term_relationships'],'Removal');
$d['tables']['posts'][]=['ID'=>'30','post_type'=>'revision','post_status'=>'inherit','post_parent'=>'10'];$d['tables']['postmeta'][]=['meta_id'=>'30','post_id'=>'30','meta_key'=>'revision','meta_value'=>'old'];$v['deleted']=true;NativeHistory::replay($d,$files,json_encode($v),['origin_id'=>10]);ok(count($d['tables']['posts'])===2&&!$d['tables']['comments']&&!$d['tables']['commentmeta']&&!isset($files['posts/10.html']),'Cascade');ok($d['tables']['posts'][1]['post_parent']==='0','Attachment detached');
NativeHistory::replay($d,$files,json_encode($v),['origin_id'=>10]);ok(count($d['tables']['posts'])===2,'Idempotent');
$rejected=false;try{NativeHistory::replay($d,$files,json_encode($v),['origin_id'=>11]);}catch(RuntimeException $x){$rejected=true;}ok($rejected,'Identity');echo "PASS native state thumbnail removal, terms/counts, delete relations, unrelated records, repeat and identity\n";
