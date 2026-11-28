<?php
// Fast contract tests: no WordPress, database, Docker setup, S3, or HTTP.
require __DIR__.'/construction-operations.php';
require __DIR__.'/../src/ConstructionFollow.php';
use OzekiResilience\M1\{ConstructionOperations as O,ConstructionFollow as F};
$start=microtime(true);$cases=0;
for($variant=0;$variant<100;$variant++){
    $options=[];$source=10+$variant*3;$dest=1000+$variant*5;
    $input=['actor'=>7,'route'=>'/wp/v2/pages','method'=>'POST','body'=>['title'=>'Parent '.$source,'status'=>'publish']];
    $n=O::begin('rest',$input);O::finish($n,['response'=>['id'=>$source]]);
    $n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','method'=>'POST','body'=>['title'=>'Child','parent'=>$source,'status'=>'publish']]);O::finish($n,['response'=>['id'=>$source+1]]);
    $n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages/'.($source+1),'method'=>'POST','body'=>['title'=>'Edited '.$source,'parent'=>0]]);O::finish($n,['response'=>['id'=>$source+1]]);
    $entries=O::stable()['entries'];$calls=[];
    $out=F::run($entries,0,['user:7'=>90],function($endpoint,$target,$body)use(&$calls,$dest){
        $calls[]=[$endpoint,$target,$body];return $target??($dest+count($calls)-1);
    });
    check($calls[0][2]['author']===90&&$calls[1][2]['parent']===$dest&&$calls[2][1]===$dest+1&&$calls[2][2]['parent']===0,'Typed relation/order lost');
    check($entries[0]['input']===$input,'Raw input changed');
    check($out['completed']===[1,2,3],'Operation order changed');
    $swapped=[$entries[1],$entries[0],$entries[2]];$ran=false;
    check(rejects(fn()=>F::run($swapped,0,[],function()use(&$ran){$ran=true;return 1;}))&&!$ran,'Out of order operation executed');
    check(rejects(fn()=>F::run($entries,0,[],fn()=>1)),'Missing author repaired');
    $bad=$entries;$bad[0]['outputs'][0]['id']=9999;
    check(rejects(fn()=>F::run($bad,0,['user:7'=>90],fn()=>1)),'Changed result accepted');
    $cases+=6;
}
$options=[];$n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'[table id="4"]']]);O::finish($n,['response'=>['id'=>10]]);
$ran=false;check(rejects(fn()=>F::run(O::stable()['entries'],0,['user:7'=>90],function()use(&$ran){$ran=true;return 20;}))&&!$ran,'Incomplete capture executed');$cases++;
echo json_encode(['checks'=>$cases,'seconds'=>round(microtime(true)-$start,4),'source_input_unchanged'=>true,'order_followed'=>true,'incomplete_capture_rejected'=>true],JSON_PRETTY_PRINT)."\n";
