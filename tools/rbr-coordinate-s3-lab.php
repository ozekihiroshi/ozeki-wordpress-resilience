<?php
declare(strict_types=1);
require __DIR__.'/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
final class RbrBrokerFailure extends RuntimeException {
    public function __construct(private int $status) { parent::__construct('Experiment transport HTTP '.$status); }
    public function getStatusCode(): int { return $this->status; }
}
function rbrBroker(string $journal): array {
    $proc=proc_open(['python3','-B',__DIR__.'/rbr-coordinator-transport.py',$journal],[0=>['pipe','r'],1=>['pipe','w'],2=>['file',$journal.'.stderr','a']],$pipes);
    if (!is_resource($proc)) { throw new RuntimeException('Broker unavailable'); }
    $request=static function(string $op,array $args) use($pipes): array {
        if(isset($args['Body'])) { $args['body64']=base64_encode(stream_get_contents($args['Body']));unset($args['Body']); }
        if(isset($args['ObjectLockRetainUntilDate'])) { $args['ObjectLockRetainUntilDate']=$args['ObjectLockRetainUntilDate']->format(DATE_ATOM); }
        fwrite($pipes[0],json_encode(['operation'=>$op,'args'=>$args],JSON_THROW_ON_ERROR)."\n");fflush($pipes[0]);
        $line=fgets($pipes[1]);if($line===false){throw new RbrBrokerFailure(502);}
        $reply=json_decode($line,true,64,JSON_THROW_ON_ERROR);
        if(!$reply['success']) {throw new RbrBrokerFailure($reply['status']);}
        $r=$reply['result'];
        if(isset($r['body64'])) {$r['Body']=GuzzleHttp\Psr7\Utils::streamFor(base64_decode($r['body64'],true));unset($r['body64']);}
        if(isset($r['LastModified'])) {$r['LastModified']=new DateTimeImmutable($r['LastModified']);}
        if(isset($r['Retention']['RetainUntilDate'])) {$r['Retention']['RetainUntilDate']=new DateTimeImmutable($r['Retention']['RetainUntilDate']);}
        return $r;
    };
    return [$request,static function()use($pipes,$proc):void{fclose($pipes[0]);fclose($pipes[1]);proc_close($proc);}];
}
if(realpath($_SERVER['SCRIPT_FILENAME'])===__FILE__) {
    $o=getopt('',['job:','case:','work:','execute-generated-lab']);$close=null;
    try {
        if(!isset($o['job'],$o['case'],$o['work'],$o['execute-generated-lab']) || !preg_match('/^[a-z0-9-]{1,40}$/D',$o['case'])) {throw new InvalidArgumentException('Explicit generated lab job/case/work required');}
        if(!is_dir($o['work']) || is_link($o['work'])) {throw new InvalidArgumentException('Private existing work directory required');}
        $job=json_decode(file_get_contents($o['job']),true,64,JSON_THROW_ON_ERROR);
        if(($job['site_id']??null)!=='corporate-test') {throw new InvalidArgumentException('Generated corporate-test only');}
        [$request,$close]=rbrBroker($o['work'].'/transport.jsonl');
        $store=new Owr\RbrObjectStore($request,'ceri-link-resilience-lock-lab-121426368082','ap-northeast-1','121426368082',
            'sites/isolated-queue-lab/sets/AWS-c057202610220001/coordinator/'.$o['case'].'/',$o['work'],fn()=>time(),'corporate-test',true);
        echo json_encode((new Owr\RbrGenerationCoordinator($store))->save($job),JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
    } catch(Throwable $e) {fwrite(STDERR,json_encode(['state'=>'failed_or_unknown','error'=>$e->getMessage()])."\n");$code=1;}
    finally {if($close!==null){$close();}}
    exit($code??0);
}
