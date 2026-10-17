<?php
declare(strict_types=1);
// Read-only preflight using the plugin authentication model, with temporary-role enforcement.
require dirname(__DIR__).'/tools/aws-autoload.php';
use Aws\Credentials\CredentialProvider;
use Aws\S3\S3Client;
use Aws\Sts\StsClient;
use Aws\Exception\AwsException;
require __DIR__ . '/temporary-role-auth.php';
require __DIR__.'/live-target.php';
$target=owrLiveTarget();
$chain = CredentialProvider::defaultProvider();
$credentials = CredentialProvider::memoize(static function () use ($chain) {
    return $chain()->then('owrRequireTemporaryCredentials');
});
$config = ['version'=>'latest','region'=>$target['region'],'credentials'=>$credentials,
    'http'=>['connect_timeout'=>10,'timeout'=>30],'retries'=>1];
$s3 = new S3Client($config);
$sts = new StsClient($config);
$report = ['kind'=>'phase3_aws_readonly_preflight','checked_at'=>gmdate('c'),
    'bucket'=>$target['bucket'],'prefix'=>$target['prefix'],'authentication'=>'sdk-default-chain-temporary-role-required',
    'requested_region'=>$target['region'],'cloud_mutations'=>false,'checks'=>[]];
function checkCall(string $name, callable $call): void {
    global $report;
    try {
        $report['checks'][$name]=['status'=>'observed','value'=>$call()];
    } catch (AwsException $e) {
        $report['checks'][$name]=['status'=>'unverified','aws_error_code'=>$e->getAwsErrorCode(),
            'http_status'=>$e->getStatusCode()];
    } catch (Throwable $e) {
        $report['checks'][$name]=['status'=>'unverified','error_type'=>get_class($e)];
    }
}
checkCall('identity',fn()=>array_intersect_key(owrRequireRoleIdentity($sts->getCallerIdentity()->toArray()),
    array_flip(['Account','Arn','UserId'])));
if (($report['checks']['identity']['status']??'') === 'observed') {
    $args=['Bucket'=>$report['bucket'],'ExpectedBucketOwner'=>$target['owner']];
    checkCall('location',fn()=>['region'=>$s3->getBucketLocation($args)['LocationConstraint']]);
    checkCall('versioning',fn()=>array_intersect_key($s3->getBucketVersioning($args)->toArray(),
        array_flip(['Status','MFADelete'])));
    checkCall('encryption',fn()=>['rules'=>$s3->getBucketEncryption($args)['ServerSideEncryptionConfiguration']['Rules']]);
    checkCall('public_access_block',fn()=>['configuration'=>$s3->getPublicAccessBlock($args)['PublicAccessBlockConfiguration']]);
    checkCall('object_lock',fn()=>['configuration'=>$s3->getObjectLockConfiguration($args)['ObjectLockConfiguration']]);
    checkCall('lifecycle',fn()=>['rules'=>$s3->getBucketLifecycleConfiguration($args)['Rules']]);
}
$dir=dirname(__DIR__).'/evidence/m1/phase3';
if(!is_dir($dir)){mkdir($dir,0700,true);}
$path=$dir.'/aws-preflight-'.gmdate('Ymd\THis').'.json';
file_put_contents($path,json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n");
echo json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES),"\n";