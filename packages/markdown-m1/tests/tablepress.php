<?php
// Standalone WordPress API fixture for guarded product includes.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require_once __DIR__.'/../src/Store.php';
require_once __DIR__.'/../src/TableHistory.php';
use Owr\M1\TableHistory;
function must($b,$m){if(!$b)throw new RuntimeException($m);}
function reject($f){try{$f();}catch(RuntimeException $e){return;}throw new RuntimeException('Expected rejection');}
$d=['tables'=>['posts'=>[],'postmeta'=>[]],'options'=>['tablepress_tables'=>'{"last_id":0,"table_post":{}}','tablepress_plugin_options'=>'{}']];
$a=['origin_id'=>'1','tablepress_version'=>'3.4.1'];
$v=['schema'=>'owr-table-1','kind'=>'table','id'=>'1','old_id'=>'','last_id'=>1,'version'=>'3.4.1','post'=>['ID'=>'10','post_type'=>'tablepress_table','post_content'=>'[["原文","A"]]'],'meta'=>[['meta_key'=>'_tablepress_table_options','meta_value'=>'{"table_head":true}'],['meta_key'=>'_tablepress_table_visibility','meta_value'=>'{"rows":[1],"columns":[1,1]}']]];
TableHistory::replay($d,json_encode($v),$a);TableHistory::replay($d,json_encode($v),$a);
must(count($d['tables']['posts'])===1&&count($d['tables']['postmeta'])===2,'Idempotent table and meta');
$v['id']='new-table';$v['old_id']='1';$a['origin_id']='new-table';TableHistory::replay($d,json_encode($v),$a);
$m=json_decode($d['options']['tablepress_tables'],true);must(!isset($m['table_post'][1])&&$m['table_post']['new-table']===10,'ID rename');
$bad=$v;$bad['meta'][0]['meta_key']='_arbitrary';reject(function()use($d,$bad,$a){TableHistory::replay($d,json_encode($bad),$a);});
$bad=$v;$bad['post']['post_type']='page';reject(function()use($d,$bad,$a){TableHistory::replay($d,json_encode($bad),$a);});
$none=[];reject(function()use($none,$v,$a){TableHistory::replay($none,json_encode($v),$a);});
$v['kind']='delete';TableHistory::replay($d,json_encode($v),$a);must(!$d['tables']['posts']&&!$d['tables']['postmeta'],'Tombstone removes table');
$v['kind']='settings';$v['id']='';$a['origin_id']='';$v['settings']='{"custom_css":".tablepress{color:red}"}';TableHistory::replay($d,json_encode($v),$a);must($d['options']['tablepress_plugin_options']===$v['settings'],'Full settings');
echo "TablePress replay checks PASS\n";

// Fresh TablePress can keep defaults in memory until its first table/settings write.
function get_option($key){return false;}
class TablePress {public static $model_table;public static $model_options;}
TablePress::$model_table=new class {function _debug_get_tables(){return ['last_id'=>0,'table_post'=>[]];}};
TablePress::$model_options=new class {function _debug_get_plugin_options(){return ['custom_css'=>'','use_custom_css'=>true];}};
$empty=['tables'=>['postmeta'=>[]],'options'=>[]];TableHistory::baseline($empty);
must(json_decode($empty['options']['tablepress_tables'],true)['last_id']===0,'Fresh baseline default registry');
echo "TablePress unpersisted defaults check PASS\n";
