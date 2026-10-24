<?php
require __DIR__.'/site-recovery-post-diff.php';
function row(int $id,string $status='publish'): array {return ['ID'=>$id,'post_content'=>'body','post_title'=>'title','post_excerpt'=>'','post_status'=>$status,'post_name'=>'slug','post_type'=>'post','post_parent'=>0,'menu_order'=>0,'comment_status'=>'closed','ping_status'=>'closed'];}
$expected=[row(1),row(37)];$target=[row(1),row(30,'auto-draft'),row(40,'draft'),row(41)];
$r=owr_recovery_post_diff($expected,$target);
if(array_column($r['destination_only'],'id')!==[30,40,41]||array_column($r['source_only'],'id')!==[37]||!$r['destination_only_requires_review'])throw new Exception('Missing one-sided rows');
$changed=row(1);$changed['post_content']='changed';$r=owr_recovery_post_diff([row(1)],[$changed]);
if($r['changed'][0]['fields']!==['post_content']||$r['destination_only_requires_review'])throw new Exception('Changed fields');
if(count(owr_recovery_post_diff([],$target)['destination_only'])!==4)throw new Exception('Empty source');
try{owr_recovery_post_diff([row(1),row(1)],[]);throw new Exception('Duplicate accepted');}catch(InvalidArgumentException $e){}
echo "PASS bidirectional post diff: publish/draft/auto-draft, additions, changes, empty source, duplicate IDs\n";
