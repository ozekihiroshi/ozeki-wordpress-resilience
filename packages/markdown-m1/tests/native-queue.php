<?php
namespace OzekiResilience\M1 {class Plugin {public static Store $store;function store(){return self::$store;}}}
namespace {
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');

require $argv[1].'/src/Store.php';require $argv[1].'/src/SiteSnapshot.php';require $argv[1].'/src/CommentHistory.php';
class QueueS3 {public array $objects=[];public bool $fail=true;public bool $lost=false;public bool $readFail=false;public int $n=0;
function putObject($a){if($this->fail||isset($this->objects[$a['Key']]))throw new RuntimeException('denied');$r=$this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];if($this->lost){$this->lost=false;throw new RuntimeException('lost response');}return $r;}
function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing');if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
function listObjectsV2($a){if($this->readFail)throw new RuntimeException('listing denied');$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}}
class DB {public string $prefix='trial_';function prepare($q,...$a){return $q;}function get_var($q){return 1;}}
$GLOBALS['wpdb']=new DB();$GLOBALS['opts']=[];
function get_option($k,$d=false){return $GLOBALS['opts'][$k]??$d;}
function update_option($k,$v,$a=null){$old=get_option($k);$GLOBALS['opts'][$k]=$v;return $old!==$v;}
function delete_option($k){unset($GLOBALS['opts'][$k]);return true;}
function wp_generate_uuid4(){static $n=0;return 'frozen-operation-'.++$n;}
function ok($x,$m){if(!$x)throw new RuntimeException($m);}
$s3=new QueueS3();$store=new OzekiResilience\M1\Store($s3,['bucket'=>'trial','prefix'=>'native/']);OzekiResilience\M1\Plugin::$store=$store;
$attrs=['post_type'=>'owr_native','content_format'=>'native-state-json','origin_id'=>10,'media'=>[['files'=>['uploads/a.png'=>null]]]];$res=['uploads/a.png'=>['body'=>base64_encode('original bytes'),'type'=>'image/png']];
$q=new OzekiResilience\M1\CommentHistory();$q->enqueue('native-state-10','{"frozen":true}',$attrs,$res);ok(count($store->history())===0,'Failure excluded');ok(count(get_option(OzekiResilience\M1\CommentHistory::PENDING))===1,'Pending durable');$res['uploads/a.png']['body']=base64_encode('changed later');
$s3->fail=false;$s3->lost=true;$q->resume();$history=$store->history();ok(count($history)===1&&!get_option(OzekiResilience\M1\CommentHistory::PENDING),'Resume committed once');$ref=$history[0]['attributes']['media'][0]['files']['uploads/a.png'];ok($store->get($ref)==='original bytes','Frozen bytes');ok(str_ends_with($history[0]['original']['source']['key'],'source.json'),'JSON original');$q->resume();ok(count($store->history())===1,'No duplicate');
$res['uploads/a.png']['body']=base64_encode('original bytes');$q->enqueue('native-state-10','{"frozen":true}',$attrs,$res);ok(count($store->history())===1,'Unchanged native state not repeated');
$s3->readFail=true;$q->enqueue('native-state-10','{"changed":true}',$attrs,$res);ok(count(get_option(OzekiResilience\M1\CommentHistory::PENDING))===1,'Failed equality lookup preserves pending');
$s3->readFail=false;$q->resume();ok(count($store->history())===2&&!get_option(OzekiResilience\M1\CommentHistory::PENDING),'Changed native state resumes after read failure');
echo "PASS frozen resource failure, resume, lost response, same-state suppression and read-failure preservation\n";

// Definition capture is ordered by the shared queue lock and frozen before any retry.
class DefinitionLockDB extends DB {public bool $locked=false;function get_var($q){if(str_contains($q,'GET_LOCK'))$this->locked=true;if(str_contains($q,'RELEASE_LOCK'))$this->locked=false;return 1;}}
$GLOBALS['wpdb']=new DefinitionLockDB();$GLOBALS['opts']=[];
$s3=new QueueS3();$store=new OzekiResilience\M1\Store($s3,['bucket'=>'trial','prefix'=>'definition-queue/']);OzekiResilience\M1\Plugin::$store=$store;
$calls=0;$current='{"schema":"owr-acf-definitions-1","acf_definitions":[]}';
$capture=function()use(&$calls,&$current){ok($GLOBALS['wpdb']->locked,'Capture inside writer lock');$calls++;return $current;};
$attrs=['post_type'=>'owr_acf','content_format'=>'acf-json','origin_id'=>0];
$q->enqueueCurrent('acf-definitions',$capture,$attrs);
ok($calls===1&&!$GLOBALS['wpdb']->locked&&count(get_option(OzekiResilience\M1\CommentHistory::PENDING))===1,'Failed definition save remains frozen and unlocks');
$frozen=$current;$current='{"changed":"after failure"}';$s3->fail=false;$q->resume();
$history=$store->history();ok($calls===1&&$store->originalSource($history[0]['original'])===$frozen,'Resume uses original definitions without recapture');
$current=$frozen;$q->enqueueCurrent('acf-definitions',$capture,$attrs);ok(count($store->history())===1,'Duplicate definition state suppressed');
try{$q->enqueueCurrent('acf-definitions',function(){throw new RuntimeException('capture failed');},$attrs);throw new LogicException('capture accepted');}catch(RuntimeException $e){}
ok(!$GLOBALS['wpdb']->locked&&!get_option(OzekiResilience\M1\CommentHistory::PENDING),'Capture failure unlocks without fabricated pending payload');
echo "PASS definition capture lock, frozen retry, deduplication and capture-failure boundary\n";
}
