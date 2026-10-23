<?php
require __DIR__.'/../src/SiteMaterialsEditor.php';require __DIR__.'/../src/SiteReconstructionAdmin.php';
use Owr\SiteReconstructionAdmin as A;
$d=sys_get_temp_dir().'/owr-material-recovery-'.bin2hex(random_bytes(8));mkdir($d);mkdir($d.'/requests');
$v=['schema'=>'owr-site-reconstruction-v1','updated_at'=>time(),'profile'=>str_repeat('a',64),'items'=>[['id'=>str_repeat('b',64),'q'=>str_repeat('c',64),'eligible'=>true]],'jobs'=>[]];
function report(){global $d,$v;file_put_contents($d.'/status.json',json_encode($v));}
function denied($f){try{$f();}catch(Throwable){return;}throw new Exception('Expected rejection');}
report();$q=['generation'=>str_repeat('b',64),'q'=>str_repeat('c',64),'profile'=>str_repeat('a',64)];
$a=A::request($d,$q);$b=A::request($d,$q);if($a!==$b||count(glob($d.'/requests/*.json'))!==1)throw new Exception('Duplicate');
$reordered=['profile'=>$q['profile'],'generation'=>$q['generation'],'q'=>$q['q']];if(A::request($d,$reordered)!==$a)throw new Exception('Field order changed identity');
$before=file_get_contents($d.'/status.json');A::status($d);if($before!==file_get_contents($d.'/status.json'))throw new Exception('Read mutation');
denied(fn()=>A::request($d,array_replace($q,['q'=>str_repeat('d',64)])));
$v['updated_at']=time()-121;report();denied(fn()=>A::request($d,$q));
$v['updated_at']=time();$v['items'][0]['eligible']=false;report();denied(fn()=>A::request($d,$q));
$v['schema']='owr-reconstruction-console-v1';report();denied(fn()=>A::status($d));
echo "Multi-material recovery PHP contracts PASS\n";
