<?php
declare(strict_types=1);
require dirname(__DIR__).'/tools/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require __DIR__.'/support/RbrS3Double.php';
$root=sys_get_temp_dir().'/owr-explicit-'.bin2hex(random_bytes(10));mkdir($root,0700);mkdir($root.'/objects',0700);mkdir($root.'/scratch',0700);
$double=new RbrS3Double($root,2000000000);$double->days=35;$puts=[];
$request=function($op,$a)use($double,&$puts){
 if($op==='PutObject'){
  if(($a['ObjectLockMode']??null)!=='GOVERNANCE' || $a['ObjectLockRetainUntilDate']->getTimestamp()!==$double->now+36*86400){throw new RuntimeException('Missing explicit retention');}
  $puts[]=$a;unset($a['ObjectLockMode'],$a['ObjectLockRetainUntilDate']);$double->days=36;
  try{return $double->request($op,$a);}finally{$double->days=35;}
 }
 return $double->request($op,$a);
};
$store=new Owr\RbrObjectStore($request,'owr-offline-rbr-test','ap-northeast-1','123456789012','sites/corporate-test/',$root.'/scratch',fn()=>$double->now,null,true);
$store->preflight();$ref=$store->ensureBytes($store->key('operations/test.json'),'{}');
if(count($puts)!==1 || $ref['retain_until']!==$double->now+36*86400 || $double->days!==35){throw new RuntimeException('Retention mode failed');}
$again=$store->ensureBytes($store->key('operations/test.json'),'{}');
if(count($puts)!==1 || $again['locator']!==$ref['locator']){throw new RuntimeException('Resume duplicate');}
$legacy=new Owr\RbrObjectStore($request,'owr-offline-rbr-test','ap-northeast-1','123456789012','sites/corporate-test/',$root.'/scratch',fn()=>$double->now);
try{$legacy->preflight();throw new LogicException('Legacy mode accepted35');}catch(RuntimeException $e){if($e instanceof LogicException){throw $e;}}
$scoped=new Owr\RbrObjectStore($request,'owr-offline-rbr-test','ap-northeast-1','123456789012','sites/experiment/nested/',$root.'/scratch',fn()=>$double->now,'corporate-test',true);
if($scoped->siteId()!=='corporate-test' || $scoped->key('commits/1.json')!=='sites/experiment/nested/commits/1.json'){throw new RuntimeException('Logical/physical scope');}
echo json_encode(['passed'=>true,'checks'=>['new_version_36_days_on_35_default','existing_default_unchanged','retry_same_version','legacy_36_default_required','logical_site_physical_prefix_separated']])."\n";
