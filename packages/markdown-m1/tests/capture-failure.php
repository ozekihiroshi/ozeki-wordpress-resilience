<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/save-status.php';
require_once $argv[1].'/src/CommentHistory.php';
$options=[];$failWrite=false;
function update_option($k,$v,$autoload=false){global $options,$failWrite;if($failWrite)return false;$options[$k]=$v;return true;}
function get_option($k,$default=false){global $options;return $options[$k]??$default;}
use Owr\M1\{SaveFailure,CommentHistory,Plugin};
$failure=new RuntimeException('capture <failed>');
try{SaveFailure::run('Test capture',fn()=>throw $failure);throw new Exception('not stopped');}catch(RuntimeException $e){ok($e===$failure,'original error preserved');}
$record=get_option(SaveFailure::OPTION);ok($record['context']==='Test capture','failure retained');
SaveFailure::run('Unrelated success',fn()=>true);ok(get_option(SaveFailure::OPTION)===$record,'success cannot clear unrelated failure');
try{(new CommentHistory())->enqueue('test',str_repeat('x',5*1024*1024+1),[]);throw new Exception('not stopped');}catch(RuntimeException $e){ok(str_contains($e->getMessage(),'5 MiB'),'size rejected before queue');}
ok(!get_option(CommentHistory::PENDING),'failure not a pending payload');
ok(get_option(SaveFailure::OPTION)['context']==='Shared queue registration','prequeue captured');
$queue=['detail'=>['attributes'=>['post_type'=>'owr_native']],'other'=>['attributes'=>['post_type'=>'owr_form']]];
ob_start();Plugin::renderSaveStatus($h,'',['record'=>$h[0]],$queue,'','',true,$record);$html=ob_get_clean();
ok(str_contains($html,'not checked by this display')&&str_contains($html,'Pending article body: 1; pending article details (images/categories/tags/deletion): 1; other shared operations: 1'),'separate confirmation and pending scopes');
ok(str_contains($html,'capture &lt;failed&gt;')&&!str_contains($html,'capture <failed>')&&str_contains($html,'Queue count zero does not resolve it'),'escaped historical diagnostic');
$failWrite=true;try{SaveFailure::run('Failing diagnostic',fn()=>throw $failure);}catch(RuntimeException $e){ok($e===$failure,'logging failure preserves original');}
echo "PASS prequeue failure, original exception, no synthetic pending payload, unrelated-success retention, status distinction and diagnostic-write failure\n";
