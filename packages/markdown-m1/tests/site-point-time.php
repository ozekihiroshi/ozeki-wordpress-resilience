<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Store.php';
require $argv[1].'/src/SiteSnapshot.php';
require $argv[1].'/src/NativeHistory.php';
function ok($v,$m){if(!$v)throw new RuntimeException($m);}
function reject($f){try{$f();}catch(RuntimeException $e){return;}throw new RuntimeException('Expected rejection');}
class PointS3 {
 public array $objects=[],$reads=[];
 function putObject($a){$r=['Body'=>$a['Body'],'VersionId'=>'v1'];$this->objects[$a['Key']]=$r;return $r;}
 function getObject($a){$this->reads[]=$a['Key'];return $this->objects[$a['Key']]??throw new RuntimeException('Missing object');}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&strcmp($k,$a['StartAfter']??'')>0)$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
$s=new PointS3();$store=new Owr\M1\Store($s,['bucket'=>'test','prefix'=>'test/']);$site=new Owr\M1\SiteSnapshot($store);
$tables=array_fill_keys(['posts','postmeta','terms','term_taxonomy','term_relationships','termmeta','comments','commentmeta'],[]);
$a=['origin_id'=>42,'post_type'=>'post','content_format'=>'wordpress-block-html','status'=>'publish','title'=>'Trial','slug'=>'trial','date'=>'2026-10-25 00:00:00','date_gmt'=>'2026-10-25 00:00:00','origin_url'=>'https://old.invalid/trial'];
foreach([1=>'Old full body',2=>'New full body'] as $n=>$body){$o=$store->prepare('article','op-'.$n,$body,$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$n,'original'=>$o,'attributes'=>$a]);}
$da=['origin_id'=>42,'post_type'=>'owr_native','content_format'=>'native-state-json'];$raw=Owr\M1\Store::json(['schema'=>'owr-native-state-1','id'=>42,'type'=>'post','deleted'=>true,'terms'=>[],'assigned'=>[]]);
$o=$store->prepare('article','delete',$raw,$da);$store->commit(['schema'=>'owr-md-history-1','sequence'=>3,'original'=>$o,'attributes'=>$da]);
$m=['through'=>0];$f=['content.json'=>Owr\M1\Store::json(['tables'=>$tables])];
$replay=new ReflectionMethod($site,'replay');$replay->setAccessible(true);
foreach([0,1,2,3] as $n){[$actual,$files]=$replay->invoke($site,$m,$f,$n);$d=json_decode($files['content.json'],true);ok($actual['through']===$n,'Exact boundary');ok(count($d['tables']['posts'])===(in_array($n,[1,2])?1:0),'Creation/deletion boundary');if(in_array($n,[1,2]))ok($d['tables']['posts'][0]['post_content']===($n===1?'Old full body':'New full body'),'Full body at selected point');}
reject(fn()=>$replay->invoke($site,['through'=>2],$f,1));reject(fn()=>$replay->invoke($site,$m,$f,4));
$saved=$s->objects;unset($s->objects['test/history/00000000000000000002.json']);reject(fn()=>$replay->invoke($site,$m,$f,3));$s->objects=$saved;
// Later corrupt records and missing later originals must not block an earlier point.
$s->objects['test/history/00000000000000000003.json']['Body']='invalid';unset($s->objects['test/'.$o['source']['key']]);$s->reads=[];
[$actual]=$replay->invoke($site,$m,$f,2);ok($actual['through']===2,'Later damage excluded');ok(!in_array('test/history/00000000000000000003.json',$s->reads,true),'No later history fetched');
unset($s->objects['test/originals/article/op-2/source.html']);reject(fn()=>$replay->invoke($site,$m,$f,2));
echo "PASS exact boundaries, full update, deletion, Checkpoint-only, incompatible Checkpoint, missing end/gap/resource, later records excluded. Memory S3 only.\n";
