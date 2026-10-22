<?php
declare(strict_types=1);
namespace Owr;

/** S3 adapter for the small RBR contract. No retention-write/delete operations. */
final class RbrObjectStore
{
    private VersionedAssetStore $transfer;
    public function __construct(private \Closure $request, private string $bucket,
        private string $region, private string $owner, private string $prefix,
        private string $scratch, private \Closure $clock, private ?string $logicalSite = null,
        private bool $explicitRetention = false)
    {
        if (!is_dir($scratch) || is_link($scratch) || !is_writable($scratch)) {
            throw new \InvalidArgumentException('Private scratch directory required');
        }
        if (($logicalSite===null && !preg_match('~^sites/([A-Za-z0-9_-]{1,80})/$~D',$prefix))
            || ($logicalSite!==null && (!preg_match('/^[A-Za-z0-9_-]{1,80}$/D',$logicalSite)
                || !preg_match('~^sites/(?:[A-Za-z0-9_-]+/)+$~D',$prefix)))) {
            throw new \InvalidArgumentException('Independent RBR site prefix required');
        }
        $transferRequest=function(string $op,array $args): array {
            if ($op==='PutObject' && $this->explicitRetention) {
                $args['ObjectLockMode']='GOVERNANCE';
                $args['ObjectLockRetainUntilDate']=new \DateTimeImmutable('@'.($this->now()+36*86400));
            }
            return ($this->request)($op,$args);
        };
        $this->transfer = new VersionedAssetStore($transferRequest, $bucket, $region, $owner, $prefix);
    }
    public function siteId(): string { return $this->logicalSite ?? explode('/', $this->prefix)[1]; }
    public function now(): int { return ($this->clock)(); }
    public function key(string $relative): string {
        if (!preg_match('~^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_.-]+)*$~D', $relative)
            || in_array('..', explode('/', $relative), true)) {
            throw new \InvalidArgumentException('Invalid RBR key');
        }
        return $this->prefix.$relative;
    }
    private function args(string $key): array {
        if (!str_starts_with($key, $this->prefix)
            || $this->key(substr($key, strlen($this->prefix))) !== $key) {
            throw new \InvalidArgumentException('Foreign key');
        }
        return ['Bucket'=>$this->bucket, 'Key'=>$key, 'ExpectedBucketOwner'=>$this->owner];
    }
    public function preflight(): void {
        $scope=['Bucket'=>$this->bucket, 'ExpectedBucketOwner'=>$this->owner];
        $v=($this->request)('GetBucketVersioning', $scope);
        $l=($this->request)('GetObjectLockConfiguration', $scope);
        $c=$l['ObjectLockConfiguration']??[];
        $d=$c['Rule']['DefaultRetention']??[];
        if (($v['Status']??null)!=='Enabled' || ($c['ObjectLockEnabled']??null)!=='Enabled'
            || (!$this->explicitRetention && (($d['Mode']??null)!=='GOVERNANCE'
                || ($d['Days']??null)!==36 || isset($d['Years'])))) {
            throw new \RuntimeException('RBR requires dedicated 36-day governance default');
        }
    }

