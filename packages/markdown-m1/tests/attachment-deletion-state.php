<?php
require __DIR__.'/separated-assets.php';
use OzekiResilience\M1\{AttachmentHistory,Store,UpdateContract};
$d=['tables'=>[
 'posts'=>[['ID'=>'8','post_type'=>'attachment'],['ID'=>'9','post_type'=>'post']],
 'postmeta'=>[['post_id'=>'8','meta_key'=>'_wp_attached_file','meta_value'=>'deleted.png'],['post_id'=>'9','meta_key'=>'_thumbnail_id','meta_value'=>'8'],['post_id'=>'9','meta_key'=>'other','meta_value'=>'keep']],
 'comments'=>[['comment_ID'=>'2','comment_post_ID'=>'8'],['comment_ID'=>'3','comment_post_ID'=>'9']],
 'commentmeta'=>[['comment_id'=>'2'],['comment_id'=>'3']],
 'term_relationships'=>[['object_id'=>'8'],['object_id'=>'9']]],'media_access'=>['uploads/deleted.png'=>['mode'=>'public']]];
$files=['uploads/deleted.png'=>'original'];
$v=['schema'=>AttachmentHistory::SCHEMA,'id'=>8,'deleted'=>true,'deleted_paths'=>['uploads/deleted.png']];
AttachmentHistory::replay($d,$files,Store::json($v),['attachment_schema'=>AttachmentHistory::SCHEMA,'update_contract'=>UpdateContract::SCHEMA,'origin_id'=>8,'media'=>[]],$store);
check(!$files&&array_column($d['tables']['posts'],'ID')===['9'],'Deleted attachment is not restored');
check(array_column($d['tables']['postmeta'],'meta_key')===['other'],'Only matching thumbnail reference removed');
check(array_column($d['tables']['comments'],'comment_ID')===['3']&&array_column($d['tables']['commentmeta'],'comment_id')===['3'],'Attachment comments and metadata removed, article comments retained');
check(array_column($d['tables']['term_relationships'],'object_id')===['9'],'Attachment relationships removed');
check($d['deleted_media'][8]===['uploads/deleted.png'],'Deletion evidence survives replay');
echo "PASS attachment deletion, related state and retained deletion evidence\n";
