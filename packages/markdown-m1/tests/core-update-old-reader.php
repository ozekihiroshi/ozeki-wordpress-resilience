<?php
// Run in a separate process against an unchanged released package.
define('ABSPATH',__DIR__.'/');
require $argv[1].'/src/Store.php';require $argv[1].'/src/SiteSnapshot.php';
$fixture=json_decode(file_get_contents($argv[2]),true,512,JSON_THROW_ON_ERROR);
$s3=new class($fixture['objects']) {
    function __construct(private array $objects){}
    function getObject($a){return $this->objects[$a['Key']]??throw new RuntimeException('Missing fixture');}
};
$store=new OzekiResilience\M1\Store($s3,['bucket'=>'fixture','prefix'=>'trial/']);$site=new OzekiResilience\M1\SiteSnapshot($store);
if($store->originalSource($fixture['old_original'])!==$fixture['raw'])throw new RuntimeException('Control legacy read failed');
foreach(['original'=>fn()=>$store->originalSource($fixture['new_original']),'baseline'=>fn()=>$site->load($fixture['new_point']),'index'=>fn()=>$store->snapshot($fixture['new_index'])] as $name=>$read){
    $rejected=false;try{$read();}catch(RuntimeException $e){$rejected=true;echo $name.': '.$e->getMessage()."\n";}
    if(!$rejected)throw new RuntimeException('Old reader accepted new '.$name);
}
echo "PASS unchanged old reader rejects new original, baseline and independent index; no writes available\n";
