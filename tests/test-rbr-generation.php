<?php
declare(strict_types=1);
require dirname(__DIR__).'/tools/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
require __DIR__.'/support/RbrS3Double.php';
use Owr\RbrObjectStore;
use Owr\RbrGenerationCoordinator as Coordinator;
$root=sys_get_temp_dir().'/owr-rbr-'.bin2hex(random_bytes(12));mkdir($root,0700);
$checks=[];$counter=0;
function assertR(bool $ok,string $why='assertion'): void { if (!$ok) { throw new RuntimeException($why); } }
function checkR(string $name,callable $fn): void { global $checks; $fn();$checks[]=['name'=>$name,'passed'=>true]; }
function rejectR(callable $fn,string $contains=''): void {
    try { $fn(); } catch(Throwable $e) {
        assertR($contains==='' || str_contains($e->getMessage(),$contains), 'Unexpected error: '.$e->getMessage());return;
    } throw new RuntimeException('Expected rejection');
}
function labR(): array {
    global $root,$counter; $dir=$root.'/case-'.(++$counter);mkdir($dir,0700);mkdir($dir.'/objects',0700);mkdir($dir.'/scratch',0700);
    $server=new RbrS3Double($dir,2000000000);
    $store=new RbrObjectStore($server->request(...),'owr-offline-rbr-test','ap-northeast-1','123456789012',
        'sites/corporate-test/',$dir.'/scratch',fn()=>$server->now);
    $assets=[];
    foreach(['company','services','contact'] as $role) {
        $raw=Coordinator::encode(['title'=>ucfirst($role),'slug'=>$role,'paragraphs'=>['Synthetic '.$role.' information']]);
        $assets[]=assetR($dir,$role,'page',$raw)+['role'=>$role];
    }
    $im=imagecreatetruecolor(2,2);ob_start();imagepng($im);$png=ob_get_clean();imagedestroy($im);
    $assets[]=assetR($dir,'logo','image',$png);
    $assets[]=assetR($dir,'profile','profile',Coordinator::encode(['schema'=>'owr-rbr-profile-v1',
        'roles'=>['company'=>'company','services'=>'services','contact'=>'contact']]));
    $assets[]=assetR($dir,'relations','relations',Coordinator::encode(['edges'=>[
        ['from'=>'company','to'=>'services','type'=>'link','position'=>0],
        ['from'=>'company','to'=>'logo','type'=>'image','position'=>1],
        ['from'=>'services','to'=>'contact','type'=>'navigation','position'=>0]]]));
    $job=['schema'=>'owr-rbr-save-v1','site_id'=>'corporate-test','operation_id'=>'initial',
        'sequence'=>1,'parent'=>null,'prepared_at'=>$server->now,'deadline'=>$server->now+3600,'assets'=>$assets];
    return [$server,new Coordinator($store),$job,$dir];
}
function assetR(string $dir,string $id,string $kind,string $bytes): array {
    $p=$dir.'/'.$id.'.input';file_put_contents($p,$bytes);
    return ['id'=>$id,'revision'=>'rev1','kind'=>$kind,'provenance'=>'s3-first',
        'size_bytes'=>strlen($bytes),'sha256'=>hash('sha256',$bytes),'path'=>$p];
}
function nextR(array $job,array $result,RbrS3Double $server): array {
    $job['sequence']++;$job['operation_id']='next-'.$job['sequence'];$job['parent']=$result['generation'];
    $job['prepared_at']=$server->now;$job['deadline']=$server->now+3600;
    foreach($job['assets'] as $i=>&$a) { unset($a['path']);$a['existing']=$result['manifest']['assets'][$i]['storage']; }
    return $job;
}
function countR(RbrS3Double $s,string $part): int { return count(array_filter($s->objects(),fn($o)=>str_contains($o['key'],$part))); }
try {
checkR('three pages image relations and profile commit; no WP publication',function(){
    [$s,$c,$j]=labR();$r=$c->save($j);
    assertR($r['state']==='committed'&&$r['wp_state']==='not_applied'&&count($r['manifest']['assets'])===6);
    assertR(countR($s,'/commits/')===1&&countR($s,'/originals/')===6);
    foreach($r['manifest']['assets'] as $a){assertR($a['storage']['retain_until'] >= $j['deadline']+35*86400);}
});
checkR('reopen coordinator and retry with local source files removed',function(){
    [$s,$c,$j,$d]=labR();$r=$c->save($j);foreach($j['assets'] as $a){unlink($a['path']);}
    $store=new RbrObjectStore($s->request(...),'owr-offline-rbr-test','ap-northeast-1','123456789012','sites/corporate-test/',$d.'/scratch',fn()=>$s->now);
    $r2=(new Coordinator($store))->save($j);assertR($r['generation']===$r2['generation']);assertR(countR($s,'/commits/')===1);
});
checkR('changed operation payload cannot be reused',function(){
    [$s,$c,$j]=labR();$c->save($j);$j['assets'][0]['sha256']=str_repeat('a',64);
    rejectR(fn()=>$c->save($j));assertR(countR($s,'/commits/')===1);
});
checkR('partial upload failure preserves previous complete generation and resumes',function(){
    [$s,$c,$j,$d]=labR();$first=$c->save($j);$j=nextR($j,$first,$s);
    $new=assetR($d,'services','page',Coordinator::encode(['title'=>'New services','slug'=>'services','paragraphs'=>['New synthetic text']]));
    $new['revision']='rev2';$j['assets'][1]=$new+['role'=>'services'];
    $s->failPutContains='/services/rev2/';rejectR(fn()=>$c->save($j));assertR(countR($s,'/commits/')===1);
    $s->failPutContains=null;$second=$c->save($j);assertR($second['manifest']['sequence']===2&&countR($s,'/commits/')===2);
});
checkR('partial originals already saved survive missing local files on retry',function(){
    [$s,$c,$j]=labR();$s->failPutContains='/services/';rejectR(fn()=>$c->save($j));
    unlink($j['assets'][0]['path']);$s->failPutContains=null;$c->save($j);assertR(countR($s,'/originals/')===6);
});
checkR('lost original PUT response reconciles exact version',function(){
    [$s,$c,$j]=labR();$s->loseResponseContains='/originals/';$c->save($j);assertR(countR($s,'/originals/')===6);
});
checkR('lost commit PUT response reconciles one commit',function(){
    [$s,$c,$j]=labR();$s->loseResponseContains='/commits/';$r=$c->save($j);$r2=$c->save($j);
    assertR($r['generation']===$r2['generation']&&countR($s,'/commits/')===1);
});
checkR('commit unavailable leaves originals confirmed and no partial generation',function(){
    [$s,$c,$j]=labR();$s->failPutContains='/commits/';rejectR(fn()=>$c->save($j));
    assertR($c->lastConfirmedStage()==='originals_confirmed'&&countR($s,'/commits/')===0);
    $s->failPutContains=null;$c->save($j);assertR(countR($s,'/originals/')===6);
});
checkR('denied discovery never becomes missing or blind PUT',function(){
    [$s,$c,$j]=labR();$s->denyReadContains='/operations/';rejectR(fn()=>$c->save($j));assertR(count($s->objects())===0);
});
checkR('36-day default required without changing legacy bucket',function(){
    [$s,$c,$j]=labR();$s->days=35;rejectR(fn()=>$c->save($j),'36-day');assertR(count($s->objects())===0);
});
checkR('expired uncommitted operation blocked; committed result still reconciled',function(){
    [$s,$c,$j]=labR();$s->now=$j['deadline']+1;rejectR(fn()=>$c->save($j),'expired');assertR(countR($s,'/commits/')===0);
    [$s,$c,$j]=labR();$r=$c->save($j);$s->now=$j['deadline']+1;assertR($c->save($j)['generation']===$r['generation']);
});
checkR('old image copied with stable logical identity and pinned bytes; no retention mutation',function(){
    [$s,$c,$j]=labR();$first=$c->save($j);$old=$first['manifest']['assets'][3]['storage'];
    $s->age($old['locator']['key'],$s->now+3600);$next=nextR($j,$first,$s);$second=$c->save($next);
    $a=$second['manifest']['assets'][3];assertR($a['id']==='logo'&&$a['revision']==='rev1'&&$a['storage']['sha256']===$old['sha256']);
    assertR($a['storage']['locator']['key']!==$old['locator']['key']);assertR(countR($s,'/copies/')===1);
    assertR(!in_array('PutObjectRetention',$s->calls,true)&&!in_array('DeleteObject',$s->calls,true));
    $third=$c->save(nextR($next,$second,$s));assertR(countR($s,'/copies/')===1);
});
checkR('copy failure blocks new generation and retry does not duplicate copy',function(){
    [$s,$c,$j]=labR();$first=$c->save($j);$s->age($first['manifest']['assets'][3]['storage']['locator']['key'],$s->now+1);
    $next=nextR($j,$first,$s);$s->failPutContains='/copies/';rejectR(fn()=>$c->save($next));assertR(countR($s,'/commits/')===1);
    $s->failPutContains=null;$s->loseResponseContains='/copies/';$c->save($next);$c->save($next);assertR(countR($s,'/copies/')===1);
});
checkR('corrupted fixed bytes stop commit',function(){
    [$s,$c,$j]=labR();$s->corruptContains='/originals/';rejectR(fn()=>$c->save($j));assertR(countR($s,'/commits/')===0);
});
checkR('foreign site and parent rejected',function(){
    [$s,$c,$j]=labR();$j['site_id']='foreign';rejectR(fn()=>$c->save($j),'scope');assertR(count($s->objects())===0);
    [$s,$c,$j]=labR();$r=$c->save($j);$j=nextR($j,$r,$s);$j['parent']['sha256']=str_repeat('0',64);rejectR(fn()=>$c->save($j));
});
checkR('missing role and unsafe identity rejected before writes',function(){
    [$s,$c,$j]=labR();$j['assets'][0]['role']='other';rejectR(fn()=>$c->save($j));assertR(count($s->objects())===0);
    [$s,$c,$j]=labR();$j['assets'][0]['id']='../escape';rejectR(fn()=>$c->save($j));assertR(count($s->objects())===0);
});
checkR('unresolved relationship withheld, never silently stripped',function(){
    [$s,$c,$j,$d]=labR();$j['assets'][5]=assetR($d,'relations','relations',Coordinator::encode(['edges'=>[
        ['from'=>'company','to'=>'missing','type'=>'link','position'=>0]]]));
    rejectR(fn()=>$c->save($j),'Unresolved');assertR(countR($s,'/commits/')===0);
});
checkR('stale editor cannot jump or overwrite newer generation',function(){
    [$s,$c,$j]=labR();$c->save($j);$j['operation_id']='competitor';rejectR(fn()=>$c->save($j),'conflict');assertR(countR($s,'/commits/')===1);
});
checkR('server clock skew fails closed',function(){
    [$s,$c,$j]=labR();$s->clockSkew=900;rejectR(fn()=>$c->save($j),'clock');assertR(countR($s,'/commits/')===0);
});
checkR('late S3 commit never returned as eligible success, including retry',function(){
    [$s,$c,$j]=labR();$s->commitDelay=4000;rejectR(fn()=>$c->save($j),'Late');
    assertR(countR($s,'/commits/')===1);rejectR(fn()=>$c->save($j),'Late');
});
if(function_exists('pcntl_fork')) {
checkR('two independent PHP processes race for same slot: one winner only',function(){
    [$s,$c,$j,$d]=labR();$children=[];
    for($i=0;$i<2;$i++) {
        $pid=pcntl_fork();assertR($pid!==-1);
        if($pid===0) {
            $s->barrier=true;$j['operation_id']='racer-'.$i;
            try {$c->save($j);$out='committed';}catch(Throwable $e){$out='rejected:'.$e->getMessage();}
            file_put_contents($d.'/child-'.$i,$out);exit(0);
        }$children[]=$pid;
    }
    foreach($children as $pid){pcntl_waitpid($pid,$status);assertR(pcntl_wexitstatus($status)===0);}
    $out=[file_get_contents($d.'/child-0'),file_get_contents($d.'/child-1')];
    assertR(count(array_filter($out,fn($v)=>$v==='committed'))===1,implode(' / ',$out));
    assertR(countR($s,'/commits/')===1&&countR($s,'/originals/')===6);
});
} else { throw new RuntimeException('pcntl required for actual process contention test'); }
echo json_encode(['kind'=>'rbr_generation_contract_tests','checked_at'=>gmdate('c'),'passed'=>true,
    'checks'=>$checks,'backend'=>'atomic-filesystem-S3-test-double','aws_verified'=>false,
    'production_changes'=>false,'wp_apply_implemented'=>false],JSON_PRETTY_PRINT)."\n";
} finally {
    $walk=function(string $dir)use(&$walk):void{foreach(scandir($dir)as$n){if($n==='.'||$n==='..')continue;$p=$dir.'/'.$n;
        if(is_dir($p)&&!is_link($p)){$walk($p);rmdir($p);}else{unlink($p);}}};
    $walk($root);rmdir($root);
}
