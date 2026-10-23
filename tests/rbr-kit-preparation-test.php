<?php
require __DIR__.'/../src/RbrReconstructionConsole.php';require __DIR__.'/../src/RbrKitPreparation.php';
use Owr\RbrKitPreparation as P;
$d=sys_get_temp_dir().'/owr-preparation-'.bin2hex(random_bytes(8));mkdir($d);mkdir($d.'/inbox');
$h=['generations'=>[['operation'=>'op','sequence'=>1,'state'=>'applied','generation'=>['sha256'=>str_repeat('a',64)],'expected_ref'=>['sha256'=>str_repeat('b',64)]]]];
$r=['schema'=>'owr-reconstruction-console-v1','updated_at'=>time(),'profile_sha256'=>str_repeat('c',64),'items'=>[]];
function saveReport(){global $r,$d;file_put_contents($d.'/report',json_encode($r));}
function reject($f){try{$f();}catch(Throwable){return;}throw new Exception('Expected refusal');}
saveReport();$req=['operation'=>'op','attempt'=>0];$a=P::request($d.'/report',$d.'/inbox',$req,$h);$b=P::request($d.'/report',$d.'/inbox',$req,$h);assert($a===$b);
reject(fn()=>P::request($d.'/report',$d.'/inbox',['operation'=>'other','attempt'=>0],$h));
$r['updated_at']=time()-100;saveReport();reject(fn()=>P::request($d.'/report',$d.'/inbox',$req,$h));
$r['updated_at']=time();$r['items']=[['job_id'=>$a['job_id'],'state'=>'running','attempt'=>0]];saveReport();reject(fn()=>P::request($d.'/report',$d.'/inbox',['operation'=>'op','attempt'=>1],$h));
$r['items'][0]['state']='failed';saveReport();$resume=P::request($d.'/report',$d.'/inbox',['operation'=>'op','attempt'=>1],$h);if($resume['job_id']!==$a['job_id'])throw new Exception('Different job on resume');
$r['items'][0]['state']='blocked';saveReport();reject(fn()=>P::request($d.'/report',$d.'/inbox',['operation'=>'op','attempt'=>1],$h));
echo "Preparation PHP contracts PASS\n";
