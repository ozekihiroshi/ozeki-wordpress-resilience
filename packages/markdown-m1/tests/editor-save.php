<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Store.php';require $argv[1].'/src/Plugin.php';require $argv[1].'/src/CommentHistory.php';
function ok($v,$m){if(!$v)throw new RuntimeException($m);}
$a=['title'=>'Trial','status'=>'publish','slug'=>'trial','origin_id'=>37];
$r=['original'=>['source'=>['sha256'=>hash('sha256','body')]],'attributes'=>$a];
ok(OzekiResilience\M1\Plugin::sameConfirmedArticle($r,'body',$a),'Same confirmed body');
ok(!OzekiResilience\M1\Plugin::sameConfirmedArticle(null,'body',$a),'Never trust only local state');
ok(!OzekiResilience\M1\Plugin::sameConfirmedArticle($r,'changed',$a),'Changed body');
foreach(['title','status','slug','origin_id'] as $key){$b=$a;$b[$key]='changed';ok(!OzekiResilience\M1\Plugin::sameConfirmedArticle($r,'body',$b),'Changed '.$key);}
$attrs=['post_type'=>'owr_native','media'=>[['id'=>1,'files'=>['uploads/a.png'=>null]]]];
$resources=['uploads/a.png'=>['body'=>base64_encode('image')]];
$row=['original'=>['source'=>['sha256'=>hash('sha256','state')]],'attributes'=>$attrs];
$row['attributes']['media'][0]['files']['uploads/a.png']=['key'=>'old','version'=>'v1','sha256'=>hash('sha256','image')];
ok(OzekiResilience\M1\CommentHistory::sameNativeState($row,'state',$attrs,$resources),'Same image bytes despite different refs');
$resources['uploads/a.png']['body']=base64_encode('different');
ok(!OzekiResilience\M1\CommentHistory::sameNativeState($row,'state',$attrs,$resources),'Changed image kept');
ok(!OzekiResilience\M1\CommentHistory::sameNativeState($row,'changed',$attrs,$resources),'Changed taxonomy/state kept');
class WP_Error {function __construct(public $code,public $message){}}
function update_option(...$a){}
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
function wp_strip_all_tags($s){return strip_tags($s);}
function wp_die($e,$title,$args){ok($e instanceof WP_Error&&$e->code==='ozeki_resilience_save_failed','Structured error code');ok(str_contains($e->message,'specific reason'),'Reason retained');ok($args['response']===409,'Conflict status');throw new LogicException('captured');}
$m=new ReflectionMethod(OzekiResilience\M1\Plugin::class,'stop');$m->setAccessible(true);
try{$m->invoke(new OzekiResilience\M1\Plugin(),new RuntimeException('specific reason'));throw new RuntimeException('Expected stop');}catch(LogicException $e){ok($e->getMessage()==='captured','Error handler called');}
echo "PASS confirmed-body and media/state equality; changed/unconfirmed data retained; editor error reason.\n";
