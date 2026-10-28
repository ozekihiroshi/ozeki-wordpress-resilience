<?php
use OzekiResilience\M1\{Store,SiteSnapshot};
require __DIR__.'/separated-assets.php';
class VerifiedCheckpointS3 extends SeparateS3 {
 public array $events=[],$written=[];public ?string $faultPath=null;public bool $missing=false;
 function putObject($a){$this->events[]=['put',$a['Key']];$r=parent::putObject($a);$this->written[$a['Key']]=true;return $r;}
 function getObject($a){$r=parent::getObject($a);$this->events[]=['get',$a['Key'],$a['VersionId']??null];
  if($this->faultPath&&isset($this->written[$a['Key']])&&str_contains($a['Key'],'/resources/'.$this->faultPath)){
   if($this->missing)throw new RuntimeException('Trial unavailable fixed version');$r['Body'].='changed';
  }return $r;}
}
foreach(['initial','checkpoint'] as $mode)foreach(['assets/data/','assets/metadata.json','uploads/photo.png','software.zip'] as $path)foreach([false,true] as $missing){
 $s=new VerifiedCheckpointS3();$st=new Store($s,['bucket'=>'fixture','prefix'=>'verify/']);$ss=new SiteSnapshot($st);
 $data=['tables'=>['posts'=>[['ID'=>'1','post_type'=>'page','post_content'=>'before']],'postmeta'=>[],'comments'=>[]],'options'=>[]];
 $f=['content.json'=>Store::json($data),'uploads/photo.png'=>'PNG fixture','software.zip'=>'software fixture'];
 $m=['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','through'=>0,'source_url'=>'https://trial.invalid'];
 if($mode==='checkpoint'){
  $base=$ss->save($f,$m);$attrs=['origin_id'=>1,'post_type'=>'page','content_format'=>'wordpress-block-html','title'=>'Updated','slug'=>'updated','status'=>'publish','date'=>'2026-10-25 00:00:00','date_gmt'=>'2026-10-25 00:00:00'];
  $o=$st->prepare('page','update','after',$attrs);$st->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$attrs]);
 }
 $existing=$s->objects;$s->events=[];$s->written=[];$s->faultPath=$path;$s->missing=$missing;
 $run=fn()=>$mode==='initial'?$ss->save($f,$m):$ss->checkpoint($base['manifest']);
 try{$run();throw new LogicException('Expected verification failure');}catch(RuntimeException $err){check(str_contains($err->getMessage(),'Site snapshot resource verification failed:'),'path/cause reported');check(str_contains($err->getMessage(),$missing?'Trial unavailable':'S3 content mismatch'),'actual cause');}
 foreach($s->events as $event)check(!($event[0]==='put'&&str_ends_with($event[1],'/manifest.json')),'no manifest PUT after resource failure');
 foreach($existing as $key=>$value)check($s->objects[$key]===$value,'existing resources unchanged');
 $s->faultPath=null;$s->events=[];$result=$run();$seen=[];$manifestAt=null;
 foreach($s->events as $i=>$event){if($event[0]==='get'&&str_contains($event[1],'/resources/')&&!empty($event[2])){$seen[$event[1]]=$event[2];}if($event[0]==='put'&&str_ends_with($event[1],'/manifest.json')){$manifestAt=$i;break;}}
 check($manifestAt!==null,'manifest after successful verification');$manifest=json_decode($st->get($result['manifest']),true);
 foreach($manifest['resources'] as $ref)check(($seen['verify/'.$ref['key']]??null)===$ref['version'],'all exact versions checked before manifest');
 [$loaded,$content]=$ss->load($result['manifest']);check($loaded['through']===($mode==='initial'?0:1),'normal reader/boundary unchanged');
 if($mode==='checkpoint')check(json_decode($content['content.json'],true)['tables']['posts'][0]['post_content']==='after','confirmed tail retained');
 foreach($existing as $key=>$value)check($s->objects[$key]===$value,'prior baseline/history never changed');
}
echo "PASS initial common save and Checkpoint: data/metadata/image/software mismatches and unavailable versions stop before manifest; same fixed versions verified on retry; normal load/tail retained; existing objects unchanged\n";
