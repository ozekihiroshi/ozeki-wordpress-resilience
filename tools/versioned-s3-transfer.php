<?php
declare(strict_types=1);
require dirname(__DIR__).'/tools/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require __DIR__.'/temporary-role-auth.php';
require __DIR__.'/live-target.php';
$target=owrLiveTarget();
use Aws\Credentials\CredentialProvider;
use Aws\S3\S3Client;
use Aws\Sts\StsClient;
if (count($argv)!==7 || !in_array($argv[1],['upload','download'],true)) {
    fwrite(STDERR,"upload FILE KEY SIZE SHA256 RECEIPT_OUTPUT\n"
        ."download RECEIPT_INPUT DESTINATION SIZE SHA256 OBSERVATION_OUTPUT\n");
    exit(2);
}
umask(0077);
$out=$argv[6];
$lock=null;
try {
    if (file_exists($out)||is_link($out)) {throw new RuntimeException('Output exists');}
    if (!ctype_digit($argv[4])) {throw new RuntimeException('Invalid size');}
    // Reserve evidence output before any cloud operation.
    $lock=fopen($out,'x');
    if (!$lock) {throw new RuntimeException('Cannot reserve output');}
    $chain=CredentialProvider::defaultProvider();
    $provider=CredentialProvider::memoize(static fn()=>$chain()->then('owrRequireTemporaryCredentials'));
    $config=['version'=>'latest','region'=>$target['region'],'credentials'=>$provider,
        'http'=>['connect_timeout'=>10,'timeout'=>120],'retries'=>0];
    $identity=owrRequireRoleIdentity((new StsClient($config))->getCallerIdentity()->toArray());
    if ($identity['Account']!==$target['owner']) {throw new RuntimeException('Unexpected account');}
    $client=new S3Client($config);
    $store=new Owr\VersionedAssetStore(
        static fn($operation,$args)=>$client->execute($client->getCommand($operation,$args))->toArray(),
        $target['bucket'],$target['region'],$target['owner'],$target['prefix']);
    if ($argv[1]==='upload') {
        $result=$store->upload($argv[2],$argv[3],(int)$argv[4],$argv[5]);
    } else {
        if (filesize($argv[2])>65536) {throw new RuntimeException('Receipt too large');}
        $r=json_decode(file_get_contents($argv[2]),true,32,JSON_THROW_ON_ERROR);
        if (($r['kind']??null)!=='owr-versioned-upload-receipt'
            || ($r['locator']['bucket']??null)!==$target['bucket']
            || ($r['locator']['region']??null)!==$target['region']
            || ($r['size_bytes']??null)!==(int)$argv[4] || ($r['sha256']??null)!==$argv[5]) {
            throw new RuntimeException('Receipt expectation mismatch');
        }
        $result=$store->download($r['locator']['key'],$r['locator']['version_id'],
            (int)$argv[4],$argv[5],$argv[3]);
    }
    $result['actor']=$identity['Arn'];
    $result['checked_at']=gmdate('c');
    fwrite($lock,json_encode($result,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n");
    fflush($lock); fsync($lock);
    echo json_encode(['result'=>'success','record'=>$out]),"\n";
} catch (Throwable $e) {
    if (is_resource($lock)) {
        fwrite($lock,json_encode(['result'=>'failed_or_indeterminate','operation'=>$argv[1],
            'error_type'=>get_class($e),'aws_error_message'=>($e instanceof \Aws\Exception\AwsException ? $e->getAwsErrorMessage() : null),'aws_error_code'=>($e instanceof \Aws\Exception\AwsException ? $e->getAwsErrorCode() : null),'aws_operation'=>($e instanceof \Aws\Exception\AwsException ? $e->getCommand()->getName() : null),'checked_at'=>gmdate('c'),
            'note'=>'Do not blindly retry PUT; inspect the exact key using separate authorized reads.'])."\n");
    }
    fwrite(STDERR,json_encode(['result'=>'failed','error_type'=>get_class($e),'aws_error_message'=>($e instanceof \Aws\Exception\AwsException ? $e->getAwsErrorMessage() : null),'aws_error_code'=>($e instanceof \Aws\Exception\AwsException ? $e->getAwsErrorCode() : null),'aws_operation'=>($e instanceof \Aws\Exception\AwsException ? $e->getCommand()->getName() : null)])."\n");
    exit(2);
} finally {if (is_resource($lock)) {fclose($lock);}}