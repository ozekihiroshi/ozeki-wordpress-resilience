<?php
define('ABSPATH',__DIR__.'/');
require_once __DIR__.'/../src/MemberHistory.php';
require_once __DIR__.'/../src/SetupReadiness.php';
use OzekiResilience\M1\MemberHistory;
function determine_locale(){return $GLOBALS['test_locale']??'en_US';}
$options=['wpmembers_settings'=>['version'=>'destination','db_version'=>123,'captcha'=>7,'form_tags'=>['default'=>'prepared'],'shortcodes'=>['other'=>1]],'wpmembers_dialogs'=>['destination_only'=>'keep','restricted_msg'=>'old']];
function get_option($key,$default=false){global $options;return $options[$key]??$default;}
class ContractRelocate {public static function relocate($v,$from,$to){if(is_array($v))return array_map(fn($x)=>self::relocate($x,$from,$to),$v);return is_string($v)?str_replace($from,$to,$v):$v;}}
class_alias(ContractRelocate::class,'OzekiResilience\\M1\\SiteSnapshot');
function check($ok,$label){if(!$ok)throw new RuntimeException($label);}
$before=$options;
$result=MemberHistory::preparedSettings(['wpmembers_settings'=>['version'=>'source','db_version'=>1,'shortcodes'=>['enable_field'=>1]],'wpmembers_dialogs'=>['restricted_msg'=>'restored'],'wpmembers_fields'=>[],'wpmembers_tos'=>false]);
check($options===$before,'Preparation check must be read-only');
check($result['wpmembers_settings']['version']==='destination'&&$result['wpmembers_settings']['db_version']===123,'Destination version retained');
check($result['wpmembers_settings']['captcha']===7&&$result['wpmembers_settings']['form_tags']['default']==='prepared','Prepared runtime retained');
check($result['wpmembers_settings']['shortcodes']===['other'=>1,'enable_field'=>1],'Recognized nested setting applied without resetting siblings');
check($result['wpmembers_dialogs']===['destination_only'=>'keep','restricted_msg'=>'restored'],'Prepared dialogs retained');
check($result['wpmembers_fields']===[]&&!isset($result['wpmembers_tos']),'Empty collection replaces; absent option does not erase destination');
$options['wpmembers_settings']['form_tags']['default']='Keep https://source.invalid unchanged';
$moved=MemberHistory::preparedSettings(['wpmembers_settings'=>['user_pages'=>['profile'=>'https://source.invalid/profile']]],'https://source.invalid','https://target.invalid');
check($moved['wpmembers_settings']['form_tags']['default']==='Keep https://source.invalid unchanged','Prepared strings must not be relocated');
check($moved['wpmembers_settings']['user_pages']['profile']==='https://target.invalid/profile','Archived page reference relocated');
unset($options['wpmembers_settings']);
try{MemberHistory::preparedSettings([]);throw new LogicException('Missing preparation accepted');}catch(RuntimeException $e){check(str_contains($e->getMessage(),'Set up WP-Members'),'Actionable preparation message');}
$GLOBALS['test_locale']='ja';
try{MemberHistory::preparedSettings([]);throw new LogicException('Missing preparation accepted');}catch(RuntimeException $e){check(str_contains($e->getMessage(),'セットアップ'),'Japanese preparation message');}
echo "Prepared settings contract PASS\n";
