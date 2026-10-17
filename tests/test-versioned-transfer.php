<?php
declare(strict_types=1);
require dirname(__DIR__).'/tools/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
use GuzzleHttp\Psr7\Utils;
use Owr\VersionedAssetStore;
$root=sys_get_temp_dir().'/owr-transfer-'.bin2hex(random_bytes(8));
mkdir($root,0700);
$checks=[];
function test(string $name,callable $fn):void {
 global $checks;
 $fn(); $checks[]=['name'=>$name,'passed'=>true];
}
function ok(bool $value):void {if (!$value) {throw new RuntimeException('Assertion failed');}}
function rejects(callable $fn):void {
 try {$fn();} catch (Throwable $e) {return;}
 throw new RuntimeException('Expected rejection');
}
$data="synthetic database\n";$sha=hash('sha256',$data);$size=strlen($data);
file_put_contents($root.'/input',$data);
$mode='normal';$calls=[];
$request=function($op,$args) use (&$mode,&$calls,$data) {
 $calls[]=[$op,$args];
 if ($op==='GetBucketVersioning') {return ['Status'=>$mode==='disabled'?'Suspended':'Enabled'];}
 if ($op==='PutObject') {
  ok($args['IfNoneMatch']==='*');
  ok($args['ExpectedBucketOwner']==='123456789012');
  ok(base64_encode(hash('sha256',stream_get_contents($args['Body']),true))===$args['ChecksumSHA256']);
  if ($mode==='conflict') {throw new RuntimeException('412');}
  return $mode==='no_version'?[]:['VersionId'=>'v-old'];
 }
 ok($op==='GetObject' && $args['VersionId']==='v-old');
 if ($mode==='denied') {throw new RuntimeException('AccessDenied');}
 return ['VersionId'=>$mode==='wrong_version'?'v-new':'v-old',
   'ContentLength'=>strlen($data),
   'Body'=>Utils::streamFor(match($mode) {
      'corrupt'=>str_repeat('x',strlen($data)),
      'short'=>substr($data,1),
      'long'=>$data.'x',
      default=>$data
   })];
};
$store=new VersionedAssetStore($request,'owr-example-bucket','ap-northeast-1','123456789012','wordpress-test/');
$key='wordpress-test/RS-TEST/database.sql.gz';
try {
 test('conditional upload returns exact version',function()use($store,$root,$key,$size,$sha){
  $r=$store->upload($root.'/input',$key,$size,$sha);
  ok($r['locator']['version_id']==='v-old' && $r['role_separation']==='unverified');
 });
 foreach(['disabled','no_version','conflict'] as $failure) {
  test('upload rejects '.$failure,function()use(&$mode,$failure,$store,$root,$key,$size,$sha){
   $mode=$failure; rejects(fn()=>$store->upload($root.'/input',$key,$size,$sha));
  });
 }
 $mode='normal';
 test('input hash rejected before network',function()use(&$calls,$store,$root,$key,$size){
  $before=count($calls);
  rejects(fn()=>$store->upload($root.'/input',$key,$size,str_repeat('0',64)));
  ok(count($calls)===$before);
 });
 test('prefix escape rejected',function()use($store,$root,$size,$sha){
  rejects(fn()=>$store->upload($root.'/input','other/key',$size,$sha));
  rejects(fn()=>$store->upload($root.'/input','wordpress-test/../outside',$size,$sha));
 });
 test('pinned download despite changed latest',function()use($store,$key,$size,$sha,$root,$data){
  $r=$store->download($key,'v-old',$size,$sha,$root.'/good');
  ok(file_get_contents($root.'/good')===$data);
  ok($r['observation']==='download_integrity_checked' && $r['role_separation']==='unverified');
 });
 test('destination overwrite refused',function()use($store,$key,$size,$sha,$root,$data){
  rejects(fn()=>$store->download($key,'v-old',$size,$sha,$root.'/good'));
  ok(file_get_contents($root.'/good')===$data);
 });
 foreach(['wrong_version','corrupt','short','long','denied'] as $failure) {
  test('download rejects '.$failure,function()use(&$mode,$failure,$store,$root,$key,$size,$sha){
   $mode=$failure;
   rejects(fn()=>$store->download($key,'v-old',$size,$sha,$root.'/bad'));
   ok(!file_exists($root.'/bad') && glob($root.'/.owr-download-*')===[]);
  });
 }
 test('null version rejected before request',function()use(&$calls,$store,$root,$key,$size,$sha){
  $before=count($calls);
  rejects(fn()=>$store->download($key,'null',$size,$sha,$root.'/bad'));
  ok(count($calls)===$before);
 });
 echo json_encode(['kind'=>'versioned_transfer_offline_tests','checked_at'=>gmdate('c'),
     'passed'=>true,'checks'=>$checks,'cloud_operations'=>false],JSON_PRETTY_PRINT)."\n";
} finally {
 foreach(glob($root.'/*') as $p){unlink($p);}
 foreach(glob($root.'/.owr-download-*') as $p){unlink($p);}
 rmdir($root);
}