    private static function missing(\Throwable $e): bool {
        return method_exists($e,'getStatusCode') && $e->getStatusCode()===404;
    }
    private function descriptor(string $key, array $head): array {
        $version=$head['VersionId']??null; $size=$head['ContentLength']??null;
        if (!is_string($version) || $version==='' || $version==='null'
            || !is_int($size) || $size<0 || $size>8*1024*1024) {
            throw new \RuntimeException('Invalid or oversized stored version');
        }
        $date=$head['@metadata']['headers']['date']??null;
        $server=is_string($date)?strtotime($date):false;
        if ($server===false || abs($server-$this->now())>300) {
            throw new \RuntimeException('S3 clock unavailable or skewed');
        }
        $stored=$head['LastModified']??null;
        if (!$stored instanceof \DateTimeInterface) { throw new \RuntimeException('Missing server stored time'); }
        return ['stored_at'=>$stored->getTimestamp(),'locator'=>['kind'=>'s3','bucket'=>$this->bucket,'region'=>$this->region,
            'key'=>$key,'version_id'=>$version], 'size_bytes'=>$size];
    }
    /** Locate latest only to reconcile a deterministic create-only key. Never fallback on 403. */
    public function locate(string $key): ?array {
        try { $head=($this->request)('HeadObject',$this->args($key)); }
        catch (\Throwable $e) { if (self::missing($e)) { return null; } throw $e; }
        return $this->descriptor($key,$head);
    }
    /** Discover bounded immutable record; hash is observed, not a signature/authenticity claim. */
    public function record(string $key): ?array {
        $ref=$this->locate($key); if ($ref===null) { return null; }
        if ($ref['size_bytes']>1024*1024) { throw new \RuntimeException('Record too large'); }
        $r=($this->request)('GetObject',$this->args($key)+['VersionId'=>$ref['locator']['version_id']]);
        $stream=$r['Body']; $raw='';
        try {
            if (($r['VersionId']??null)!==$ref['locator']['version_id']
                || ($r['ContentLength']??null)!==$ref['size_bytes']) { throw new \RuntimeException('Record version mismatch'); }
            while (!$stream->eof()) {
                $chunk=$stream->read(65536);
                if ($chunk===''&&!$stream->eof()) { throw new \RuntimeException('Stalled record'); }
                $raw.=$chunk;
                if (strlen($raw)>$ref['size_bytes']) { throw new \RuntimeException('Oversized record'); }
            }
        } finally { $stream->close(); }
        if (strlen($raw)!==$ref['size_bytes']) { throw new \RuntimeException('Short record'); }
        $ref['sha256']=hash('sha256',$raw); $ref['retain_until']=$this->protection($ref);
        $data=json_decode($raw,true,64,JSON_THROW_ON_ERROR);
        if (!is_array($data)) { throw new \RuntimeException('Invalid record'); }
        return ['reference'=>$ref,'data'=>$data];
    }
    private function scoped(array $ref): array {
        $l=$ref['locator']??[];
        if (($l['bucket']??null)!==$this->bucket || ($l['region']??null)!==$this->region
            || ($l['kind']??null)!=='s3' || !is_string($l['key']??null)
            || !is_string($l['version_id']??null) || $l['version_id']==='' || $l['version_id']==='null'
            || !is_int($ref['size_bytes']??null) || $ref['size_bytes']<0 || $ref['size_bytes']>8*1024*1024
            || !is_string($ref['sha256']??null) || !preg_match('/^[a-f0-9]{64}$/D',$ref['sha256'])) {
            throw new \InvalidArgumentException('Invalid fixed-version reference');
        }
        return $this->args($l['key'])+['VersionId'=>$l['version_id']];
    }
    public function observation(array $ref): array {
        $a=$this->scoped($ref);
        $head=($this->request)('HeadObject',$a);
        $seen=$this->descriptor($a['Key'],$head);
        if ($seen['locator']['version_id']!==$a['VersionId'] || $seen['size_bytes']!==$ref['size_bytes']) {
            throw new \RuntimeException('Fixed-version mismatch');
        }
        $ret=($this->request)('GetObjectRetention',$a);
        $ret=$ret['Retention']??[]; $until=$ret['RetainUntilDate']??null;
        if (($ret['Mode']??null)!=='GOVERNANCE' || !$until instanceof \DateTimeInterface) {
            throw new \RuntimeException('Fixed-version governance retention missing');
        }
        return ['retain_until'=>$until->getTimestamp(),'stored_at'=>$seen['stored_at']];
    }
    public function protection(array $ref): int {
        return $this->observation($ref)['retain_until'];
    }
    public function download(array $ref, string $path): void {
        $this->scoped($ref);
        $this->transfer->download($ref['locator']['key'],$ref['locator']['version_id'],
            $ref['size_bytes'],$ref['sha256'],$path);
    }
    public function bytes(array $ref): string {
        $p=$this->scratch.'/read-'.bin2hex(random_bytes(16));
        try { $this->download($ref,$p); return (string)file_get_contents($p); }
        finally { if (is_file($p)) { unlink($p); } }
    }
    public function json(array $ref): array {
        $value=json_decode($this->bytes($ref),true,64,JSON_THROW_ON_ERROR);
        if (!is_array($value)) { throw new \RuntimeException('Expected JSON object'); }
        return $value;
    }
    /** Returns existing exact bytes on retries, or fails; no unconditional resend. */
    public function ensure(string $key, string $path, int $size, string $sha): array {
        if ($size<0 || $size>8*1024*1024 || !preg_match('/^[a-f0-9]{64}$/D',$sha)) {
            throw new \InvalidArgumentException('Invalid original expectation');
        }
        $ref=$this->locate($key);
        if ($ref===null) {
            if (!is_file($path) || is_link($path) || filesize($path)!==$size || hash_file('sha256',$path)!==$sha) {
                throw new \InvalidArgumentException('Missing or changed local original');
            }
            try { $ref=$this->transfer->upload($path,$key,$size,$sha); }
            catch (\Throwable $e) {
                // Includes successful PUT with lost response. A read failure propagates unknown.
                $ref=$this->locate($key);
                if ($ref===null) { throw $e; }
            }
        }
        if ($ref['size_bytes']!==$size) { throw new \RuntimeException('Immutable key content conflict'); }
        $ref=['locator'=>$ref['locator'],'size_bytes'=>$size,'sha256'=>$sha];
        $this->bytes($ref); // Verify independently; checksum metadata alone is insufficient.
        $observation=$this->observation($ref);
        return ['stored_at'=>$observation['stored_at'],'locator'=>$ref['locator'],
            'size_bytes'=>$size,'sha256'=>$sha,'retain_until'=>$observation['retain_until']];
    }
    public function ensureBytes(string $key, string $body): array {
        $p=$this->scratch.'/write-'.bin2hex(random_bytes(16));
        $h=fopen($p,'x+b'); if (!$h) { throw new \RuntimeException('Scratch creation failed'); }
        chmod($p,0600);
        try {
            if (fwrite($h,$body)!==strlen($body) || !fflush($h)) { throw new \RuntimeException('Scratch write failed'); }
            fclose($h); $h=null;
            return $this->ensure($key,$p,strlen($body),hash('sha256',$body));
        } finally { if (is_resource($h)) { fclose($h); } if (is_file($p)) { unlink($p); } }
    }
    public function protectedOriginal(array $asset, string $operation, int $required): array {
        if (isset($asset['existing'])) {
            $old=$asset['existing'];
            if ($old['sha256']!==$asset['sha256'] || $old['size_bytes']!==$asset['size_bytes']) {
                throw new \InvalidArgumentException('Source reference changed original identity');
            }
            $until=$this->protection($old);
            if ($until >= $required) {
                $this->bytes($old); $old['retain_until']=$until; return $old;
            }
            $p=$this->scratch.'/copy-'.bin2hex(random_bytes(16));
            try {
                $this->download($old,$p);
                $new=$this->ensure($this->key('originals/'.$asset['id'].'/'.$asset['revision'].'/copies/'.$operation),
                    $p,$asset['size_bytes'],$asset['sha256']);
            } finally { if (is_file($p)) { unlink($p); } }
            $new['copied_from']=['locator'=>$old['locator'],'sha256'=>$old['sha256']];
        } else {
            $new=$this->ensure($this->key('originals/'.$asset['id'].'/'.$asset['revision'].'/source'),
                $asset['path'],$asset['size_bytes'],$asset['sha256']);
        }
        if ($new['retain_until']<$required) { throw new \RuntimeException('Protection too short; generation not committed'); }
        return $new;
    }
}
