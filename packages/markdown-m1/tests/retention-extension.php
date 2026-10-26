<?php
require_once $argv[1].'/src/Store.php';require_once $argv[1].'/src/SiteSnapshot.php';
require_once __DIR__.'/retention-memory.php';
use Owr\M1\{Store,SiteSnapshot};
function checkRetention($v,$m){if(!$v)throw new RuntimeException($m);}
function retentionFailure($f,$text){try{$f();}catch(RuntimeException $e){checkRetention(str_contains($e->getMessage(),$text),'Wrong failure: '.$e->getMessage());return;}throw new RuntimeException('Expected failure: '.$text);}
class RetentionFixture {
 use RetentionMemory {getObjectRetention as readRetention;putObjectRetention as extendRetention;}
 public array $objects=[],$puts=[];public int $n=0;public string $fault='';
 function putObject($a){$this->puts[]=$a['Key'];if(isset($this->objects[$a['Key']]))throw new RuntimeException('exists');$this->rememberRetention($a);return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('wrong version');return $r;}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}
 function getObjectRetention($a){if($this->fault==='read')throw new RuntimeException('Denied retention read');return $this->readRetention($a);}
 function putObjectRetention($a){if($this->fault==='extend')throw new RuntimeException('Denied extension');if($this->fault==='ineffective')return [];return $this->extendRetention($a);}
 function age(){foreach($this->retentions as &$r)$r['RetainUntilDate']=new DateTimeImmutable('-1 day');}
}
function retentionFixture(){ $s=new RetentionFixture();return [$s,new Store($s,['bucket'=>'fixture','prefix'=>'site/','retention_days'=>2,'cleanup_keep_days'=>3])]; }
foreach(['read','extend','ineffective'] as $fault){
 [$s,$st]=retentionFixture();$o=$st->prepare('asset','one','raw',['title'=>'test']);$image=$st->put('media/image.png','image','image/png');$s->age();$s->fault=$fault;
 $record=['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>['media'=>[['files'=>[$image]]]]];
 retentionFailure(fn()=>$st->commit($record),$fault==='read'?'Denied retention read':($fault==='extend'?'Denied extension':'shorter than required'));
 checkRetention(!isset($s->objects['site/history/00000000000000000001.json']),'No formal history on retention failure');
 $before=$s->objects;$s->fault='';$st->commit($record);foreach($before as $key=>$v)checkRetention($s->objects[$key]===$v,'Old bytes and fixed versions unchanged');
 foreach($s->retentions as $ret)checkRetention($ret['RetainUntilDate']->getTimestamp()>=time()+2*86400,'Originals, media and history cover optional lock window');
}
[$s,$st]=retentionFixture();$r=$st->put('reused','same','text/plain');$s->retentions['site/reused']=['Mode'=>'COMPLIANCE','RetainUntilDate'=>new DateTimeImmutable('+1 day')];
$same=$st->put('reused','same','text/plain',$st->requiredRetentionUntil());checkRetention($r===$same,'Reuse keeps fixed version');checkRetention($s->retentions['site/reused']['Mode']==='COMPLIANCE','Keep compliance mode');
$extensions=count($s->extensions);$st->ensureRetention($r,gmdate('c',time()+86400));checkRetention(count($s->extensions)===$extensions,'Never shorten sufficient protection');
retentionFailure(fn()=>$st->assertRetentionWindow(gmdate('c',time()+2*86400-1)),'window expired');
[$nestedS,$nestedStore]=retentionFixture();$file=$nestedStore->put('files/inside.png','nested image','image/png');$attrs=['content_format'=>'form-json'];
$original=$nestedStore->prepare('form','nested',Store::json(['attachment'=>$file]),$attrs);$nestedS->age();
$nestedStore->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$original,'attributes'=>$attrs]);
checkRetention($nestedS->retentions['site/files/inside.png']['RetainUntilDate']->getTimestamp()>=time()+2*86400,'References in reassembled adapter source protected');
$m=['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial'];$files=['content.json'=>'{}','uploads/image.png'=>'image'];
foreach(['initial','checkpoint'] as $kind){
 [$s,$st]=retentionFixture();$site=new SiteSnapshot($st);
 if($kind==='checkpoint')$base=$site->save($files,$m);
 $s->fault='read';$s->puts=[];
 retentionFailure(fn()=>$kind==='initial'?$site->save($files,$m):$site->checkpoint($base['manifest']),'Denied retention read');
 foreach($s->puts as $key)checkRetention(!str_ends_with($key,'/manifest.json'),'No manifest after failed protection check');
 $s->fault='';$point=$kind==='initial'?$site->save($files,$m):$site->checkpoint($base['manifest']);
 checkRetention(isset($point['manifest']),'Retry succeeds');
}
[$s,$st]=retentionFixture();$site=new SiteSnapshot($st);$old=$site->save($files,$m);$m['through']=1;$latest=$site->save($files,$m);
$o=$st->prepare('asset','tail','later',[]);$st->commit(['schema'=>'owr-md-history-1','sequence'=>2,'original'=>$o,'attributes'=>[]]);
$s->age();$before=$s->objects;$s->fault='extend';retentionFailure(fn()=>$st->renewLatestSiteRetention(),'Denied extension');
$s->fault='';$renewed=$st->renewLatestSiteRetention();checkRetention($renewed['through']===2&&$renewed['checkpoint_through']===1,'Latest plus tail');
checkRetention($s->objects===$before,'Renewal changes no content or references');
checkRetention($s->retentions['site/'.$old['manifest']['key']]['RetainUntilDate']->getTimestamp()<time(),'Older unused baseline not extended');
checkRetention($s->retentions['site/'.$latest['manifest']['key']]['RetainUntilDate']->getTimestamp()>time()+2*86400,'Latest manifest protected');
$zero=new Store(new RetentionFixture(),['bucket'=>'fixture','prefix'=>'site/']);checkRetention($zero->requiredRetentionUntil()===null,'Disabled is explicit');retentionFailure(fn()=>$zero->renewLatestSiteRetention(),'positive retention');
echo "PASS retention: new/reused/delayed confirmation, insufficient/read/extension failure, reread, same versions/modes, latest Checkpoint+tail renewal, no old content mutation or rollback; memory storage only.\n";
