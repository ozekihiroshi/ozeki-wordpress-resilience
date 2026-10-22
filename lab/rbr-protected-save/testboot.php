<?php
// Dedicated generated-data lab only; never included by the production plugin bootstrap.
if(!defined('ABSPATH'))exit;
if(!is_file('/lab/config.json'))return;
require_once '/kit/tools/aws-autoload.php';
foreach(['VersionedAssetStore','RbrObjectStore','RbrGenerationCoordinator','RbrWordPressSave','RbrWordPressSaveApi'] as $n)require_once '/kit/src/'.$n.'.php';
require_once '/kit/tests/support/RbrS3Double.php';
function owr_test_factory(){
 $config=json_decode(file_get_contents('/lab/config.json'),true);
 $db=new mysqli('127.0.0.1',DB_USER,DB_PASSWORD,DB_NAME,3306);
 $server=new RbrS3Double('/lab/s3',time());
 $control=is_file('/lab/control.json')?json_decode(file_get_contents('/lab/control.json'),true):[];
 $server->failPutContains=$control['fail']??null;
 $request=function($op,$args)use($server){file_put_contents('/lab/calls.jsonl',json_encode(['op'=>$op,'key'=>$args['Key']??null])."\n",FILE_APPEND|LOCK_EX);return $server->request($op,$args);};
 $store=new Owr\RbrObjectStore($request,'owr-offline-rbr-test','ap-northeast-1','123456789012','sites/corporate-test/','/lab/scratch',fn()=>time());
 $fault=function($stage)use($control){
  if(($control['stop']??null)===$stage)exit(93);
  if(($control['throw']??null)===$stage)throw new RuntimeException('Injected failure');
  if(($control['pause']??null)===$stage){touch('/lab/paused');$end=microtime(true)+15;while(!file_exists('/lab/release')&&microtime(true)<$end)usleep(10000);if(!file_exists('/lab/release'))throw new RuntimeException('Barrier expired');}
 };
 global $wpdb;return new Owr\RbrWordPressSave($db,$wpdb->posts,$config['ids'],$config['seed'],$store,'/lab/originals',$config['images'],$fault);
}
Owr\RbrWordPressSaveApi::boot(owr_test_factory(...),json_decode(file_get_contents('/lab/config.json'),true)['ids']);
