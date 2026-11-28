<?php
namespace OzekiResilience\M1 {
require_once '/tmp/product/src/Store.php';
require_once '/tmp/product/src/CommentHistory.php';
require_once '/tmp/product/src/FormHistory.php';
require_once '/tmp/product/src/FlamingoReconstruction.php';
class FixtureObjects {
 function path($key){if(!is_dir('/tmp/receipt-objects'))mkdir('/tmp/receipt-objects',0777);return '/tmp/receipt-objects/'.hash('sha256',$key).'.json';}
 function getObject($a){$p=$this->path($a['Key']);if(!is_file($p))throw new \RuntimeException('missing',404);$r=json_decode(file_get_contents($p),true);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new \RuntimeException('wrong version');return $r;}
 function putObject($a){$p=$this->path($a['Key']);if(is_file($p))throw new \RuntimeException('exists');if(is_file('/tmp/deny-writes'))throw new \RuntimeException('fixture write outage');$r=['Key'=>$a['Key'],'Body'=>$a['Body'],'VersionId'=>hash('sha256',$a['Body'])];file_put_contents($p,json_encode($r));chmod($p,0666);if(str_contains($a['Key'],'/history/')&&is_file('/tmp/lose-response')){unlink('/tmp/lose-response');throw new \RuntimeException('fixture lost commit response');}return $r;}
 function listObjectsV2($a){$out=[];foreach(glob('/tmp/receipt-objects/*.json') as $p){$r=json_decode(file_get_contents($p),true);if(str_starts_with($r['Key'],$a['Prefix'])&&$r['Key']>($a['StartAfter']??''))$out[]=['Key'=>$r['Key']];}usort($out,fn($x,$y)=>strcmp($x['Key'],$y['Key']));return ['Contents'=>$out];}
}
class Plugin {function config(){return ['protect'=>get_option('fixture_protect',false)];} function store(){return new Store(new FixtureObjects(),['bucket'=>'fixture','prefix'=>'inputs/']);}}
add_action('plugins_loaded',function(){(new FormHistory())->boot();});
}
namespace {
add_filter('pre_wp_mail',fn()=>true,PHP_INT_MAX);
// Deliberate process interruption at the end of Flamingo's argument filter.
add_filter('flamingo_add_inbound',function($a){if(is_file('/tmp/interrupt-registration'))exit('fixture interruption before registration');return $a;},PHP_INT_MAX);
}
