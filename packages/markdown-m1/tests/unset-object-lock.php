<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/cleanup.php';
require_once $argv[1].'/src/SiteSnapshot.php';
class UnsetLockS3 extends CleanupS3 {
 public string $fault='unset',$failOp='retention'; public bool $missing=false; public int $heads=0;
 function headObject($a){$this->heads++;if($this->missing)throw new RuntimeException('Missing fixed version');return parent::headObject($a);}
 function lockRead($op){
  if($op!==$this->failOp)return [];
  if($this->fault==='network')throw new RuntimeException('Network timeout');
  $code=match($this->fault){'unset'=>'NoSuchObjectLockConfiguration','denied'=>'AccessDenied','missing'=>'NoSuchVersion',default=>'Other404'};
  throw new Aws\Exception\AwsException($code,new Aws\Command($op),['code'=>$code,'response'=>new GuzzleHttp\Psr7\Response($this->fault==='denied'?403:404)]);
 }
 function getObjectRetention($a){return $this->lockRead('retention');}
 function getObjectLegalHold($a){return $this->lockRead('hold');}
}
foreach(['retention','hold'] as $op)foreach(['unset','denied','network','missing','other404','head-missing'] as $fault){
 $s=new UnsetLockS3();$st=new Owr\M1\Store($s,['bucket'=>'test','prefix'=>'site/']);$site=new Owr\M1\SiteSnapshot($st);
 $base=$site->save(['content.json'=>'{}','markdown/a.md'=>'original'],['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial']);
 $site->checkpoint($base['manifest']);
 $s->failOp=$op;$s->fault=$fault==='head-missing'?'unset':$fault;$s->missing=$fault==='head-missing';
 $before=$s->objects;$plan=$st->siteCleanupPreview(time());
 if($fault==='unset'){ok(count($plan['candidates'])>0,'Unset config permits otherwise eligible candidates');ok($s->heads>0,'Fixed version existence checked');}
 else {ok(!$plan['candidates']&&count($plan['blocked'])>0,'Failure blocks entire obsolete point: '.$op.'/'.$fault);}
 ok($s->objects===$before&&!$s->deleted,'Preview never mutates assets');
}
echo "PASS unset-lock: retention/hold unset only; denial/network/missing/other404/head failure blocked; preview read-only.\n";
