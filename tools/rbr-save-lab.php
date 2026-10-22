<?php
/** Opt-in lab-only SDK entry. No credentials in job/config, no production bucket support. */
declare(strict_types=1);
require __DIR__.'/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
$options=getopt('', ['config:', 'job:', 'execute-lab']);
$coordinator=null;$scratch=null;
try {
    if (!isset($options['config'],$options['job']) || !array_key_exists('execute-lab',$options)) {
        throw new InvalidArgumentException('Usage: php tools/rbr-save-lab.php --config=private-config.json --job=job.json --execute-lab');
    }
    $config=json_decode(file_get_contents($options['config']),true,32,JSON_THROW_ON_ERROR);
    $job=json_decode(file_get_contents($options['job']),true,64,JSON_THROW_ON_ERROR);
    if (($config['environment']??null)!=='synthetic-lab'
        || !preg_match('/^owr-rbr-lab-[a-z0-9-]+$/D',$config['bucket']??'')
        || !preg_match('/^[a-z]{2}-[a-z]+-[0-9]+$/D',$config['region']??'')
        || !preg_match('/^[0-9]{12}$/D',$config['owner']??'')
        || !preg_match('/^[A-Za-z0-9_-]{1,80}$/D',$job['site_id']??'')
        || array_diff(array_keys($config),['environment','bucket','region','owner'])) {
        throw new InvalidArgumentException('Dedicated synthetic-lab config required; no endpoint/credentials override');
    }
    $scratch=sys_get_temp_dir().'/owr-rbr-sdk-'.bin2hex(random_bytes(16));mkdir($scratch,0700);
    $sdk=new Aws\S3\S3Client(['version'=>'latest','region'=>$config['region'],
        'retries'=>0,'http'=>['connect_timeout'=>5,'timeout'=>30]]);
    $request=static fn(string $op,array $args): array=>$sdk->execute($sdk->getCommand($op,$args))->toArray();
    $store=new Owr\RbrObjectStore($request,$config['bucket'],$config['region'],$config['owner'],
        'sites/'.$job['site_id'].'/',$scratch,static fn():int=>time());
    $coordinator=new Owr\RbrGenerationCoordinator($store);
    echo json_encode($coordinator->save($job),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
} catch(Throwable $e) {
    // Do not echo SDK exception URLs, credentials or request bodies.
    fwrite(STDERR,json_encode(['state'=>'failed_or_unknown','last_confirmed_stage'=>$coordinator?->lastConfirmedStage()??'not_started',
        'action'=>'Review access/configuration and reconcile the same operation; do not delete or blindly resend.',
        'error_type'=>get_class($e)],JSON_PRETTY_PRINT)."\n");
    exitCodeRbr(1);
} finally {
    if($scratch!==null && is_dir($scratch)) { foreach(glob($scratch.'/*')as$p){if(is_file($p)){unlink($p);}}rmdir($scratch); }
}
function exitCodeRbr(int $code): void { $GLOBALS['rbr_exit_code']=$code; }
exit($GLOBALS['rbr_exit_code']??0);
