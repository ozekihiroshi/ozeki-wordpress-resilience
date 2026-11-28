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
$mode=$args[0];$object=new NativeMemoryObjects();$store=new Store($object,['bucket'=>'local-only','prefix'=>'tablepress-fixture/','retention_days'=>0]);$site=new SiteSnapshot($store);
if($mode==='capture'){
 $data=(new ReflectionMethod($site,'data'))->invoke($site);$files=[];$upload=wp_upload_dir();
 foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($upload['basedir'],FilesystemIterator::SKIP_DOTS)) as $f)if($f->isFile())$files['uploads/'.substr($f->getPathname(),strlen($upload['basedir'])+1)]=file_get_contents($f->getPathname());
 foreach($data['tables']['postmeta'] as $row)if($row['meta_key']==='_ozmd_source')$files['markdown/'.$row['post_id'].'.md']=$row['meta_value'];
 $files['content.json']=Store::json($data);$initial=$site->save($files,['schema'=>'owr-site-snapshot-1','source_url'=>home_url(),'source_upload_url'=>$upload['baseurl'],'through'=>0,'wordpress'=>$GLOBALS['wp_version'],'plugins'=>['tablepress/tablepress.php']]);
 file_put_contents('/tmp/tp-materials.bin',serialize(['objects'=>$object->objects,'ref'=>$initial['manifest'],'n'=>$object->n]));echo wp_json_encode(['baseline_posts'=>count($data['tables']['posts'])]);return;
}
$material=unserialize(file_get_contents('/tmp/tp-materials.bin'),['allowed_classes'=>false]);$object->objects=$material['objects'];$object->n=$material['n'];
if($mode==='history'){
 $sequence=0;foreach(array_slice($args,1) as $instruction){
  [$kind,$id]=explode(':',$instruction,2);$map=json_decode(get_option('tablepress_tables'),true,512,JSON_THROW_ON_ERROR);
  $v=['schema'=>'owr-table-1','kind'=>$kind,'id'=>$id,'old_id'=>'','version'=>TablePress::version,'last_id'=>(int)$map['last_id']];
  if($kind==='table'){
   $pid=$map['table_post'][$id];$v['post']=get_post($pid,ARRAY_A);$v['meta']=[];
   foreach(['_tablepress_table_options','_tablepress_table_visibility'] as $key)$v['meta'][]=['meta_key'=>$key,'meta_value'=>get_post_meta($pid,$key,true)];
  }
  $a=['post_type'=>'owr_table','content_format'=>'table-json','origin_id'=>$id,'title'=>'TablePress '.$id,'status'=>$kind==='delete'?'deleted':'saved','tablepress_version'=>TablePress::version];
  $original=$store->prepare('table-'.$id,'formal-'.++$sequence,Store::json($v),$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>$sequence,'original'=>$original,'attributes'=>$a]);
 }
 $material['objects']=$object->objects;$material['n']=$object->n;$material['through']=$sequence;file_put_contents('/tmp/tp-materials.bin',serialize($material));echo wp_json_encode(['through'=>$sequence]);return;
}
if($mode==='plan'){
 $before=hash('sha256',serialize($object->objects));$target=(int)($args[1]??$material['through']);$plan=$site->tablepressRegistrationPlan($material['ref'],$target);must_native($before===hash('sha256',serialize($object->objects)),'Input mutated');$plan['input_unchanged']=true;echo wp_json_encode($plan);return;
}
throw new RuntimeException('Unknown mode');
