<?php
spl_autoload_register(function($n){$p='OzekiResilience\\M1\\';if(str_starts_with($n,$p)){$f='/tmp/product/src/'.substr($n,strlen($p)).'.php';if(is_file($f))require_once $f;}});
use OzekiResilience\M1\{MemberHistory,MemberReconstruction,Store};
$mode=$args[0];$p='/tmp/member-material.json';
function material(){global $wpdb;$d=['membership'=>MemberHistory::baseline(),'tables'=>[]];foreach(['posts','postmeta'] as $t)$d['tables'][$t]=$wpdb->get_results('SELECT * FROM '.$wpdb->$t,ARRAY_A);return $d;}
if($mode==='baseline'){$d=material();file_put_contents($p,json_encode($d));echo json_encode(['users'=>count($d['membership']['users']),'fields'=>count($d['membership']['settings']['wpmembers_fields'])]);return;}
$d=json_decode(file_get_contents($p),true);$current=material();$through=0;
// Freeze the actual completed ordinary profile update as the existing formal member contract.
foreach($current['membership']['users'] as $id=>$entry){
 $a=['post_type'=>'owr_member','origin_id'=>(int)$id,'member_version'=>$current['membership']['version']];
 $raw=Store::json(['schema'=>'owr-member-1','kind'=>'user','id'=>(int)$id,'value'=>$entry]);MemberHistory::replay($d,$raw,$a);$through++;
}
$manifest=['source_url'=>home_url(),'through'=>$through];$files=['content.json'=>Store::json($d)];$before=hash('sha256',$files['content.json']);$plan=MemberReconstruction::plan($manifest,$files);
echo json_encode(['plan'=>$plan,'unchanged'=>$before===hash('sha256',$files['content.json']),'raw_hash_present'=>!empty(reset($d['membership']['users'])['user']['user_pass']),'baseline_sha256'=>hash_file('sha256',$p)]);
