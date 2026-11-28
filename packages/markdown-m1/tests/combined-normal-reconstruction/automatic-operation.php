<?php
use OzekiResilience\M1\{ConstructionOperations as C,FlamingoReconstruction as F,Store,SiteSnapshot};
wp_set_current_user(1);
switch($args[0]){
case 'journal':echo wp_json_encode(C::read());break;
case 'baseline':
    $packet=C::initialSave(function(){
        $snapshot=new SiteSnapshot(new Store(new stdClass(),['bucket'=>'not-used','prefix'=>'isolated/']));
        $data=(new ReflectionMethod($snapshot,'data'))->invoke($snapshot);
        return [['source_url'=>home_url(),'through'=>0],['content.json'=>Store::json($data)]];
    });
    file_put_contents('/tmp/automatic-baseline.json',wp_json_encode($packet));
    echo wp_json_encode(['anchor'=>$packet['construction_anchor'],'sha256'=>hash_file('sha256','/tmp/automatic-baseline.json')]);break;
case 'tail':
    $p=json_decode(file_get_contents('/tmp/automatic-baseline.json'),true,512,JSON_THROW_ON_ERROR);
    $tail=C::afterInitialSave($p['construction_anchor'],$p['manifest'],$p['files'],C::stable());
    $oldRejected=false;try{C::afterInitialSave([],$p['manifest'],$p['files'],C::stable());}catch(Throwable $e){$oldRejected=true;}
    $p['files']['content.json'].=' ';
    $changeRejected=false;try{C::afterInitialSave($p['construction_anchor'],$p['manifest'],$p['files'],C::stable());}catch(Throwable $e){$changeRejected=true;}
    echo wp_json_encode(['tail'=>$tail,'unanchored_old_save_rejected'=>$oldRejected,'changed_original_rejected'=>$changeRejected]);break;
case 'receipt':
    $p=json_decode(file_get_contents('/tmp/automatic-receipt.json'),true,512,JSON_THROW_ON_ERROR);
    $r=F::recorded($p['entry'],$p['source'],(int)$p['form'],'/tmp/automatic-receipt-journal.json',true);
    echo wp_json_encode(['result'=>$r,'submission_count'=>(int)get_option('fixture_submission_count',0),'journal'=>C::stable()]);break;
default:throw new RuntimeException('Unknown fixture action');
}
