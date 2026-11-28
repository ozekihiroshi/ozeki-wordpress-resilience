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
    $packet=C::initialSaveWithAuthors(function()use($store){$s=new SiteSnapshot($store);$r=$s->capture(true,get_option('active_plugins'));return $s->load($r['manifest'],true);});
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
case 'authors':
    $kit=$transfer->load(json_decode(file_get_contents('/tmp/kit-commit.json'),true));
    $prepared=get_userdata(1);$before=[$prepared->user_login,$prepared->user_pass,$prepared->roles];
    $legacy=$kit;unset($legacy['files'][OzekiResilience\M1\ConstructionAuthors::PATH]);
    $legacyHeld=R::inspect($legacy)['state']==='held_before_destination_writes';
    $conflict=$kit;$records=OzekiResilience\M1\ConstructionAuthors::read($kit['files']);
    $bad=$records;foreach($bad as &$record){$record['user_login']=$prepared->user_login;}unset($record);
    $conflict['files'][OzekiResilience\M1\ConstructionAuthors::PATH]=wp_json_encode(['schema'=>OzekiResilience\M1\ConstructionAuthors::SCHEMA,'users'=>$bad]);
    $count=count_users()['total_users'];$rejected=false;
    try{OzekiResilience\M1\ConstructionAuthors::register($conflict);}catch(RuntimeException $e){$rejected=true;}
    $conflictSafe=$rejected&&count_users()['total_users']===$count;
    $map=OzekiResilience\M1\ConstructionAuthors::register($kit);$count=count_users()['total_users'];
    $repeat=OzekiResilience\M1\ConstructionAuthors::register($kit);$equal=true;$new=true;$noPrivileges=true;
    foreach($map as $old=>$id){$u=get_userdata($id);foreach($records[$old] as $k=>$v)$equal=$equal&&(string)$u->$k===$v;$new=$new&&$id!==(int)$old;$noPrivileges=$noPrivileges&&!$u->roles&&!$u->caps;}
    $prepared=get_userdata(1);
    echo wp_json_encode(['saved_fields_retained'=>$equal,'new_ids'=>$new,'no_imported_privileges'=>$noPrivileges,'retry_no_duplicates'=>$map===$repeat&&count_users()['total_users']===$count,'prepared_admin_unchanged'=>$before===[$prepared->user_login,$prepared->user_pass,$prepared->roles],'conflict_rejected_without_writes'=>$conflictSafe,'old_material_held'=>$legacyHeld]);break;
case 'bundle':
    $kit=$transfer->load(json_decode(file_get_contents('/tmp/kit-commit.json'),true));
    echo wp_json_encode(OzekiResilience\M1\ConstructionBundle::plan($kit));break;
case 'contracts':
    $kit=$transfer->load(json_decode(file_get_contents('/tmp/kit-commit.json'),true));
    $before=hash('sha256',wp_json_encode($kit));
    $normal=OzekiResilience\M1\ConstructionBundle::plan($kit);
    if($normal['held'])throw new RuntimeException('Current ordinary input held');
    $missing=$kit;unset($missing['files'][OzekiResilience\M1\ConstructionInitialReferences::PATH]);
    $old=OzekiResilience\M1\ConstructionBundle::plan($missing);
    if(!array_filter(array_keys($old['held']),fn($k)=>str_starts_with($k,'image-reference:')))throw new RuntimeException('Missing baseline references guessed');
    $unsafe=$kit;
    foreach($unsafe['tail'] as &$e)if(is_array($e['input']['body']??null)){$e['input']['body']['content']='<img src="x" onerror="alert(1)" />';break;}unset($e);
    if(!OzekiResilience\M1\ConstructionBundle::plan($unsafe)['held'])throw new RuntimeException('Executable HTML accepted');
    if($before!==hash('sha256',wp_json_encode($kit)))throw new RuntimeException('Preserved inputs changed');
    echo wp_json_encode(['ordinary_block_spacing_accepted'=>true,'missing_initial_references_held'=>true,'unsafe_html_held'=>true,'input_unchanged'=>true]);break;
case 'register':
    $kit=$transfer->load(json_decode(file_get_contents('/tmp/kit-commit.json'),true));
    echo wp_json_encode(OzekiResilience\M1\ConstructionAuthors::register($kit));break;
default:throw new RuntimeException('Unknown fixture mode');
}
