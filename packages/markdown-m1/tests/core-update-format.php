<?php
require __DIR__.'/separated-assets.php';
use OzekiResilience\M1\{UpdateContract,Store};
$s3->fail=null;$s3->objects=[];
$a=['post_type'=>'post','content_format'=>'wordpress-block-html','update_contract'=>UpdateContract::SCHEMA,'post_excerpt'=>'','post_parent'=>'0','menu_order'=>'0','comment_status'=>'closed','ping_status'=>'closed','post_password'=>'private','post_author'=>'0','author'=>null,'title'=>'Example','status'=>'publish','slug'=>'example','origin_id'=>10];
$raw='<p>Independent original</p>';
$old=$store->prepare('old','1',$raw,['content_format'=>'wordpress-block-html']);
check($store->originalSource($old)===$raw,'Legacy original still readable');
$new=$store->prepare('new','1',$raw,$a);
check($new['schema']===UpdateContract::ORIGINAL_FORMAT&&$store->originalSource($new)===$raw,'New contract preserves exact original');
$content=json_decode($files['content.json'],true);$content['update_contract']=UpdateContract::SCHEMA;$files['content.json']=Store::json($content);
$point=$site->save($files,$manifest);[$m]=$site->load($point['manifest']);check($m['asset_format']===UpdateContract::SNAPSHOT_FORMAT,'New baseline requires new reader');
$index=$store->createInitialSnapshot(['article'=>['source'=>$raw,'row'=>['schema'=>'owr-md-history-1','sequence'=>0,'attributes'=>$a]]]);
check($store->snapshot($index['key'])['schema']===UpdateContract::INDEX_FORMAT,'New independent index requires new reader');
if(isset($argv[2]))file_put_contents($argv[2],Store::json(['objects'=>$s3->objects,'old_original'=>$old,'new_original'=>$new,'new_point'=>$point['manifest'],'new_index'=>$index['key'],'raw'=>$raw]));
echo "PASS old original readability, lossless core original, new baseline and independent index formats\n";
