<?php
require __DIR__.'/../src/RbrReconstructionConsole.php';
use Owr\RbrReconstructionConsole as C;
$d=sys_get_temp_dir().'/owr-console-'.bin2hex(random_bytes(8));mkdir($d);mkdir($d.'/inbox');$token=str_repeat('a',64);$input=['item_id'=>'test','token'=>$token];
function report($d,$token,$age=0,$approval='approved'){file_put_contents($d.'/report.json',json_encode(['schema'=>'owr-reconstruction-console-v1','updated_at'=>time()-$age,'items'=>[['item_id'=>'test','token'=>$token,'approval'=>$approval]]]));}
function reject($fn){try{$fn();}catch(Throwable){return;}throw new RuntimeException('Expected rejection');}
$item=['generation'=>['sha256'=>'g','locator'=>['version_id'=>'v1']],'q_sha256'=>'q'];
$history=['generations'=>[['state'=>'applied','generation'=>$item['generation'],'q_sha256'=>'q']]];
if(!C::matches($item,$history))throw new RuntimeException('Matching local generation rejected');
$wrong=$item;$wrong['q_sha256']='other';if(C::matches($wrong,$history))throw new RuntimeException('Different Q accepted');
$wrong=$item;$wrong['generation']['locator']['version_id']='v2';if(C::matches($wrong,$history))throw new RuntimeException('Different version accepted');
$history['generations'][0]['state']='stored';if(C::matches($item,$history))throw new RuntimeException('Pending generation accepted');
report($d,$token);$a=C::enqueue($d.'/report.json',$d.'/inbox',$input);$b=C::enqueue($d.'/report.json',$d.'/inbox',$input);if($a!==$b||count(glob($d.'/inbox/*'))!==1)throw new RuntimeException('Duplicate');
report($d,$token,100);reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',$input));
report($d,$token,0,'blocked');reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',$input));
report($d,$token);reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',['item_id'=>'../bad','token'=>$token]));
reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',['item_id'=>'test','token'=>str_repeat('b',64)]));
reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',$input+['command'=>'bad']));
$history['generations'][0]['state']='applied';
file_put_contents($d.'/report.json',json_encode(['schema'=>'owr-reconstruction-console-v1','updated_at'=>time(),'items'=>[array_merge($item,['item_id'=>'test','token'=>$token,'approval'=>'approved','require_local_match'=>true])]]));
reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',$input));
$badHistory=$history;$badHistory['generations'][0]['q_sha256']='other';
reject(fn()=>C::enqueue($d.'/report.json',$d.'/inbox',$input,$badHistory));
C::enqueue($d.'/report.json',$d.'/inbox',$input,$history);
foreach(glob($d.'/inbox/*') as $f)unlink($f);rmdir($d.'/inbox');unlink($d.'/report.json');rmdir($d);echo "PASS: queue replay, stale, blocked, traversal, token mismatch, unknown fields\n";
