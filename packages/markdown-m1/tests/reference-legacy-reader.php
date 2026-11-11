<?php
// Invoke in a separate process with the frozen old reader, not a simulated version check.
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/Store.php';require $argv[1].'/src/SiteSnapshot.php';
$v=json_decode(file_get_contents($argv[2]),true,512,JSON_THROW_ON_ERROR);
$s3=new class($v['objects']) {
 public function __construct(public array $objects){}
 public function getObject($args){return $this->objects[$args['Key']]??throw new RuntimeException('missing');}
};
$s=new OzekiResilience\M1\Store($s3,['bucket'=>'fixture','prefix'=>'trial/']);$site=new OzekiResilience\M1\SiteSnapshot($s);
$s->originalSource($v['old_original']);$site->load($v['old_point']);
foreach([fn()=>$s->originalSource($v['new_original']),fn()=>$site->load($v['new_point'])] as $read){
 $blocked=false;try{$read();}catch(RuntimeException $e){$blocked=in_array($e->getMessage(),['Unsupported original format.','Invalid separated site resources.'],true);}
 if(!$blocked)throw new RuntimeException('Legacy reader did not reject mandatory new context');
}
echo "PASS: actual legacy reader reads old originals/points and rejects new mandatory-context originals/points\n";
