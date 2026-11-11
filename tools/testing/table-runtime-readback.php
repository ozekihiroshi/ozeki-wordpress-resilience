<?php
// Development-only readback. Invoke in a fresh request on an isolated prepared site.
require $argv[1].'/wp-load.php';
if(!defined('DISABLE_WP_CRON')||!DISABLE_WP_CRON)throw new RuntimeException('Use an isolated site with cron disabled');
$expected=json_decode(file_get_contents($argv[2]),true,512,JSON_THROW_ON_ERROR);
$fail=[];$template=TablePress::$model_table->get_table_template()['options'];
foreach($expected as $id=>$e){
 $table=TablePress::$model_table->load((string)$id,true,true);
 if(is_wp_error($table)){$fail[]='table.'.$id.'.absent';continue;}
 foreach(array_keys($template) as $key)if(!array_key_exists($key,$table['options']))$fail[]='table.'.$id.'.runtime.missing.'.$key;
 if(($table['options']['datatables_custom_commands']??null)!=='')$fail[]='table.'.$id.'.unsafe_commands';
 foreach(['data','visibility'] as $key)if($table[$key]!==$e[$key])$fail[]='table.'.$id.'.'.$key;
 foreach($e['options'] as $key=>$value)if($key!=='last_editor'&&$key!=='datatables_custom_commands'&&(!array_key_exists($key,$table['options'])||$table['options'][$key]!==$value))$fail[]='table.'.$id.'.options.'.$key;
}
echo json_encode(['ok'=>!$fail,'differences'=>$fail])."\n";exit($fail?1:0);
