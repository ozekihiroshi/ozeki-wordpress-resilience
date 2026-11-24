<?php
require __DIR__.'/basic-settings.php';
use OzekiResilience\M1\UpdateContract;
$v=UpdateContract::options();check(array_key_exists('default_category',$v)&&array_key_exists('wp_page_for_privacy_policy',$v),'Both reference settings captured');
$d=['options'=>['default_category'=>2,'wp_page_for_privacy_policy'=>5],'tables'=>['terms'=>[['term_id'=>2]],'term_taxonomy'=>[['term_id'=>2,'taxonomy'=>'category']],'posts'=>[['ID'=>5,'post_type'=>'page']]]];$report=[];
UpdateContract::referenceOptions($d,$report);check(!$report&&$d['options']['default_category']===2&&$d['options']['wp_page_for_privacy_policy']===5,'Existing targets retained');
$d['tables']['term_taxonomy']=[];$d['tables']['posts'][0]['post_type']='post';
UpdateContract::referenceOptions($d,$report);check(count($report)===2&&$d['options']['default_category']===0&&$d['options']['wp_page_for_privacy_policy']===0,'Missing or wrong-type targets cleared and reported');
$report=[];UpdateContract::referenceOptions($d,$report);check(!$report,'Explicit unset remains unset');
echo "PASS reference existence, type, removal and no arbitrary reassignment\n";
