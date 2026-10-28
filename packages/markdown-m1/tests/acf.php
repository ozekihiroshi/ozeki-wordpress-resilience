<?php
declare(strict_types=1);
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Store.php';
require $argv[1].'/src/SiteSnapshot.php';
require $argv[1].'/src/FormHistory.php';
require $argv[1].'/src/MemberHistory.php';
require $argv[1].'/src/TableHistory.php';
require $argv[1].'/src/NativeHistory.php';
use Owr\M1\{Store,SiteSnapshot,AcfHistory,RecoveryRules,AssetFormat};
function maybe_serialize($v){return is_array($v)||is_string($v)&&preg_match('/^(?:a|s|i|b|d|O):|^N;/',$v)?serialize($v):$v;}
function ok($v,$m){if(!$v)throw new RuntimeException($m);}
class AcfS3 {public array $objects=[];public bool $corrupt=false;
 function putObject($a){$this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>hash('sha256',$a['Body'])];return $this->objects[$a['Key']];}
 function getObject($a){$v=$this->objects[$a['Key']]??throw new RuntimeException('missing');if(isset($a['VersionId'])&&$a['VersionId']!==$v['VersionId'])throw new RuntimeException('version');if($this->corrupt&&str_contains($a['Key'],'/data/'))$v['Body'].='corrupt';return $v;}
 function listObjectsV2($a){$v=[];foreach($this->objects as $k=>$x)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$v[]=['Key'=>$k];return ['Contents'=>$v];}
}
$v=['schema'=>'owr-acf-1','id'=>10,'type'=>'post','version'=>'6.8.10',
 'acf_values'=>['caption'=>["日本語\n原本"],'choices'=>[['one','two']],'opaque'=>['untouched']],
 'acf_definitions'=>[['key'=>'group_trial','title'=>'Trial','location'=>[[['param'=>'post_type','operator'=>'==','value'=>'post']]],'fields'=>[
 ['key'=>'field_caption','name'=>'caption','label'=>'Caption','type'=>'text','unknown_setting'=>'preserved'],
 ['key'=>'field_choices','name'=>'choices','type'=>'checkbox','choices'=>['one'=>'一','two'=>'二']],
 ['key'=>'field_opaque','name'=>'opaque','type'=>'third_party']]]],
 'acf_references'=>['caption'=>'field_caption','choices'=>'field_choices','opaque'=>'field_opaque'],
 'raw_meta'=>['unknown'=>['keep these bytes']]];
$raw=Store::json($v);$layout=AssetFormat::split($v);
ok(count($layout['files'])===3,'Values, definitions, references are separate files');
ok(AssetFormat::join($layout,$layout['files'])===$v,'Lossless separated original');
$s3=new AcfS3();$s=new Store($s3,['bucket'=>'test','prefix'=>'acf/']);$a=['post_type'=>'owr_acf','content_format'=>'acf-json','origin_id'=>10];
$o=$s->prepare('acf-10','one',$raw,$a);$s3->corrupt=true;
try{$s->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$a]);throw new LogicException('corruption committed');}catch(RuntimeException $e){}
ok(!$s->history(),'Failed fixed-version comparison cannot confirm');$s3->corrupt=false;
$s->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$a]);ok($s->originalSource($o)===$raw,'Exact complete original');
$d=['tables'=>['posts'=>[['ID'=>'10','post_type'=>'post']],'postmeta'=>[],'commentmeta'=>[],'termmeta'=>[]],'options'=>[]];
AcfHistory::replay($d,$raw,$a);$unchanged=Store::json($d);$project=RecoveryRules::project($d,[]);
ok(Store::json($d)===$unchanged,'Projection never rewrites preserved unknowns');
$meta=array_column($project['data']['tables']['postmeta'],'meta_value','meta_key');
ok($meta['caption']==="日本語\n原本"&&$meta['_caption']==='field_caption','Value and field-key reference');
ok(unserialize($meta['choices'])===['one','two'],'Ordered selection');
ok(!isset($meta['opaque'])&&count($project['report']['not_applied'])>=2,'Unknown type/setting reported, withheld');
// WordPress stores serialization-shaped strings in an outer string envelope.
foreach(['plain Japanese 日本語','a:0:{}','s:3:"abc";','b:0;','N;'] as $literal){
 $case=json_decode($raw,true);$case['acf_values']['caption']=[$literal];
 AcfHistory::replay($d,Store::json($case),$a);$m=AcfHistory::project($d)['meta'];
 $stored=array_column($m,'meta_value','meta_key')['caption'];
 $read=$stored===$literal?$stored:unserialize($stored,['allowed_classes'=>false]);
 ok(is_string($read)&&$read===$literal,'Literal text survives metadata decode');
 if($literal==='a:0:{}')ok($stored==='s:6:"a:0:{}";','Serialization-shaped text must be wrapped');
}
$case=json_decode($raw,true);$case['acf_definitions'][0]['fields'][0]['name']='sub-title';
$case['acf_values']['sub-title']=$case['acf_values']['caption'];unset($case['acf_values']['caption']);
$case['acf_references']['sub-title']=$case['acf_references']['caption'];unset($case['acf_references']['caption']);
AcfHistory::replay($d,Store::json($case),$a);$m=array_column(AcfHistory::project($d)['meta'],'meta_value','meta_key');
ok($m['sub-title']==="日本語\n原本"&&$m['_sub-title']==='field_caption','Hyphenated name and reference preserved');
AcfHistory::replay($d,$raw,$a);
$v['acf_values']['caption']=['updated'];AcfHistory::replay($d,Store::json($v),$a);
ok(AcfHistory::project($d)['meta'][0]['meta_value']==='updated','Complete latest field state');
unset($v['acf_values']['caption']);AcfHistory::replay($d,Store::json($v),$a);
ok(!in_array('caption',array_column(AcfHistory::project($d)['meta'],'meta_key'),true),'Removed value not resurrected');
$v['acf_values']['caption']=[['invalid'=>'scalar']];AcfHistory::replay($d,Store::json($v),$a);
try{AcfHistory::project($d);throw new LogicException('invalid scalar accepted');}catch(RuntimeException $e){}
unset($v['acf_values']['caption']);AcfHistory::replay($d,Store::json($v),$a);
$site=new SiteSnapshot($s);$base=$site->save(['content.json'=>Store::json($d)],['schema'=>'owr-site-snapshot-1','through'=>1]);$cp=$site->checkpoint($base['manifest']);
$prefix='acf/'.dirname($cp['manifest']['key']).'/';foreach(array_keys($s3->objects) as $key)if(!str_starts_with($key,$prefix))unset($s3->objects[$key]);
[$m,$files]=$site->load($cp['manifest']);$loaded=json_decode($files['content.json'],true);
ok($loaded['acf']['posts']['10']['raw_meta']['unknown']===['keep these bytes'],'Independent Checkpoint preserves unknown original');
echo "PASS ACF separated originals, comparison failure, history, projection, removed value, independent Checkpoint (simulated S3).\n";
