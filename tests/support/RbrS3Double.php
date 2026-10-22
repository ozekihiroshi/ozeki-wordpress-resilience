<?php
declare(strict_types=1);
use GuzzleHttp\Psr7\Utils;
final class RbrS3Failure extends RuntimeException {
    public function __construct(private int $status) { parent::__construct('Synthetic S3 failure '.$status); }
    public function getStatusCode(): int { return $this->status; }
}
/** Filesystem-backed atomic S3 contract double. No AWS SDK client, network or credentials. */
final class RbrS3Double {
    public int $days=36;
    public ?string $failPutContains=null;
    public ?string $loseResponseContains=null;
    public ?string $denyReadContains=null;
    public ?string $corruptContains=null;
    public bool $barrier=false;
    public int $commitDelay=0;
    public int $clockSkew=0;
    public array $calls=[];
    public function __construct(public string $root, public int $now) {}
    private function path(string $key): string { return $this->root.'/objects/'.hash('sha256',$key).'.json'; }
    public function objects(): array {
        $out=[]; foreach(glob($this->root.'/objects/*.json') as $p) { $out[]=json_decode(file_get_contents($p),true); }
        return $out;
    }
    public function age(string $key, int $until): void {
        $p=$this->path($key); $j=json_decode(file_get_contents($p),true);$j['until']=$until;
        file_put_contents($p,json_encode($j,JSON_THROW_ON_ERROR));
    }
    public function request(string $op,array $a): array {
        $this->calls[]=$op;
        if (($a['Bucket']??null)!=='owr-offline-rbr-test' || ($a['ExpectedBucketOwner']??null)!=='123456789012') {
            throw new RuntimeException('Unexpected scope');
        }
        if ($op==='GetBucketVersioning') { return ['Status'=>'Enabled']; }
        if ($op==='GetObjectLockConfiguration') { return ['ObjectLockConfiguration'=>['ObjectLockEnabled'=>'Enabled',
            'Rule'=>['DefaultRetention'=>['Mode'=>'GOVERNANCE','Days'=>$this->days]]]]; }
        $key=$a['Key'];
        if (!str_starts_with($key,'sites/corporate-test/')) { throw new RuntimeException('Scope escaped'); }
        if ($op==='PutObject') {
            if (($a['IfNoneMatch']??null)!=='*' || isset($a['ObjectLockRetainUntilDate'])) {
                throw new RuntimeException('Unconditional write or retention override');
            }
            if ($this->failPutContains!==null && str_contains($key,$this->failPutContains)) { throw new RbrS3Failure(503); }
            if ($this->barrier && str_contains($key,'/commits/')) {
                touch($this->root.'/barrier-'.getmypid()); $end=microtime(true)+5;
                while (count(glob($this->root.'/barrier-*'))<2 && microtime(true)<$end) { usleep(10000); }
                if (count(glob($this->root.'/barrier-*'))<2) { throw new RuntimeException('Race barrier timed out'); }
            }
            if (str_contains($key,'/commits/')) { $this->now+=$this->commitDelay; }
            $raw=stream_get_contents($a['Body']);
            if (strlen($raw)!==$a['ContentLength'] || base64_encode(hash('sha256',$raw,true))!==$a['ChecksumSHA256']) {
                throw new RuntimeException('Checksum mismatch');
            }
            $lock=fopen($this->root.'/mutex','c');flock($lock,LOCK_EX);
            try {
                if (file_exists($this->path($key))) { throw new RbrS3Failure(412); }
                $record=['key'=>$key,'version'=>bin2hex(random_bytes(12)),'raw'=>base64_encode($raw),
                    'stored'=>$this->now,'until'=>$this->now+$this->days*86400];
                $temp=$this->path($key).'.tmp-'.getmypid();
                file_put_contents($temp,json_encode($record,JSON_THROW_ON_ERROR));rename($temp,$this->path($key));
            } finally { flock($lock,LOCK_UN);fclose($lock); }
            if ($this->loseResponseContains!==null && str_contains($key,$this->loseResponseContains)) {
                $this->loseResponseContains=null;throw new RbrS3Failure(504);
            }
            return ['VersionId'=>$record['version']];
        }
        if ($this->denyReadContains!==null && str_contains($key,$this->denyReadContains)) { throw new RbrS3Failure(403); }
        if (!file_exists($this->path($key))) { throw new RbrS3Failure(404); }
        $record=json_decode(file_get_contents($this->path($key)),true);
        if (isset($a['VersionId']) && $a['VersionId']!==$record['version']) { throw new RbrS3Failure(404); }
        $raw=base64_decode($record['raw']);
        if ($op==='GetObjectRetention') { return ['Retention'=>['Mode'=>'GOVERNANCE',
            'RetainUntilDate'=>new DateTimeImmutable('@'.$record['until'])]]; }
        $result=['VersionId'=>$record['version'],'ContentLength'=>strlen($raw),
            'LastModified'=>new DateTimeImmutable('@'.$record['stored']),
            '@metadata'=>['headers'=>['date'=>gmdate('D, d M Y H:i:s \G\M\T',$this->now+$this->clockSkew)]]];
        if ($op==='HeadObject') { return $result; }
        if ($op==='GetObject') {
            if ($this->corruptContains!==null && str_contains($key,$this->corruptContains)) { $raw=str_repeat('x',strlen($raw)); }
            return $result+['Body'=>Utils::streamFor($raw)];
        }
        throw new RuntimeException('Forbidden/unknown operation '.$op);
    }
}
