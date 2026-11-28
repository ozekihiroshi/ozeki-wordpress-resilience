<?php
/** Runs only in the disposable, network-isolated WordPress fixture. */
use OzekiResilience\M1\{Store,SiteSnapshot,UpdateContract,NativeReconstruction};
spl_autoload_register(static function($name){$prefix='OzekiResilience\\M1\\';if(str_starts_with($name,$prefix)){ $p='/tmp/product/src/'.substr($name,strlen($prefix)).'.php';if(is_file($p))require_once $p;}});
require_once '/tmp/product/tests/retention-memory.php';
class NativeMemoryObjects {
    use RetentionMemory;
    public array $objects=[];public int $n=0;
    function putObject($a){if(isset($this->objects[$a['Key']]))throw new RuntimeException('duplicate object');return $this->objects[$a['Key']]=['Body'=>(string)$a['Body'],'VersionId'=>'v'.++$this->n];}
    function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
    function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&(!isset($a['StartAfter'])||strcmp($k,$a['StartAfter'])>0))$out[]=['Key'=>$k];usort($out,fn($x,$y)=>strcmp($x['Key'],$y['Key']));return ['Contents'=>$out];}
}
function ok($x){if(is_wp_error($x))throw new RuntimeException($x->get_error_message());return $x;}
function must_native($x,$m){if(!$x)throw new RuntimeException($m);}
wp_set_current_user(1);
$mode=$args[0];$object=new NativeMemoryObjects();$store=new Store($object,['bucket'=>'local-only','prefix'=>'flamingo-fixture/','retention_days'=>0]);$site=new SiteSnapshot($store);
if($mode==='seed'){
 $form=wpcf7_contact_form((int)$args[1]);$tid=wpcf7_flamingo_add_channel($form->name(),$form->title());$term=get_term($tid,'flamingo_inbound_channel');$out=[];
 foreach(['normal','spam','slashes'] as $kind){
  $a=['channel'=>$term->slug,'status'=>$kind==='spam'?'spam':'mail_sent','subject'=>'技術受付 '.$kind,'from'=>'Tester <tester@example.invalid>','from_name'=>'Tester','from_email'=>'tester@example.invalid','fields'=>['equipment-code'=>'PLC-24','choices'=>['solar','monitor'],'details'=>"一行目\n二行目",'zero'=>'0','empty'=>''],'meta'=>['url'=>'https://source.example.invalid/form','post_id'=>'100'],'akismet'=>[],'recaptcha'=>[],'spam_log'=>[],'consent'=>['acceptance'=>'accepted'],'timestamp'=>1794000000,'posted_data_hash'=>hash('sha256',$kind),'spam'=>$kind==='spam'];
  if($kind==='slashes')$a['fields']['details']='C:\\\\docs';
  $x=Flamingo_Inbound_Message::add($a);$read=new Flamingo_Inbound_Message($x->id());$out[$kind]=['id'=>$x->id(),'fields'=>$read->fields,'date'=>get_post($x->id())->post_date_gmt];
 }
 echo wp_json_encode($out);return;
}
if($mode==='capture'){
 $data=(new ReflectionMethod($site,'data'))->invoke($site);$files=[];$upload=wp_upload_dir();
 foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($upload['basedir'],FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$files['uploads/'.substr($f->getPathname(),strlen($upload['basedir'])+1)]=file_get_contents($f->getPathname());
 foreach($data['tables']['postmeta'] as $row)if($row['meta_key']==='_ozmd_source')$files['markdown/'.$row['post_id'].'.md']=$row['meta_value'];
 $files['content.json']=Store::json($data);$initial=$site->save($files,['schema'=>'owr-site-snapshot-1','source_url'=>home_url(),'source_upload_url'=>$upload['baseurl'],'through'=>0,'wordpress'=>$GLOBALS['wp_version'],'plugins'=>['contact-form-7/wp-contact-form-7.php','flamingo/flamingo.php']]);
 file_put_contents('/tmp/fl-materials.bin',serialize(['objects'=>$object->objects,'ref'=>$initial['manifest'],'n'=>$object->n]));echo wp_json_encode(['baseline_posts'=>count($data['tables']['posts'])]);return;
}
$material=unserialize(file_get_contents('/tmp/fl-materials.bin'),['allowed_classes'=>false]);$object->objects=$material['objects'];$object->n=$material['n'];
if($mode==='history'){
 $sequence=0;foreach(array_slice($args,1) as $instruction){
  [$kind,$id]=explode(':',$instruction,2);$post=get_post((int)$id,ARRAY_A);$meta=[];
  foreach(get_post_meta((int)$id) as $key=>$values){if(in_array($key,['_edit_lock','_edit_last'],true))continue;foreach($values as $value)$meta[]=['meta_key'=>$key,'meta_value'=>$value];}
  $channels=[];foreach(wp_get_object_terms((int)$id,'flamingo_inbound_channel') as $t)$channels[]=(array)$t;$item=['post'=>$post,'meta'=>$meta,'channels'=>$channels];if($kind==='delete')$item['deleted']=true;
  $a=['post_type'=>'owr_form','content_format'=>'form-json','origin_id'=>(int)$id,'title'=>$post['post_title'],'status'=>$kind==='delete'?'deleted':$post['post_status'],'dependencies'=>['contact-form-7/wp-contact-form-7.php'=>WPCF7_VERSION]];
  $original=$store->prepare('form-'.$id,'formal-'.++$sequence,Store::json(['schema'=>'owr-form-1','items'=>[$item]]),$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$sequence,'original'=>$original,'attributes'=>$a]);
 }
 $material['objects']=$object->objects;$material['n']=$object->n;$material['through']=$sequence;file_put_contents('/tmp/fl-materials.bin',serialize($material));echo wp_json_encode(['through'=>$sequence]);return;
}
if($mode==='plan'){
 $before=hash('sha256',serialize($object->objects));$target=(int)($args[1]??$material['through']);$plan=$site->flamingoRegistrationPlan($material['ref'],$target);must_native($before===hash('sha256',serialize($object->objects)),'Input mutated');$plan['input_unchanged']=true;echo wp_json_encode($plan);return;
}
throw new RuntimeException('Unknown mode');
