<?php
/** Run against an isolated WordPress: php flamingo-application.php /path/to/wp-load.php */
if(!class_exists('OzekiResilience\\M1\\RecoveryRules',false))require $argv[1];
set_exception_handler(function($error){fwrite(STDERR,$error->getMessage()."\n");exit(1);});
use OzekiResilience\M1\{RecoveryRules,Store};
function fg_check(bool $ok,string $message): void { if(!$ok)throw new RuntimeException($message); }
function fg_state(array $map,array $individual): array {
    $rows=[];
    foreach(['_fields'=>serialize($map)]+$individual as $key=>$raw)$rows[]=['meta_id'=>(string)(count($rows)+1),'post_id'=>'41','meta_key'=>$key,'meta_value'=>$raw];
    return ['tables'=>['posts'=>[['ID'=>'41','post_type'=>'flamingo_inbound','post_content'=>'']], 'postmeta'=>$rows,'commentmeta'=>[],'termmeta'=>[],'terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[]],'options'=>[]];
}
function fg_values(array $state): array {
    $meta=[];foreach($state['tables']['postmeta'] as $row){$raw=$row['meta_value'];$meta[$row['meta_key']]=preg_match('/^(?:a|s|i|b|d|O|C):|^N;$/',$raw)?unserialize($raw,['allowed_classes'=>false]):$raw;}
    $values=$meta['_fields'];foreach($values as $key=>&$value){$name=sanitize_key('_field_'.$key);if(array_key_exists($name,$meta))$value=$meta[$name];}unset($value);
    return $values;
}
$expected=['your-name'=>'技術者','your-message'=>"本文 & < >\n次の行",'choice'=>['PLC','solar'],'zero'=>'0','empty'=>'','encoded'=>'a:1:{i:0;s:1:"x";}'];
$individual=[];foreach($expected as $key=>$value)$individual['_field_'.$key]=is_array($value)||$key==='encoded'?serialize($value):$value;
$state=fg_state(array_fill_keys(array_keys($expected),null),$individual+['_field_unlisted'=>'not declared','_recaptcha'=>'not applied']);
$frozen=Store::json($state);$projected=RecoveryRules::project($state,[]);
fg_check(fg_values($projected['data'])===$expected,'Real Flamingo effective values must survive, not merely its null _fields map');
fg_check(Store::json($state)===$frozen,'Never rewrite the preserved input');
$keys=array_column($projected['data']['tables']['postmeta'],'meta_key');
fg_check(!in_array('_field_unlisted',$keys,true)&&!in_array('_recaptcha',$keys,true),'No wildcard metadata permission');
$legacy=fg_state($expected,[]);fg_check(fg_values(RecoveryRules::project($legacy,[])['data'])===$expected,'Legacy inline fields remain readable');
$mixed=fg_state($expected,['_field_your-name'=>'Updated']);$mixedExpected=$expected;$mixedExpected['your-name']='Updated';
fg_check(fg_values(RecoveryRules::project($mixed,[])['data'])===$mixedExpected,'Individual values take precedence as in Flamingo');
foreach(['_field_your-name','_field_choice','_field_zero'] as $drop){
    $mutant=$projected['data'];$mutant['tables']['postmeta']=array_values(array_filter($mutant['tables']['postmeta'],fn($r)=>$r['meta_key']!==$drop));
    fg_check(fg_values($mutant)!==$expected,'Acceptance must detect omitted '.$drop);
}
$bad=fg_state(['your-name'=>null],['_field_your-name'=>serialize((object)['bad'=>true])]);
try{RecoveryRules::project($bad,[]);throw new LogicException('Object accepted');}catch(RuntimeException $e){}
foreach([['A B'=>null,'ab'=>null],[''=>null]] as $map){
    try{RecoveryRules::project(fg_state($map,[]),[]);throw new LogicException('Ambiguous field accepted');}catch(RuntimeException $e){}
}
$duplicate=$state;$duplicate['tables']['postmeta'][]=$state['tables']['postmeta'][0];
try{RecoveryRules::project($duplicate,[]);throw new LogicException('Duplicate map accepted');}catch(RuntimeException $e){}
$other=$state;$other['tables']['posts'][0]['post_type']='post';
$otherKeys=array_column(RecoveryRules::project($other,[])['data']['tables']['postmeta'],'meta_key');
fg_check(!in_array('_field_your-name',$otherKeys,true),'Field permission stays within Flamingo receipts');
echo "Flamingo application contract passed\n";
