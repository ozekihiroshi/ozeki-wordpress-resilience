<?php
require __DIR__.'/native-queue.php';
class VerificationS3 extends QueueS3 {
 public ?string $broken=null;public bool $unavailable=false;public array $reads=[];public int $historyPuts=0;
 function getObject($a){$this->reads[]=$a;$r=parent::getObject($a);if($this->broken&&str_contains($a['Key'],$this->broken)){
  if($this->unavailable)throw new RuntimeException('Trial fixed-version read failed');
  $r['Body'].='CORRUPTED-IN-TRANSIT';
 }return $r;}
 function putObject($a){if(str_contains($a['Key'],'/history/'))$this->historyPuts++;return parent::putObject($a);}
}
foreach(['source.json','metadata.json','/data/','/media/'] as $broken){
 $GLOBALS['opts']=[];$s3=new VerificationS3();$s3->fail=false;$s3->broken=$broken;
 $store=new Owr\M1\Store($s3,['bucket'=>'fixture','prefix'=>'verify/']);Owr\M1\Plugin::$store=$store;
 $attrs=['post_type'=>'owr_native','content_format'=>'native-state-json','origin_id'=>10,'media'=>[['files'=>['uploads/a.png'=>null]]]];
 $source='{"post_content":"Full original trial text"}';$resources=['uploads/a.png'=>['body'=>base64_encode('image original'),'type'=>'image/png']];
 $queue=new Owr\M1\CommentHistory();$queue->enqueue('trial',$source,$attrs,$resources);
 ok($s3->historyPuts===0&&!$store->history(),'Mismatch must not PUT formal history: '.$broken);
 $pending=get_option(Owr\M1\CommentHistory::PENDING);ok(count($pending)===1,'Pending retained');$entry=reset($pending);$op=$entry['operation'];
 $objects=$s3->objects;$s3->unavailable=true;
 try{$queue->resume();throw new LogicException('Expected read failure');}catch(RuntimeException $e){ok(str_contains($e->getMessage(),'read failed'),'Read failure propagated');}
 ok($s3->historyPuts===0&&$s3->objects===$objects,'Read failure leaves originals/history unchanged');
 $s3->broken=null;$s3->unavailable=false;$queue->resume();$history=$store->history();
 ok(count($history)===1&&!get_option(Owr\M1\CommentHistory::PENDING),'Resume confirms after verification');
 ok($history[0]['original']['operation']===$op,'Same operation resumed');
 foreach($s3->reads as $request)if(str_contains($request['Key'],'/originals/'))ok(!empty($request['VersionId']),'Fixed version used');
 foreach($objects as $key=>$v)ok($s3->objects[$key]===$v,'Existing original unchanged');
}
echo "PASS source/metadata/split-part/media hash mismatch and read failure prevent history PUT; pending retained; same operation resumes after verification; fixed versions and originals preserved\n";
