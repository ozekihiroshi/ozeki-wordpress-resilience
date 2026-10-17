<?php
declare(strict_types=1);
namespace Owr;

/** Version-specific transfer. Caller supplies an authenticated SDK transport. */
final class VersionedAssetStore
{
    public function __construct(private \Closure $request, private string $bucket,
        private string $region, private string $owner, private string $prefix)
    {
        if (!preg_match('~^[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/$~D', $prefix)
            || !preg_match('/^[0-9]{12}$/D', $owner)) {
            throw new \InvalidArgumentException('Invalid storage scope');
        }
    }
    private function key(string $key): array {
        if (!str_starts_with($key, $this->prefix) || strlen($key) <= strlen($this->prefix)
            || !preg_match('~^[A-Za-z0-9_./-]+$~D', $key)
            || in_array('..', explode('/', $key), true)) {
            throw new \InvalidArgumentException('Key outside storage scope');
        }
        return ['Bucket'=>$this->bucket,'Key'=>$key,'ExpectedBucketOwner'=>$this->owner];
    }
    private static function version(mixed $version): string {
        if (!is_string($version) || $version === '' || $version === 'null' || strlen($version)>1024) {
            throw new \RuntimeException('Non-null VersionId required');
        }
        return $version;
    }
    private static function expected(int $size, string $sha): void {
        if ($size<0 || $size>5*1024*1024*1024 || !preg_match('/^[a-f0-9]{64}$/D',$sha)) {
            throw new \InvalidArgumentException('Invalid artifact expectation');
        }
    }
    public function upload(string $path, string $key, int $size, string $sha): array {
        $args=$this->key($key);
        self::expected($size,$sha);
        $stream=fopen($path,'rb');
        if (!$stream) {throw new \RuntimeException('Cannot open artifact');}
        try {
            if (fstat($stream)['size'] !== $size) {throw new \RuntimeException('Size mismatch');}
            $hash=hash_init('sha256'); hash_update_stream($hash,$stream);
            if (hash_final($hash)!==$sha) {throw new \RuntimeException('Hash mismatch');}
            rewind($stream);
            $configuration=($this->request)('GetBucketVersioning',[
                'Bucket'=>$this->bucket,'ExpectedBucketOwner'=>$this->owner]);
            if (($configuration['Status']??null)!=='Enabled') {
                throw new \RuntimeException('Versioning must be enabled');
            }
            $response=($this->request)('PutObject',$args+[
                'Body'=>$stream,'ContentLength'=>$size,'ChecksumSHA256'=>base64_encode(hex2bin($sha)),
                'IfNoneMatch'=>'*','ServerSideEncryption'=>'AES256']);
            $version=self::version($response['VersionId']??null);
        } finally {
            if (is_resource($stream)) {fclose($stream);}
        }
        // A PUT acknowledgement is not independent retrieval evidence.
        return ['schema_version'=>1,'kind'=>'owr-versioned-upload-receipt',
            'locator'=>['kind'=>'s3','bucket'=>$this->bucket,'region'=>$this->region,
                'key'=>$key,'version_id'=>$version],
            'size_bytes'=>$size,'sha256'=>$sha,'observation'=>'put_acknowledged',
            'authenticity'=>'unverified','role_separation'=>'unverified'];
    }
    public function download(string $key, string $version, int $size, string $sha, string $destination): array {
        $args=$this->key($key)+['VersionId'=>self::version($version)];
        self::expected($size,$sha);
        if (file_exists($destination)||is_link($destination)) {
            throw new \RuntimeException('Destination already exists');
        }
        $temporary=dirname($destination).'/.owr-download-'.bin2hex(random_bytes(16));
        $output=fopen($temporary,'x+b');
        if (!$output) {throw new \RuntimeException('Cannot create private download');}
        chmod($temporary,0600);
        try {
            $response=($this->request)('GetObject',$args);
            if (($response['VersionId']??null)!==$version || ($response['ContentLength']??null)!==$size) {
                throw new \RuntimeException('Version or size mismatch');
            }
            $body=$response['Body']; $bytes=0; $hash=hash_init('sha256');
            try {
                while (!$body->eof()) {
                    $chunk=$body->read(1024*1024);
                    if ($chunk==='' && !$body->eof()) {throw new \RuntimeException('Stalled stream');}
                    $bytes+=strlen($chunk);
                    if ($bytes>$size) {throw new \RuntimeException('Oversized stream');}
                    hash_update($hash,$chunk);
                    $offset=0;
                    while ($offset<strlen($chunk)) {
                        $written=fwrite($output,substr($chunk,$offset));
                        if (!$written) {throw new \RuntimeException('Short disk write');}
                        $offset+=$written;
                    }
                }
            } finally {$body->close();}
            if ($bytes!==$size || hash_final($hash)!==$sha) {throw new \RuntimeException('Integrity mismatch');}
            if (!fflush($output)||!fsync($output)) {throw new \RuntimeException('Flush failed');}
            fclose($output); $output=null;
            // Hard link publishes without overwriting a concurrent destination.
            if (!link($temporary,$destination)) {throw new \RuntimeException('Publish failed');}
        } finally {
            if (is_resource($output)) {fclose($output);}
            unlink($temporary);
        }
        return ['kind'=>'owr-versioned-download-observation','schema_version'=>1,
            'locator'=>['kind'=>'s3','bucket'=>$this->bucket,'region'=>$this->region,
                'key'=>$key,'version_id'=>$version],
            'size_bytes'=>$size,'sha256'=>$sha,'observation'=>'download_integrity_checked',
            'authenticity'=>'unverified','role_separation'=>'unverified'];
    }
}