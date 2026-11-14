<?php
use OzekiResilience\M1\RecoveryRules;
require __DIR__.'/../../packages/markdown-m1/tests/application-rules.php';
require __DIR__.'/MemberApplicationContract.php';
require __DIR__.'/MemberContractReadback.php';
// Literal expectations remain independent of the production URL conversion helper.
$urlCases=[
    ['https://source.example','https://target.example','https://source.example/profile','https://target.example/profile'],
    ['https://source.example','https://target.example','https://source.example','https://target.example'],
    ['https://source.example/','https://target.example/','https://source.example/profile?view=1#form','https://target.example/profile?view=1#form'],
    ['https://source.example','https://target.example','https://source.example.evil.invalid/profile','https://source.example.evil.invalid/profile'],
    ['https://source.example','https://target.example','https://source.example@evil.invalid/profile','https://source.example@evil.invalid/profile'],
    ['https://source.example/site','https://target.example/new','https://source.example/site/profile','https://target.example/new/profile'],
    ['https://source.example/site','https://target.example/new','https://source.example/site-other/profile','https://source.example/site-other/profile'],
    ['https://source.example/site/','https://target.example/new/','https://source.example/site2/profile','https://source.example/site2/profile'],
    ['https://source.example','https://target.example',24,24],
    ['','https://target.example','/profile','/profile'],
];
foreach($urlCases as [$from,$to,$input,$expectedUrl]){
    $urlRaw=['settings'=>['wpmembers_settings'=>['user_pages'=>['profile'=>$input]],'unrelated'=>$input],'users'=>[]];
    $before=serialize($urlRaw);
    $rebased=MemberContractReadback::destinationExpected($urlRaw,$from,$to);
    check($rebased['settings']['wpmembers_settings']['user_pages']['profile']===$expectedUrl,'Page URL boundary: '.(string)$input);
    check($rebased['settings']['unrelated']===$input&&serialize($urlRaw)===$before,'Only page references change; originals preserved');
}
echo 'PASS '.count($urlCases)." independent page URL boundary cases.\n";
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
$prepared=['wpmembers_settings'=>['version'=>'prepared','db_version'=>'2.4.3','runtime_required'=>['enabled'=>true]],'wpmembers_dialogs'=>['prepared_only'=>'keep']];$installed=$actual;
$installed['settings']['wpmembers_settings']=array_replace_recursive($prepared['wpmembers_settings'],$installed['settings']['wpmembers_settings']);$installed['settings']['wpmembers_settings']['version']='prepared';$installed['settings']['wpmembers_settings']['db_version']='2.4.3';
$installed['settings']['wpmembers_dialogs']['prepared_only']='keep';
check(MemberApplicationContract::compare($raw,$installed,$prepared)['pass'],'Prepared destination settings distinguished from archived settings');
$reset=$installed;$reset['settings']['wpmembers_settings']['runtime_required']['enabled']=false;check(!MemberApplicationContract::compare($raw,$reset,$prepared)['pass'],'Reset to a different installation default rejected');
unset($installed['settings']['wpmembers_settings']['runtime_required']);check(!MemberApplicationContract::compare($raw,$installed,$prepared)['pass'],'Missing prepared runtime setting rejected');
$bad=$raw;$bad['settings']['wpmembers_fields'][0]['profile']=[];check(!MemberApplicationContract::compare($bad,$actual)['pass'],'Invalid source is not a successful omission');
check(serialize($raw)===$original,'Raw originals unchanged');
echo 'PASS member application contract; '.count($paths)." missing-leaf mutations detected, normal product output, changed values, prepared settings and exclusions.\n";
