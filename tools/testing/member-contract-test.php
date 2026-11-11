<?php
use OzekiResilience\M1\RecoveryRules;
require __DIR__.'/../../packages/markdown-m1/tests/application-rules.php';
require __DIR__.'/MemberApplicationContract.php';
$fields=json_decode(file_get_contents(__DIR__.'/../../packages/markdown-m1/tests/member-fields-editor.json'),true);
$user=array_fill_keys(MemberApplicationContract::USER,'fixture');$user['ID']='3';$user['user_pass']='test-only-hash-never-report';
$raw=['version'=>'3.5.8.1','settings'=>['wpmembers_fields'=>$fields,'wpmembers_settings'=>['db_version'=>'2.4.3','block'=>['post'=>1,'page'=>0],'user_pages'=>['profile'=>24]],'wpmembers_tos'=>false],'users'=>['3'=>['user'=>$user,'meta'=>['first_name'=>['fixture'],'trial_checkbox'=>['accepted'],'trial_multiselect'=>['a,b']]]]];
// Exercise every declared setting, so a contract/production rule change cannot silently
// leave an unrepresented leaf. Real editor fixtures remain the independent external anchor.
$sample=function($rule)use(&$sample){if(is_array($rule)){return array_map($sample,$rule);}return match($rule){'text'=>'fixture','version'=>'2.4.3','number'=>1,'number-empty'=>'','page'=>24,default=>throw new RuntimeException('Uncovered contract type')};};
foreach(MemberApplicationContract::settings() as $key=>$rule)$raw['settings'][$key]=$sample($rule);
$case=$state;$case['membership']=$raw;
$actual=RecoveryRules::project($case,['blogname'])['data']['membership'];
check(MemberApplicationContract::compare($raw,$actual)['pass'],'Normal product output satisfies independent contract');
$original=serialize($raw);$paths=[];
$walk=function($value,$path=[])use(&$walk,&$paths){foreach($value as $k=>$v){$p=[...$path,$k];if(is_array($v)&&$v)$walk($v,$p);else $paths[]=$p;}};$walk($actual);
foreach($paths as $path){$broken=$actual;$ref=&$broken;foreach(array_slice($path,0,-1) as $key)$ref=&$ref[$key];unset($ref[end($path)]);unset($ref);check(!MemberApplicationContract::compare($raw,$broken)['pass'],'Missing leaf must fail');}
$broken=$actual;$broken['settings']['wpmembers_fields'][0]['profile']=false;check(!MemberApplicationContract::compare($raw,$broken)['pass'],'Changed boolean rejected');
$broken=$actual;$broken['users']['3']['meta']['trial_checkbox']=[''];check(!MemberApplicationContract::compare($raw,$broken)['pass'],'Empty differs from checked');
$broken=$actual;$broken['users']['3']['meta']['session_tokens']=['secret'];$r=MemberApplicationContract::compare($raw,$broken);check(!$r['pass']&&!str_contains(json_encode($r),'secret'),'Unexpected access data rejected without disclosure');
$unknown=$raw;$unknown['settings']['unknown']='secret';check(MemberApplicationContract::compare($unknown,$actual)['pass'],'Unsupported source setting excluded explicitly');
$defaults=['runtime_required'=>['enabled'=>true]];$installed=$actual;$installed['settings']['wpmembers_settings']=array_replace_recursive($defaults,$installed['settings']['wpmembers_settings']);
check(MemberApplicationContract::compare($raw,$installed,$defaults)['pass'],'Trusted defaults distinguished from archived settings');
unset($installed['settings']['wpmembers_settings']['runtime_required']);check(!MemberApplicationContract::compare($raw,$installed,$defaults)['pass'],'Missing runtime default rejected');
$bad=$raw;$bad['settings']['wpmembers_fields'][0]['profile']=[];check(!MemberApplicationContract::compare($bad,$actual)['pass'],'Invalid source is not a successful omission');
check(serialize($raw)===$original,'Raw originals unchanged');
echo 'PASS member application contract; '.count($paths)." missing-leaf mutations detected, normal product output, changed values, defaults and exclusions.\n";
