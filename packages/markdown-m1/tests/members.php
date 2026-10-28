<?php
// Standalone WordPress API fixture for guarded product includes.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require_once __DIR__.'/../src/MemberHistory.php';
use OzekiResilience\M1\MemberHistory;
function must($b,$m){if(!$b)throw new RuntimeException($m);}
function reject($f){try{$f();}catch(RuntimeException $e){return;}throw new RuntimeException('Expected rejection');}
$d=['membership'=>['users'=>[],'settings'=>[]],'tables'=>['postmeta'=>[]]];
$attrs=['origin_id'=>12,'member_version'=>'3.5.8.1'];
$apply=function($kind,$value)use(&$d,$attrs){MemberHistory::replay($d,json_encode(['schema'=>'owr-member-1','kind'=>$kind,'id'=>12,'value'=>$value]),$attrs);};
$apply('restriction','1');$apply('restriction','0');$apply('restriction','2');
must(count($d['tables']['postmeta'])===1&&$d['tables']['postmeta'][0]['meta_value']==='2','Latest full restriction replaces earlier state');
$apply('restriction','');must(!$d['tables']['postmeta'],'Deleted restriction uses configured default');
reject(fn()=>$apply('restriction','99'));
$apply('user',['user'=>['ID'=>'12'],'meta'=>[]]);must(isset($d['membership']['users'][12]),'User stored');
$apply('user',null);must(!$d['membership']['users'],'Tombstone removes member');
reject(fn()=>MemberHistory::replay($d,'{"schema":"owr-member-1","kind":"user","id":13,"value":null}',$attrs));
$none=[];reject(function()use(&$none,$attrs){MemberHistory::replay($none,'{"schema":"owr-member-1","kind":"user","id":12,"value":null}',$attrs);});
echo "membership replay checks PASS\n";
