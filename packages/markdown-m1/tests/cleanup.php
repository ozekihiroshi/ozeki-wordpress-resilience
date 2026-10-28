<?php
require __DIR__.'/checkpoint.php';
class CleanupS3 extends MemoryS3 {
 public array $dates=[],$holds=[],$deleted=[];public ?int $failAfter=null;public bool $duplicate=false,$denyLockRead=false,$loseDeleteResponse=false;
 function putObject($a){$r=parent::putObject($a);$this->dates[$a['Key']]=time()-86400*100;return $r;}
 function listObjectVersions($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix']))$out[]=['Key'=>$k,'VersionId'=>$v['VersionId'],'LastModified'=>new DateTimeImmutable('@'.$this->dates[$k])];if($this->duplicate&&$out)$out[]=$out[0];return ['Versions'=>$out];}
 function headObject($a){$this->getObject($a);return $this->holds[$a['Key']]??[];}
 function getObjectLockConfiguration($a){return ['ObjectLockConfiguration'=>['ObjectLockEnabled'=>'Enabled']];}
 function getObjectRetention($a){if($this->denyLockRead)throw new RuntimeException('AccessDenied');return ['Retention'=>['RetainUntilDate'=>$this->holds[$a['Key']]['ObjectLockRetainUntilDate']??null]];}
 function getObjectLegalHold($a){return ['LegalHold'=>['Status'=>$this->holds[$a['Key']]['ObjectLockLegalHoldStatus']??'OFF']];}
 function deleteObject($a){ok(isset($a['VersionId'])&&!isset($a['BypassGovernanceRetention']),'exact version, no bypass');if($this->failAfter!==null&&count($this->deleted)>=$this->failAfter)throw new RuntimeException('simulated interruption');$this->getObject($a);unset($this->objects[$a['Key']]);$this->deleted[]=$a;if($this->loseDeleteResponse){$this->loseDeleteResponse=false;throw new RuntimeException('lost delete response');}return [];}
}
function cleanupFixture(){
 $s=new CleanupS3();$store=new OzekiResilience\M1\Store($s,['bucket'=>'test','prefix'=>'site/']);
 $first=$store->createInitialSnapshot(['cleanup-a'=>material('A initial','cleanup-a'),'cleanup-b'=>material('B initial','cleanup-b')]);
 add($store,1,'cleanup-a','A checkpoint');$cp=$store->createCheckpoint();
 add($store,2,'cleanup-b','B tail');
 $s->putObject(['Key'=>'site/other/keep.txt','Body'=>'unrelated']);
 return [$s,$store,$first,$cp];
}
[$s,$store,$first,$cp]=cleanupFixture();$cutoff=time();
$p=$store->cleanupPlan($cutoff);ok(count($p['keep'])===1&&$p['keep'][0]===$cp['key'],'latest survives age0');ok(count($p['delete'])>0,'eligible assets');
$s->holds['site/'.$p['delete'][0]['key']]=['ObjectLockRetainUntilDate'=>new DateTimeImmutable('+1 day')];
$blocked=$store->cleanupPlan($cutoff);rejects(fn()=>$store->cleanup($cutoff,$blocked['hash']));ok(!$s->deleted,'lock prevents all deletes');
$s->holds=['site/'.$p['delete'][0]['key']=>['ObjectLockLegalHoldStatus'=>'ON']];$blocked=$store->cleanupPlan($cutoff);rejects(fn()=>$store->cleanup($cutoff,$blocked['hash']));$s->holds=[];
$p=$store->cleanupPlan($cutoff);add($store,3,'cleanup-a','A new tail');rejects(fn()=>$store->cleanup($cutoff,$p['hash']));ok(!$s->deleted,'stale preview rejected');
$p=$store->cleanupPlan($cutoff);$s->failAfter=2;$partial=$store->cleanup($cutoff,$p['hash']);ok(!$partial['ok']&&count($partial['deleted'])===2,'interruption visible');
$state=$store->latestState();foreach($state['assets'] as $r)$store->get($r['original']['source']);ok($state['through']===3,'recovery after partial delete');
$s->failAfter=null;$p=$store->cleanupPlan($cutoff);$done=$store->cleanup($cutoff,$p['hash']);ok($done['ok'],'resume from S3');
ok(isset($s->objects['site/other/keep.txt']),'unrelated preserved');ok(count($store->checkpoints())===1,'only latest baseline');
ok(!isset($s->objects['site/history/00000000000000000001.json']),'covered history removed');ok(isset($s->objects['site/history/00000000000000000002.json']),'tail retained');
$state=$store->latestState();ok($state['through']===3,'restore checkpoint plus tail');
$selected=[];foreach($state['assets'] as $id=>$row)$selected[$id]=[$row,$store->get($row['original']['source'])];
// No-op repeat, boundary (new objects retained), ambiguous versions, damaged tail.
$p=$store->cleanupPlan($cutoff);ok(!$p['delete'],'idempotent cleanup');
$s->duplicate=true;rejects(fn()=>$store->cleanupPlan($cutoff));$s->duplicate=false;
$saved=$s->objects['site/history/00000000000000000002.json'];unset($s->objects['site/history/00000000000000000002.json']);rejects(fn()=>$store->cleanupPlan($cutoff));$s->objects['site/history/00000000000000000002.json']=$saved;
[$fresh,$freshStore,$initial,$checkpoint]=cleanupFixture();$recent=$freshStore->cleanupPlan(time()-1);ok(count($recent['keep'])===2,'retention window keeps older snapshot and complete chain');
ok(!$recent['delete'],'no needed asset eligible');
[$denied,$deniedStore]=cleanupFixture();$denied->denyLockRead=true;rejects(fn()=>$deniedStore->cleanupPlan(time()));ok(!$denied->deleted,'missing inspection rights fail closed');
[$lost,$lostStore]=cleanupFixture();$p=$lostStore->cleanupPlan(time());$lost->loseDeleteResponse=true;$r=$lostStore->cleanup($p['cutoff'],$p['hash']);ok(!$r['ok']&&isset($r['uncertain']),'lost response explicit');$p=$lostStore->cleanupPlan(time());ok($lostStore->cleanup($p['cutoff'],$p['hash'])['ok'],'lost-response resume from inventory');ok($lostStore->latestState()['through']===2,'recoverable after lost response');
echo "PASS: latest baseline; window; complete tail; exact version deletion; no bypass; Object Lock; Legal Hold; stale plan; partial deletion recovery/resume; unrelated keys; repeat; duplicate versions; gap. In-memory S3 only.\n";
