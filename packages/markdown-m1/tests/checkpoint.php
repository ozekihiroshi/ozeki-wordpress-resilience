<?php
declare(strict_types=1);
require_once $argv[1].'/src/Store.php';
class MemoryS3 {
 public array $objects=[];public int $n=0;public ?string $failOn=null;
 function putObject($a){if(($this->failOn && str_ends_with($a['Key'],$this->failOn))||isset($this->objects[$a['Key']]))throw new RuntimeException('put denied');$r=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];$this->objects[$a['Key']]=$r;return $r;}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$r['VersionId']!==$a['VersionId'])throw new RuntimeException('wrong version');return $r;}
 function listObjectsV2($a){$keys=array_keys($this->objects);sort($keys);$out=[];foreach($keys as $k)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
function ok($v,$m){if(!$v)throw new RuntimeException($m);}
function rejects($fn){try{$fn();}catch(Throwable $e){return;}throw new RuntimeException('Expected rejection');}
function material($text,$slug){return ['source'=>$text,'row'=>['schema'=>'owr-md-history-1','sequence'=>0,'attributes'=>['title'=>$slug,'slug'=>$slug,'status'=>'publish','date'=>'2026-10-24 01:00:00','date_gmt'=>'2026-10-24 01:00:00','origin_id'=>1,'origin_url'=>'https://lost.invalid/'.$slug.'/']]];}
function add($store,$n,$asset,$text){$attrs=material($text,$asset)['row']['attributes'];$o=$store->prepare($asset,'operation-'.$n,$text,$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$n,'original'=>$o,'attributes'=>$attrs]);}
$s3=new MemoryS3();$store=new Owr\M1\Store($s3,['bucket'=>'test','prefix'=>'site/','retention_days'=>36]);
$initial=['a'=>material("# A\n```mermaid\ngraph LR; A-->B\n```\n$$ x^2 $$\n[B](https://lost.invalid/b/)",'a'),'b'=>material('[A](https://lost.invalid/a/)','b')];
$first=$store->createInitialSnapshot($initial);ok($first['through']===0&&$first['assets']===2,'initial');ok($store->createInitialSnapshot($initial)['unchanged'],'initial resume');
$changed=$initial;$changed['a']['source']='different';rejects(fn()=>$store->createInitialSnapshot($changed));
add($store,1,'a',"# A updated\n[B](https://lost.invalid/b/)");
$s3->failOn='assets/b/metadata.json';rejects(fn()=>$store->createCheckpoint());ok(count($store->checkpoints())===1,'partial snapshot not visible');$s3->failOn=null;
$cp=$store->createCheckpoint();ok($cp['through']===1,'resumed');ok($store->createCheckpoint()['unchanged'],'idempotent');
$manifest=$store->snapshot($cp['key']);ok($manifest['schema']===$store->snapshot($first['key'])['schema'],'common format');
// Remove EVERY preceding object, including initial snapshot and source originals.
$keep='site/'.dirname($cp['key']).'/';foreach(array_keys($s3->objects) as $key)if(!str_starts_with($key,$keep))unset($s3->objects[$key]);
$state=$store->recoveryState($cp['key']);ok($state['through']===1&&count($state['assets'])===2,'independent snapshot');
foreach($state['assets'] as $row){$store->get($row['original']['source']);$store->get($row['original']['metadata']);}
ok($store->get($state['assets']['b']['original']['source'])===$initial['b']['source'],'unchanged asset copied');
add($store,2,'b','B later');add($store,3,'c','C later');$state=$store->recoveryState($cp['key']);ok($state['through']===3&&count($state['assets'])===3,'snapshot plus tail');
ok($store->latestState()['through']===3,'next sequence survives pruning');
$saved=$s3->objects['site/history/00000000000000000002.json'];unset($s3->objects['site/history/00000000000000000002.json']);rejects(fn()=>$store->recoveryState($cp['key']));$s3->objects['site/history/00000000000000000002.json']=$saved;
$next=$store->createCheckpoint();$keep='site/'.dirname($next['key']).'/';foreach(array_keys($s3->objects) as $key)if(!str_starts_with($key,$keep))unset($s3->objects[$key]);
$final=$store->latestState();ok($final['through']===3&&count($final['assets'])===3,'second generation independent');
$selected=[];foreach($final['assets'] as $asset=>$row)$selected['snapshot-test-'.$asset]=[$row,$store->get($row['original']['source'])];
$ref=$final['assets']['a']['original']['source'];$s3->objects['site/'.$ref['key']]['Body']='changed';rejects(fn()=>$store->get($ref));
echo "PASS: common initial/Checkpoint format; complete raw files; partial-write resume; idempotence; all ancestor objects removed; tail replay; sequence after pruning; gap rejection; second independent generation; hash checks. Storage is an in-memory test double, not AWS.\n";
