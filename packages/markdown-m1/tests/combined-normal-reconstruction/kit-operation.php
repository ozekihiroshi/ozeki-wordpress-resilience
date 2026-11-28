<?php
use OzekiResilience\M1\{Store,SiteSnapshot,ConstructionOperations as C,ConstructionTransfer as T,ConstructionReadiness as R};
wp_set_current_user(1);
final class KitObjects {
    public bool $outage=false,$loseAck=false,$corrupt=false;
    private function path($key){return '/tmp/kit-objects/'.hash('sha256',$key).'.json';}
    public function putObject($a){
        $p=$this->path($a['Key']);
        if($this->outage&&str_contains($a['Key'],'construction-experiment/'))throw new RuntimeException('Synthetic storage outage');
        if(is_file($p))throw new RuntimeException('Immutable key exists');
        if(!is_dir(dirname($p)))mkdir(dirname($p),0700,true);
        $r=['Key'=>$a['Key'],'body64'=>base64_encode($a['Body']),'VersionId'=>hash('sha256',$a['Body'])];file_put_contents($p,json_encode($r));
        if($this->loseAck&&str_contains($a['Key'],'/history/')){$this->loseAck=false;throw new RuntimeException('Synthetic lost acknowledgment');}
        return ['VersionId'=>$r['VersionId']];
    }
    public function getObject($a){
        $p=$this->path($a['Key']);if(!is_file($p))throw new RuntimeException('Missing object',404);
        $r=json_decode(file_get_contents($p),true);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('Wrong object version');
        $r['Body']=base64_decode($r['body64']);if($this->corrupt)$r['Body'].='corrupted-read';return $r;
    }
    public function listObjectsV2($a){
        $out=[];foreach(glob('/tmp/kit-objects/*.json') as $p){$r=json_decode(file_get_contents($p),true);if(str_starts_with($r['Key'],$a['Prefix'])&&$r['Key']>($a['StartAfter']??''))$out[]=['Key'=>$r['Key']];}return ['Contents'=>$out];
    }
    public function inventory(){
        $out=[];foreach(glob('/tmp/kit-objects/*.json') as $p){$r=json_decode(file_get_contents($p),true);$out[$r['Key']]=$r['VersionId'];}ksort($out);return $out;
    }
}
$objects=new KitObjects();$store=new Store($objects,['bucket'=>'isolated','prefix'=>'fixture/']);$transfer=new T($store);
switch($args[0]){
case 'capture':
    $packet=C::initialSave(function()use($store){$s=new SiteSnapshot($store);$r=$s->capture(true,get_option('active_plugins'));return $s->load($r['manifest'],true);});
    file_put_contents('/tmp/kit-packet.bin',serialize($packet));file_put_contents('/tmp/kit-before.json',json_encode($objects->inventory()));
    echo wp_json_encode(['files'=>array_keys($packet['files']),'cutoff'=>$packet['construction_anchor']['through'],'snapshot_schema'=>$packet['manifest']['schema']]);break;
case 'publish':
    $p=unserialize(file_get_contents('/tmp/kit-packet.bin'),['allowed_classes'=>false]);$j=C::stable();
    $objects->outage=true;$stopped=false;try{$transfer->flush($p,$j);}catch(Throwable $e){$stopped=true;}$objects->outage=false;
    $noCommit=!array_filter(array_keys($objects->inventory()),fn($k)=>str_contains($k,'/commits/'));
    $objects->loseAck=true;$ref=$transfer->flush($p,$j);$inventory=$objects->inventory();$retry=$transfer->flush($p,$j);
    if($ref!==$retry||$inventory!==$objects->inventory())throw new RuntimeException('Retry duplicated or changed immutable objects');
    $kit=$transfer->load($ref);$objects->corrupt=true;$reject=false;try{$transfer->load($ref);}catch(Throwable $e){$reject=true;}$objects->corrupt=false;
    $before=json_decode(file_get_contents('/tmp/kit-before.json'),true);foreach($before as $key=>$hash)if(($inventory[$key]??null)!==$hash)throw new RuntimeException('Existing original changed');
    file_put_contents('/tmp/kit-commit.json',json_encode($ref));
    echo wp_json_encode(['outage_stopped'=>$stopped,'outage_no_commit'=>$noCommit,'retry_same_commit'=>$ref===$retry,'no_duplicate_objects'=>$inventory===$objects->inventory(),'tampered_read_rejected'=>$reject,'old_objects_unchanged'=>true,'tail_count'=>count($kit['tail']),'ref'=>$ref]);break;
case 'inspect':
    $before=['posts'=>wp_count_posts('page'),'users'=>count_users(),'options'=>get_option('wpmembers_settings')];
    $kit=$transfer->load(json_decode(file_get_contents('/tmp/kit-commit.json'),true));$r=R::inspect($kit);
    $after=['posts'=>wp_count_posts('page'),'users'=>count_users(),'options'=>get_option('wpmembers_settings')];
    echo wp_json_encode(['readiness'=>$r,'destination_unchanged'=>wp_json_encode($before)===wp_json_encode($after),'consumed'=>'versioned initial save and automatically captured operation stream only']);break;
default:throw new RuntimeException('Unknown fixture mode');
}
