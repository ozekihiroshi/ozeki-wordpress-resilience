<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/separated-assets.php';
$s3->fail=null; // Previous contract deliberately leaves its write-failure switch enabled.
foreach(['FormHistory','MemberHistory','TableHistory'] as $class)require_once $argv[1].'/src/'.$class.'.php';
use OzekiResilience\M1\{RecoveryRules,FormHistory,Store};
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
function determine_locale(){return 'en_US';} // Standalone WordPress locale fixture.
function sanitize_key($key){return preg_replace('/[^a-z0-9_-]/','',strtolower((string)$key));} // Core metadata-name mapping.
$state=['tables'=>['posts'=>[['ID'=>'10','post_type'=>'wpcf7_contact_form','post_content'=>''],['ID'=>'11','post_type'=>'flamingo_inbound','post_content'=>'問い合わせ'],['ID'=>'12','post_type'=>'tablepress_table','post_content'=>'[["Item","Count"],["A",2]]'],['ID'=>'13','post_type'=>'ozmd_document','post_content'=>'generated']], 'postmeta'=>[], 'commentmeta'=>[['comment_id'=>'1','meta_key'=>'extension','meta_value'=>'private value']], 'termmeta'=>[],'term_relationships'=>[],'terms'=>[],'term_taxonomy'=>[]], 'options'=>['blogname'=>'Example','tablepress_tables'=>'{"table_post":{"1":12},"last_id":1}','tablepress_plugin_options'=>'{"tablepress_version":"3.4.1","custom_css":"private-style","modules":{"unknown":true}}','widget_unknown'=>['private'=>'do not apply']], 'membership'=>['version'=>'3.5.8.1','settings'=>['wpmembers_settings'=>['mod_reg'=>1,'block'=>['post'=>1,'page'=>0],'extension'=>'private-setting'],'wpmembers_fields'=>[[1,'Name','first_name','text','y','y','n','profile'=>1]],'wpmembers_dialogs'=>['success'=>'Welcome'],'wpmembers_tos'=>'Terms'], 'users'=>['3'=>['user'=>['ID'=>'3','user_pass'=>'private hash'],'meta'=>['first_name'=>['Alice'],'active'=>['1'],'session_tokens'=>['private token']]]]]];
$add=function($id,$key,$value)use(&$state){$state['tables']['postmeta'][]=['meta_id'=>(string)(count($state['tables']['postmeta'])+1),'post_id'=>(string)$id,'meta_key'=>$key,'meta_value'=>$value];};
$add(10,'_form','[text your-name]');$add(10,'_mail',serialize(['subject'=>'Question','body'=>'[your-name]','active'=>true,'extension'=>'private-mail']));
$add(10,'_additional_settings',"skip_mail: on\nextension_action: private-command");$add(10,'unknown','private unknown');
$add(11,'_fields',serialize(['your-name'=>'Alice','your-message'=>'Saved content']));$add(11,'_recaptcha',serialize(['private'=>'token']));
$add(12,'_tablepress_table_options','{"table_head":1,"datatables_sort":true,"datatables_paginate":true,"datatables_paginate_entries":10,"datatables_custom_commands":"private-js"}');$add(12,'_tablepress_table_visibility','{"rows":[1,1],"columns":[1,1]}');
$add(13,'_ozmd_source',"# Source\n```mermaid\ngraph LR; A-->B\n```");
$state['tables']['commentmeta'][]=['comment_id'=>'1','meta_key'=>'_wp_trash_meta_status','meta_value'=>'1'];
$before=Store::json($state);$first=RecoveryRules::project($state,['blogname']);
check(Store::json($state)===$before,'Projection must not mutate original input');
$find=function($d,$id,$key){foreach($d['tables']['postmeta'] as $m)if($m['post_id']==$id&&$m['meta_key']===$key)return $m['meta_value'];return null;};
check($find($first['data'],13,'_ozmd_source')===$find($state,13,'_ozmd_source'),'MD unchanged');
$textState=$state;foreach($textState['tables']['postmeta'] as &$meta)if($meta['meta_key']==='_ozmd_source')$meta['meta_value']='a:1:{i:0;s:4:"text";}';unset($meta);
check($find(RecoveryRules::project($textState,['blogname'])['data'],13,'_ozmd_source')==='a:1:{i:0;s:4:"text";}','Serialization-looking Markdown remains text');
check($find($first['data'],11,'_fields')===$find($state,11,'_fields'),'Submitted fields unchanged');
check($find($first['data'],10,'unknown')===null&&$find($first['data'],11,'_recaptcha')===null,'Unrecognized metadata not applied');
check(unserialize($find($first['data'],10,'_mail'))===['subject'=>'Question','body'=>'[your-name]','active'=>true],'CF7 nested recognized attributes');
check($find($first['data'],10,'_additional_settings')==='skip_mail: on','Known additional directive only');
$opts=json_decode($find($first['data'],12,'_tablepress_table_options'),true);check($opts['datatables_sort']&&$opts['datatables_paginate']&&($opts['datatables_custom_commands']??null)==='','Table controls kept; executable source withheld; safe empty runtime value required');
foreach(['',null,[], 'initComplete: function(){window.__owrArchivedExecuted=true;}'] as $commands){
 $case=$state;foreach($case['tables']['postmeta'] as &$row)if($row['post_id']==='12'&&$row['meta_key']==='_tablepress_table_options')$row['meta_value']=Store::json(['table_head'=>0,'datatables_sort'=>false,'datatables_paginate'=>false,'extra_css_classes'=>'','datatables_custom_commands'=>$commands]);unset($row);
 $frozen=Store::json($case);$applied=RecoveryRules::project($case,['blogname']);$options=json_decode($find($applied['data'],12,'_tablepress_table_options'),true);
 check($options===['table_head'=>0,'datatables_sort'=>false,'datatables_paginate'=>false,'extra_css_classes'=>'','datatables_custom_commands'=>''],'Independent exact runtime expectation; preserve zero/false/empty and neutralize executable setting');
 check(Store::json($case)===$frozen,'Complete original unchanged including excluded setting');
 $missing=$options;unset($missing['datatables_custom_commands']);check(($missing['datatables_custom_commands']??null)!=='','Removing runtime default must fail the acceptance predicate');
}
check($first['data']['membership']['settings']['wpmembers_settings']['mod_reg']===1&&$first['data']['membership']['users']['3']['meta']['active']===['1'],'Approval retained');
check(!isset($first['data']['membership']['users']['3']['meta']['session_tokens']),'Sessions withheld');
foreach(['2.4.3','2.4',243,2.4] as $version){
 $case=$state;$case['membership']['settings']['wpmembers_settings']['db_version']=$version;
 $original=Store::json($case);$result=RecoveryRules::project($case,['blogname']);
 check($result['data']['membership']['settings']['wpmembers_settings']['db_version']===$version,'Member DB version preserved without conversion');
 check(Store::json($case)===$original,'Member version original unchanged');
}
foreach([['2.4.3'],true,null,'2..4','<script>'] as $version){
 $case=$state;$case['membership']['settings']['wpmembers_settings']['db_version']=$version;
 reject(fn()=>RecoveryRules::project($case,['blogname']));
}
foreach([0,2,'2','','https://example.org/profile'] as $page){
 $case=$state;$case['membership']['settings']['wpmembers_settings']['user_pages']=['profile'=>$page,'register'=>$page,'login'=>$page];
 $original=Store::json($case);$result=RecoveryRules::project($case,['blogname']);
 check($result['data']['membership']['settings']['wpmembers_settings']['user_pages']['profile']===$page,'Member page ID or URL retained');
 check(Store::json($case)===$original,'Member page original unchanged');
}
foreach([[],true,-1,2.5] as $page){
 $case=$state;$case['membership']['settings']['wpmembers_settings']['user_pages']=['profile'=>$page];
 reject(fn()=>RecoveryRules::project($case,['blogname']));
}
check(!str_contains(Store::json($first['report']),'private-')&&!str_contains(Store::json($first['report']),'private token'),'Report does not expose values');
// Captured from WP-Members 3.5.8.1's real Add Field form, not invented normalized definitions.
$editorFields=json_decode(file_get_contents(__DIR__.'/member-fields-editor.json'),true,512,JSON_THROW_ON_ERROR);
foreach([true,false,1,0,'1','0'] as $profile){
 $case=$state;$fields=$editorFields;foreach($fields as &$field)$field['profile']=$profile;unset($field);
 $case['membership']['settings']['wpmembers_fields']=$fields;
 $case['membership']['users']['3']['meta']+=['trial_checkbox'=>['accepted'],'trial_multiselect'=>['a,b'],'trial_hidden'=>['fixed']];
 $original=Store::json($case);$projected=RecoveryRules::project($case,['blogname'])['data'];
 check($projected['membership']['settings']['wpmembers_fields']===$fields,'Editor field definitions retained, including native storage types');
 foreach(['trial_checkbox','trial_multiselect','trial_hidden'] as $key)check($projected['membership']['users']['3']['meta'][$key]===$case['membership']['users']['3']['meta'][$key],'Member values retained with their definitions');
 check(Store::json($case)===$original,'Member editor originals unchanged');
 check(RecoveryRules::project($projected,['blogname'])['data']['membership']===$projected['membership'],'Member application is stable on another recovery');
}
$fieldCase=function($type,$key,$value)use($state,$editorFields){$case=$state;foreach($editorFields as $f)if($f[3]===$type){$f[$key]=$value;$case['membership']['settings']['wpmembers_fields']=[$f];break;}return $case;};
foreach([['multiselect',8,'|'],['checkbox',8,'y'],['checkbox',7,'0'],['date','min',''],['number','max',''],['textarea','rows','']] as [$type,$key,$value]){
 $case=$fieldCase($type,$key,$value);$result=RecoveryRules::project($case,['blogname']);
 check($result['data']['membership']['settings']['wpmembers_fields']===$case['membership']['settings']['wpmembers_fields'],'Optional empty constraints and alternate native field settings preserved');
}
foreach([['text','profile',2],['text','profile','yes'],['text','profile',[]],['select',7,'a|Alpha'],['select',7,[['nested']]],['checkbox',7,['accepted']],['checkbox',8,'yes'],['multiselect',8,';'],['number','min',[]],['textarea','rows','four'],['text','pattern',new stdClass()]] as [$type,$key,$value]){
 $case=$fieldCase($type,$key,$value);reject(fn()=>RecoveryRules::project($case,['blogname']));
}
$case=$fieldCase('text','extension_command','private-command');$projected=RecoveryRules::project($case,['blogname']);
check(!isset($projected['data']['membership']['settings']['wpmembers_fields'][0]['extension_command']),'Unknown field settings remain withheld');
check(!str_contains(Store::json($projected['report']),'private-command'),'Field omission report does not expose values');
check(count($first['data']['tables']['commentmeta'])===1&&$first['data']['tables']['commentmeta'][0]['meta_key']==='_wp_trash_meta_status','Core comment trash state retained');
// Both baseline and confirmed-history overlay arrive at the same projection boundary.
$baseline=$site->save(['content.json'=>$before,'software.zip'=>'fixture'],['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial']);
$item=['post'=>$state['tables']['posts'][0],'meta'=>array_values(array_map(fn($m)=>['meta_key'=>$m['meta_key'],'meta_value'=>$m['meta_value']],array_filter($state['tables']['postmeta'],fn($m)=>$m['post_id']==='10'))),'channels'=>[]];
$after=$state;FormHistory::replay($after,Store::json(['schema'=>'owr-form-1','items'=>[$item]]),['origin_id'=>10]);
$tail=RecoveryRules::project($after,['blogname']);
check($find($tail['data'],10,'_mail')===$find($first['data'],10,'_mail'),'Same baseline/tail rule');
check($find($after,10,'unknown')==='private unknown','Replay retains unknown before projection');
$savedObjects=$s3->objects;[$manifest,$stored]=$site->load($baseline['manifest']);RecoveryRules::project(json_decode($stored['content.json'],true),['blogname']);
check($s3->objects===$savedObjects&&str_contains($stored['content.json'],'private unknown'),'No S3 mutation or unknown loss');
$bad=$state;$bad['tables']['postmeta'][]=['post_id'=>'12','meta_key'=>'_tablepress_table_options','meta_value'=>'{"datatables_sort":{"code":"bad"}}'];reject(fn()=>RecoveryRules::project($bad,['blogname']));
$success=['at'=>'now','through'=>1,'posts'=>4,'files'=>0,'application_report'=>$first['report']];ob_start();OzekiResilience\M1\Plugin::renderSiteResult(['status'=>'success']+$success,$success,[]);$html=ob_get_clean();
check(str_contains($html,'Preserved in S3')&&str_contains($html,'postmeta.10.unknown')&&!str_contains($html,'private unknown'),'Visible value-free reasons');
ob_start();OzekiResilience\M1\Plugin::renderSiteResult(['status'=>'failed','error'=>'failure'],$success,[]);$html=ob_get_clean();check(!str_contains(explode('<details>',$html)[0],'Preserved in S3'),'Failure cannot show old projection as current');
echo "PASS common baseline/tail rules, originals preserved, core adapter settings, unknown withholding, invalid known type stops, value-free result report.\n";

$legacy=[["post_id"=>"1","meta_key"=>"_owr_m1_asset","meta_value"=>"asset","meta_id"=>"1"]];
$mapped=\OzekiResilience\M1\Identifiers::metadata($legacy);
if($mapped[0]["meta_key"]!=="_ozeki_resilience_m1_asset"||$legacy[0]["meta_key"]!=="_owr_m1_asset")throw new RuntimeException("Legacy archive mapping failed");

// Existing contracts CI must check effective receipt values, not only _fields.
(static function(){require __DIR__.'/flamingo-application.php';})();
