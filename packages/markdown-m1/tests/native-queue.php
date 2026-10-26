<?php
namespace Owr\M1 {class Plugin {public static Store $store;function store(){return self::$store;}}}
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
$s3=new QueueS3();$store=new Owr\M1\Store($s3,['bucket'=>'trial','prefix'=>'native/']);Owr\M1\Plugin::$store=$store;
$attrs=['post_type'=>'owr_native','content_format'=>'native-state-json','origin_id'=>10,'media'=>[['files'=>['uploads/a.png'=>null]]]];$res=['uploads/a.png'=>['body'=>base64_encode('original bytes'),'type'=>'image/png']];
$q=new Owr\M1\CommentHistory();$q->enqueue('native-state-10','{"frozen":true}',$attrs,$res);ok(count($store->history())===0,'Failure excluded');ok(count(get_option(Owr\M1\CommentHistory::PENDING))===1,'Pending durable');$res['uploads/a.png']['body']=base64_encode('changed later');
$s3->fail=false;$s3->lost=true;$q->resume();$history=$store->history();ok(count($history)===1&&!get_option(Owr\M1\CommentHistory::PENDING),'Resume committed once');$ref=$history[0]['attributes']['media'][0]['files']['uploads/a.png'];ok($store->get($ref)==='original bytes','Frozen bytes');ok(str_ends_with($history[0]['original']['source']['key'],'source.json'),'JSON original');$q->resume();ok(count($store->history())===1,'No duplicate');
$res['uploads/a.png']['body']=base64_encode('original bytes');$q->enqueue('native-state-10','{"frozen":true}',$attrs,$res);ok(count($store->history())===1,'Unchanged native state not repeated');
$s3->readFail=true;$q->enqueue('native-state-10','{"changed":true}',$attrs,$res);ok(count(get_option(Owr\M1\CommentHistory::PENDING))===1,'Failed equality lookup preserves pending');
$s3->readFail=false;$q->resume();ok(count($store->history())===2&&!get_option(Owr\M1\CommentHistory::PENDING),'Changed native state resumes after read failure');
echo "PASS frozen resource failure, resume, lost response, same-state suppression and read-failure preservation\n";
}
