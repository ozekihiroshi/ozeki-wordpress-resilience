<?php
require __DIR__.'/navigation-state.php';
use OzekiResilience\M1\{UpdateContract,CoreStateHistory,Store};
$expected=['blogdescription'=>'Changed description','category_base'=>'topics','tag_base'=>'labels','date_format'=>'d/m/Y','time_format'=>'g:i a','start_of_week'=>0,'posts_per_rss'=>5,'default_comment_status'=>'closed','default_ping_status'=>'closed'];
$values=UpdateContract::options();
foreach($expected as $key=>$value){check(array_key_exists($key,$values),'Daily contract must cover '.$key);$values[$key]=$value;}
$data=['options'=>['active_plugins'=>['prepared/plugin.php'],'stylesheet'=>'prepared-theme']];
CoreStateHistory::replay($data,Store::json(['schema'=>UpdateContract::SCHEMA,'kind'=>'options','options'=>$values]));
foreach($expected as $key=>$value)check($data['options'][$key]===$value,'Setting meaning retained: '.$key);
check($data['options']['active_plugins']===['prepared/plugin.php']&&$data['options']['stylesheet']==='prepared-theme','Prepared software settings retained');
echo "PASS nine basic settings and prepared software boundary\n";
$old=['schema'=>'owr-core-updates-3','kind'=>'options','options'=>$values];$failed=false;
try{CoreStateHistory::replay($data,Store::json($old));}catch(Throwable $e){$failed=true;}check($failed,'Earlier unpublished settings contract rejected');
