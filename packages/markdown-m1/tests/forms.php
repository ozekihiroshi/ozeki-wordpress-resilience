<?php
declare(strict_types=1);
require_once $argv[1].'/src/Store.php';
require_once $argv[1].'/src/FormHistory.php';
class CommentMemoryS3 {
 public array $objects=[];public int $n=0;public bool $fail=false;
 function putObject($a){if($this->fail||isset($this->objects[$a['Key']]))throw new RuntimeException('denied');return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
function ok($b,$m){if(!$b)throw new RuntimeException($m);}

$s3=new CommentMemoryS3();$store=new Owr\M1\Store($s3,['bucket'=>'test','prefix'=>'forms/']);
$d=['tables'=>['posts'=>[],'postmeta'=>[],'terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[]]];
$attrs=['post_type'=>'owr_form','content_format'=>'form-json','origin_id'=>17,'dependencies'=>[]];
$item=['post'=>['ID'=>'17','post_type'=>'wpcf7_contact_form','post_title'=>'Form'],'meta'=>[['meta_key'=>'_form','meta_value'=>'[text* name]']],'channels'=>[]];
$raw=Owr\M1\Store::json(['schema'=>'owr-form-1','items'=>[$item]]);
$o=$store->prepare('form-17','op1',$raw,$attrs);ok(str_ends_with($o['source']['key'],'source.json'),'complete JSON');$store->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$attrs]);
Owr\M1\FormHistory::replay($d,$raw,$attrs);Owr\M1\FormHistory::replay($d,$raw,$attrs);ok(count($d['tables']['posts'])===1&&count($d['tables']['postmeta'])===1,'idempotent form replay');
$receipt=['post'=>['ID'=>'18','post_type'=>'flamingo_inbound','post_title'=>'Inquiry'],'meta'=>[['meta_key'=>'_field_message','meta_value'=>'Complete inquiry']],'channels'=>[['term_id'=>'3','name'=>'Form','slug'=>'form','term_group'=>'0','term_taxonomy_id'=>'4','taxonomy'=>'flamingo_inbound_channel','description'=>'','parent'=>'0']]];
$attrs['origin_id']=18;$raw=Owr\M1\Store::json(['schema'=>'owr-form-1','items'=>[$item,$receipt]]);
Owr\M1\FormHistory::replay($d,$raw,$attrs);Owr\M1\FormHistory::replay($d,$raw,$attrs);ok(count($d['tables']['posts'])===2&&count($d['tables']['term_relationships'])===1&&$d['tables']['term_taxonomy'][0]['count']==='1','receipt and channel stable');
$bad=$attrs;$bad['origin_id']=19;try{Owr\M1\FormHistory::replay($d,$raw,$bad);throw new LogicException('accepted bad identity');}catch(RuntimeException $e){}
$s3->fail=true;try{$store->prepare('form-18','failure',$raw,$attrs);throw new LogicException('expected failure');}catch(RuntimeException $e){}ok(count($store->history())===1,'failure excluded');
echo "PASS complete form/inquiry JSON, idempotent replay, channels, identity rejection, failed original exclusion.\n";
