<?php
namespace Aws\Exception {
    // Minimal SDK exception double: no credentials/network required.
    class AwsException extends \RuntimeException { public function getAwsErrorCode(){return 'AccessDenied';} }
}
namespace {
require __DIR__.'/site-retention.php';
class ListDeniedS3 extends CleanupS3 {
 function listObjectVersions($a){throw new \Aws\Exception\AwsException('denied');}
 function headObject($a){$r=$this->getObject($a);return ['VersionId'=>$r['VersionId'],'LastModified'=>new \DateTimeImmutable('@'.$this->dates[$a['Key']])];}
}
$s=new ListDeniedS3();$store=new \Owr\M1\Store($s,['bucket'=>'test','prefix'=>'site/']);$site=new \Owr\M1\SiteSnapshot($store);
$GLOBALS['test_options']=[];
$m=['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial'];$site->save(['content.json'=>'{}'],$m);
add($store,1,'a','changed');$m['through']=1;$site->save(['content.json'=>'{"new":true}'],$m);
$before=$s->objects;$p=$store->siteCleanupPreview(time());
ok(!$p['inventory_complete']&&!$p['candidates']&&count($p['retained'])>0&&count($p['blocked'])>0,'fallback keeps required assets but never certifies deletion');
ok(str_contains(implode(' ',array_column($p['blocked'],'reason')),'ListBucketVersions'),'permission reason visible');
ok($before===$s->objects&&!$s->deleted,'fallback no writes');
echo "PASS missing version-list permission: fixed-version read fallback, retained assets, blocked reasons, no candidates or mutations.\n";
}
