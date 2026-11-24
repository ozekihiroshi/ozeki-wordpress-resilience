<?php
require __DIR__.'/core-update-contract.php';
require_once __DIR__.'/../src/CommentHistory.php';
use OzekiResilience\M1\{CoreStateHistory,UpdateContract,Store};
$comment=['comment_ID'=>'2','comment_post_ID'=>'10','comment_content'=>'Reply','comment_approved'=>'trash','comment_parent'=>'0'];
$data=['authors'=>[],'tables'=>['posts'=>[['ID'=>'10','post_author'=>'3']],'comments'=>[$comment],'commentmeta'=>[['meta_id'=>'1','comment_id'=>'2','meta_key'=>'_wp_trash_meta_status','meta_value'=>'1']]]];
$v=['schema'=>UpdateContract::SCHEMA,'kind'=>'comment:2','comment'=>$comment,'meta'=>['_wp_trash_meta_status'=>'0','_wp_trash_meta_time'=>'123']];
CoreStateHistory::replay($data,Store::json($v));
check(array_column($data['tables']['commentmeta'],'meta_value','meta_key')===$v['meta'],'Completed operation replaces stale approval');
$v['comment']['comment_approved']='0';$v['meta']=[];CoreStateHistory::replay($data,Store::json($v));check(!$data['tables']['commentmeta'],'Untrash clears old transition metadata');
$v=['schema'=>UpdateContract::SCHEMA,'kind'=>'authors','authors'=>['4'=>['display_name'=>'New author','user_nicename'=>'new-author']],'assignments'=>['10'=>'4']];
CoreStateHistory::replay($data,Store::json($v));check($data['tables']['posts'][0]['post_author']==='4'&&$data['authors']['4']['display_name']==='New author','Author definition and assignment move together');
echo "PASS completed comment metadata and author assignment\n";
