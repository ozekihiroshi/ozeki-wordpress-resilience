<?php
declare(strict_types=1);
namespace Owr\M1;

/** S3 is the authority. The database is never used to discover recovery history. */
final class Store
{
    private static function sourceName(array $a): string {return match($a['content_format']??'markdown'){'comment-json','form-json'=>'source.json','wordpress-block-html'=>'source.html',default=>'source.md'};}
    private static function sourceType(array $a): string {return match($a['content_format']??'markdown'){'comment-json','form-json'=>'application/json','wordpress-block-html'=>'text/html',default=>'text/markdown'};}
    public function __construct(private object $s3, private array $config) {}
    private function args(string $key = ''): array {
        $a = ['Bucket'=>$this->config['bucket']];
        if ($key !== '') $a['Key']=$this->config['prefix'].$key;
        if (!empty($this->config['owner'])) $a['ExpectedBucketOwner']=$this->config['owner'];
        return $a;
    }
    public static function json(array $value): string {
        return json_encode($value, JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
    }
    public function put(string $key, string $body, string $type, ?string $until=null): array {
        $args=$this->args($key)+['Body'=>$body,'ContentType'=>$type,'IfNoneMatch'=>'*',
            'ServerSideEncryption'=>'AES256','ChecksumSHA256'=>base64_encode(hash('sha256',$body,true))];
        if (!empty($this->config['retention_days'])) {
            $args['ObjectLockMode']='GOVERNANCE';
            $args['ObjectLockRetainUntilDate']=new \DateTimeImmutable($until??'+'.(int)$this->config['retention_days'].' days');
        }
        try { $r=$this->s3->putObject($args); }
        catch (\Throwable $error) {
            // A lost response is not permission to overwrite or duplicate an operation.
            try { $r=$this->s3->getObject($this->args($key)); }
            catch (\Throwable $readError) { throw $error; }
            if ((string)$r['Body'] !== $body) throw new \RuntimeException('S3 write failed or key conflict.',0,$error);
        }
        $version=(string)($r['VersionId']??'');
        if ($version==='' || $version==='null') throw new \RuntimeException('S3 versioning must be enabled.');
        return ['key'=>$key,'version'=>$version,'sha256'=>hash('sha256',$body)];
    }
    public function get(array $ref): string {
        if (!isset($ref['key'],$ref['version'],$ref['sha256']) || str_contains($ref['key'],'..') || str_starts_with($ref['key'],'/')) throw new \RuntimeException('Invalid S3 reference.');
        $r=$this->s3->getObject($this->args($ref['key'])+['VersionId'=>$ref['version']]);
        $body=(string)$r['Body'];
        if (!hash_equals($ref['sha256'],hash('sha256',$body))) throw new \RuntimeException('S3 content mismatch.');
        return $body;
    }
    public function history(int $after=0): array {
        $rows=[];$token=null;
        do {
            $a=$this->args()+['Prefix'=>$this->config['prefix'].'history/'];
            if ($after>0) $a['StartAfter']=$this->config['prefix'].sprintf('history/%020d.json',$after);
            if ($token) $a['ContinuationToken']=$token;
            $list=$this->s3->listObjectsV2($a);
            foreach ($list['Contents']??[] as $entry) {
                $key=substr($entry['Key'],strlen($this->config['prefix']));
                if (!preg_match('~^history/[0-9]{20}\.json$~D',$key)) continue;
                $r=$this->s3->getObject($this->args($key));
                $row=json_decode((string)$r['Body'],true,512,JSON_THROW_ON_ERROR);
                if (($row['schema']??'')!=='owr-md-history-1' || $key!==sprintf('history/%020d.json',$row['sequence'])) throw new \RuntimeException('Invalid formal history.');
                $rows[]=$row;
            }
            $token=$list['NextContinuationToken']??null;
        } while ($token);
        usort($rows,fn($a,$b)=>$a['sequence']<=>$b['sequence']);
        return $rows;
    }
    public function siteSnapshots(): array {
        $out=[];$token=null;
        do {$a=$this->args()+['Prefix'=>$this->config['prefix'].'site-snapshots/'];if($token)$a['ContinuationToken']=$token;
            $list=$this->s3->listObjectsV2($a);
            foreach($list['Contents']??[] as $item){$key=substr($item['Key'],strlen($this->config['prefix']));if(!preg_match('~^site-snapshots/[a-f0-9]{64}/manifest\.json$~D',$key))continue;
                $r=$this->s3->getObject($this->args($key));$body=(string)$r['Body'];$m=json_decode($body,true,512,JSON_THROW_ON_ERROR);
                if(($m['schema']??'')!=='owr-site-snapshot-1'||empty($r['VersionId']))throw new \RuntimeException('Invalid site snapshot.');
                $out[]=['ref'=>['key'=>$key,'version'=>$r['VersionId'],'sha256'=>hash('sha256',$body)],'through'=>$m['through'],'origin'=>$m['origin']];
            }$token=$list['NextContinuationToken']??null;
        }while($token);return $out;
    }
    private function applyRows(array $assets, array $rows, int $through): array {
        foreach ($rows as $row) {
            if (!is_int($row['sequence']??null) || $row['sequence']!==$through+1 || ($row['schema']??'')!=='owr-md-history-1'
                || !is_string($row['original']['asset']??null) || !is_array($row['attributes']??null)) throw new \RuntimeException('Formal history is incomplete or invalid; refusing partial site recovery.');
            $assets[$row['original']['asset']]=$row;
            $through=$row['sequence'];
        }
        ksort($assets,SORT_STRING);
        return ['through'=>$through,'assets'=>$assets];
    }
    public function checkpoints(): array {
        $result=[];$token=null;
        do {
            $args=$this->args()+['Prefix'=>$this->config['prefix'].'snapshots/'];
            if ($token) $args['ContinuationToken']=$token;
            $list=$this->s3->listObjectsV2($args);
            foreach ($list['Contents']??[] as $item) {
                $key=substr($item['Key'],strlen($this->config['prefix']));
                if (preg_match('~^snapshots/[0-9]{20}/[a-f0-9]{64}/manifest\.json$~D',$key)) $result[]=$key;
            }
            $token=$list['NextContinuationToken']??null;
        } while ($token);
        sort($result,SORT_STRING);return $result;
    }
    public function recoveryState(?string $checkpoint=null): array {
        $assets=[];$through=0;
        if ($checkpoint!==null) {
            $cp=$this->snapshot($checkpoint);$assets=$cp['assets'];$through=$cp['through'];
        }
        return $this->applyRows($assets,$this->history($through),$through)+['checkpoint'=>$checkpoint];
    }
    public function snapshot(string $key): array {
        if (!preg_match('~^(snapshots/([0-9]{20})/[a-f0-9]{64}/)manifest\.json$~D',$key,$m)) throw new \RuntimeException('Invalid independent snapshot key.');
        $r=$this->s3->getObject($this->args($key));
        if (empty($r['VersionId']) || $r['VersionId']==='null') throw new \RuntimeException('Snapshot requires versioning.');
        $cp=json_decode((string)$r['Body'],true,512,JSON_THROW_ON_ERROR);
        if (($cp['schema']??'')!=='owr-md-snapshot-2' || ($cp['through']??null)!==(int)$m[2]
            || !is_array($cp['assets']??null) || !$cp['assets']
            || !hash_equals((string)($cp['inventory_sha256']??''),hash('sha256',self::json($cp['assets'])))) throw new \RuntimeException('Invalid independent snapshot inventory.');
        foreach ($cp['assets'] as $asset=>$row) {
            if (($row['original']['asset']??null)!==$asset || !is_int($row['sequence']??null) || $row['sequence']<0 || $row['sequence']>$cp['through']) throw new \RuntimeException('Invalid snapshot asset.');
            foreach (['source','metadata'] as $type) {
                $ref=$row['original'][$type]??[];
                if (!str_starts_with((string)($ref['key']??''),$m[1].'assets/')) throw new \RuntimeException('Snapshot depends on an earlier resource.');
            }
        }
        return $cp;
    }
    /** Shared builder: input raw files may originate in trusted WP or S3; output is always independent. */
    public function saveSnapshot(array $materials,int $through,string $origin): array {
        if (!$materials || $through<0 || !in_array($origin,['administrator_initial','confirmed_s3'],true)) throw new \RuntimeException('Invalid snapshot input.');
        ksort($materials,SORT_STRING);$identity=[];
        foreach ($materials as $asset=>$item) {
            if (!preg_match('/^[a-zA-Z0-9-]+$/D',(string)$asset) || !is_string($item['source']??null)
                || strlen($item['source'])>5*1024*1024 || !preg_match('//u',$item['source']) || str_contains($item['source'],"\0")
                || !is_array($item['row']['attributes']??null)) throw new \RuntimeException('Invalid snapshot material.');
            $identity[$asset]=['sha256'=>hash('sha256',$item['source']),'attributes'=>$item['row']['attributes'],'sequence'=>$item['row']['sequence']];
        }
        $base=sprintf('snapshots/%020d/',$through).hash('sha256',self::json($identity)).'/';
        $key=$base.'manifest.json';
        if (in_array($key,$this->checkpoints(),true)) { $this->snapshot($key);return ['key'=>$key,'through'=>$through,'assets'=>count($materials),'unchanged'=>true]; }
        // A persisted intent fixes timestamps/retention across a partially completed attempt.
        $planKey=$base.'plan.json';$plan=null;
        try { $r=$this->s3->getObject($this->args($planKey));$plan=json_decode((string)$r['Body'],true,512,JSON_THROW_ON_ERROR); }
        catch (\Throwable $e) {
            $missing=($e instanceof \Aws\Exception\AwsException && in_array($e->getAwsErrorCode(),['NoSuchKey','NotFound'],true)) || $e->getCode()===404;
            if (!$missing) throw $e;
        }
        if ($plan===null) {
            $plan=['schema'=>'owr-md-snapshot-plan-2','through'=>$through,'origin'=>$origin,'created_at'=>gmdate('c'),
                'retain_until'=>!empty($this->config['retention_days'])?gmdate('c',time()+86400*(int)$this->config['retention_days']):null];
            $this->put($planKey,self::json($plan),'application/json',$plan['retain_until']);
        }
        if (($plan['schema']??'')!=='owr-md-snapshot-plan-2' || $plan['through']!==$through || $plan['origin']!==$origin
            || ($plan['retain_until']!==null && strtotime($plan['retain_until'])<=time())) throw new \RuntimeException('Invalid or expired snapshot attempt.');
        $assets=[];
        foreach ($materials as $asset=>$item) {
            $row=$item['row'];$where=$base.'assets/'.$asset.'/';
            foreach($row['attributes']['media']??[] as $index=>$media)foreach($media['files'] as $path=>$ref){
                SiteSnapshot::safePath($path);
                $row['attributes']['media'][$index]['files'][$path]=$this->put($where.'media/'.$path,$this->get($ref),'application/octet-stream',$plan['retain_until']);
            }
            $row['original']=['schema'=>'owr-md-original-1','asset'=>$asset,'operation'=>basename(rtrim($base,'/')),'retain_until'=>$plan['retain_until'],
                'source'=>$this->put($where.self::sourceName($row['attributes']),$item['source'],self::sourceType($row['attributes']).'; charset=utf-8',$plan['retain_until']),
                'metadata'=>$this->put($where.'metadata.json',self::json($row['attributes']),'application/json',$plan['retain_until'])];
            // Read back exact newly saved versions before adopting the snapshot.
            $this->get($row['original']['source']);$this->get($row['original']['metadata']);$assets[$asset]=$row;
        }
        $body=['schema'=>'owr-md-snapshot-2','through'=>$through,'origin'=>$origin,'created_at'=>$plan['created_at'],'retain_until'=>$plan['retain_until'],
            'assets'=>$assets,'inventory_sha256'=>hash('sha256',self::json($assets))];
        $ref=$this->put($key,self::json($body),'application/json',$plan['retain_until']);
        $this->get($ref);
        return $ref+['through'=>$through,'assets'=>count($assets),'unchanged'=>false];
    }
    public function createInitialSnapshot(array $materials): array {
        if ($this->history()) throw new \RuntimeException('Initial snapshot requires an unused history stream; do not reset an existing stream.');
        $keys=$this->checkpoints();
        if ($keys) {
            if (count($keys)!==1) throw new \RuntimeException('Initial state already exists.');
            $cp=$this->snapshot($keys[0]);
            if ($cp['through']!==0 || $cp['origin']!=='administrator_initial' || count($cp['assets'])!==count($materials)) throw new \RuntimeException('Initial state already exists.');
            foreach ($materials as $id=>$item) if (!isset($cp['assets'][$id]) || $cp['assets'][$id]['attributes']!==$item['row']['attributes'] || $this->get($cp['assets'][$id]['original']['source'])!==$item['source']) throw new \RuntimeException('Initial state changed; refusing reset.');
            return ['key'=>$keys[0],'through'=>0,'assets'=>count($materials),'unchanged'=>true];
        }
        return $this->saveSnapshot($materials,0,'administrator_initial');
    }
    public function createCheckpoint(): array {
        $keys=$this->checkpoints();$base=$keys?end($keys):null;
        $state=$this->recoveryState($base);$materials=[];
        if (!$state['assets']) throw new \RuntimeException('No confirmed assets to checkpoint.');
        if ($base!==null && $this->snapshot($base)['through']===$state['through']) return ['key'=>$base,'through'=>$state['through'],'assets'=>count($state['assets']),'unchanged'=>true];
        foreach ($state['assets'] as $asset=>$row) {
            $this->get($row['original']['metadata']);
            $materials[$asset]=['row'=>$row,'source'=>$this->get($row['original']['source'])];
        }
        return $this->saveSnapshot($materials,$state['through'],'confirmed_s3');
    }
    public function latestState(): array {
        $keys=$this->checkpoints();return $this->recoveryState($keys?end($keys):null);
    }
    /** Read-only cleanup preview. A timestamp fixes the policy across preview/execute. */
    public function cleanupPlan(int $cutoff): array {
        if ($cutoff<0 || $cutoff>time()) throw new \RuntimeException('Invalid cleanup cutoff.');
        $keys=$this->checkpoints();
        if (!$keys) throw new \RuntimeException('A complete Checkpoint is required before cleanup.');
        $latest=end($keys);$keep=[];$protected=[];$floor=PHP_INT_MAX;
        foreach ($keys as $key) {
            $cp=$this->snapshot($key);$created=strtotime((string)($cp['created_at']??''));
            if ($created===false) throw new \RuntimeException('Invalid snapshot creation time.');
            if ($key===$latest || $created>$cutoff) {
                $keep[]=$key;$floor=min($floor,$cp['through']);
                foreach ($cp['assets'] as $row) foreach (['source','metadata'] as $type) $this->get($row['original'][$type]);
            }
        }
        // Every intermediate operation after the oldest retained baseline is required.
        $this->recoveryState($keep[0]);
        $versions=[];$keyMarker=null;$versionMarker=null;
        do {
            $args=$this->args()+['Prefix'=>$this->config['prefix']];
            if ($keyMarker!==null) $args['KeyMarker']=$keyMarker;
            if ($versionMarker!==null) $args['VersionIdMarker']=$versionMarker;
            $list=$this->s3->listObjectVersions($args);
            foreach ($list['DeleteMarkers']??[] as $v) {
                $key=substr($v['Key'],strlen($this->config['prefix']));
                if (preg_match('~^(snapshots|history|originals)/~',$key)) throw new \RuntimeException('Delete markers require separate review; cleanup stopped.');
            }
            foreach ($list['Versions']??[] as $v) {
                if (!str_starts_with($v['Key'],$this->config['prefix'])) throw new \RuntimeException('Version outside configured prefix.');
                $key=substr($v['Key'],strlen($this->config['prefix']));
                if (!preg_match('~^(snapshots|history|originals)/~',$key)) continue;
                if (isset($versions[$key]) || empty($v['VersionId']) || $v['VersionId']==='null') throw new \RuntimeException('Unexpected mutable or unversioned key; cleanup stopped.');
                $date=$v['LastModified'] instanceof \DateTimeInterface?$v['LastModified']->getTimestamp():strtotime((string)$v['LastModified']);
                if ($date===false) throw new \RuntimeException('Missing object age.');
                $versions[$key]=['key'=>$key,'version'=>$v['VersionId'],'modified'=>$date];
            }
            $keyMarker=$list['NextKeyMarker']??null;$versionMarker=$list['NextVersionIdMarker']??null;
        } while (!empty($list['IsTruncated']));
        ksort($versions,SORT_STRING);
        $historyDelete=[];
        foreach ($this->history() as $row) {
            $key=sprintf('history/%020d.json',$row['sequence']);
            if (!isset($versions[$key])) throw new \RuntimeException('History inventory changed.');
            if ($row['sequence']<=$floor && $versions[$key]['modified']<=$cutoff) $historyDelete[$key]=true;
            else {
                $protected[$key]=true;
                foreach (['source','metadata'] as $type) {
                    $ref=$row['original'][$type];$this->get($ref);$protected[$ref['key']]=true;
                }
            }
        }
        $delete=[];$blocked=[];$lockEnabled=false;
        try {$lock=$this->s3->getObjectLockConfiguration($this->args());$lockEnabled=($lock['ObjectLockConfiguration']['ObjectLockEnabled']??'')==='Enabled';}
        catch (\Throwable $e) {
            if (!($e instanceof \Aws\Exception\AwsException) || $e->getAwsErrorCode()!=='ObjectLockConfigurationNotFoundError') throw $e;
        }
        foreach ($versions as $key=>$v) {
            if (isset($protected[$key]) || $v['modified']>$cutoff) continue;
            $eligible=isset($historyDelete[$key]);
            if (preg_match('~^(snapshots/([0-9]{20})/[a-f0-9]{64}/)(?:manifest\.json|plan\.json|assets/[a-zA-Z0-9-]+/(?:source\.md|metadata\.json))$~D',$key,$m)) {
                $eligible=(int)$m[2]<=$floor && !in_array($m[1].'manifest.json',$keep,true);
            } elseif (preg_match('~^originals/[a-zA-Z0-9-]+/[a-zA-Z0-9-]+/(?:source\.md|metadata\.json)$~D',$key)) $eligible=true;
            if (!$eligible) continue;
            $head=$this->s3->headObject($this->args($key)+['VersionId'=>$v['version']]);
            // HEAD can omit lock headers when the caller lacks read-lock rights.
            // Explicit reads must succeed instead of treating hidden state as OFF.
            $retention=$lockEnabled?$this->s3->getObjectRetention($this->args($key)+['VersionId'=>$v['version']]):[];
            $hold=$lockEnabled?$this->s3->getObjectLegalHold($this->args($key)+['VersionId'=>$v['version']]):[];
            $until=$retention['Retention']['RetainUntilDate']??null;
            $until=$until instanceof \DateTimeInterface?$until->getTimestamp():($until===null?0:strtotime((string)$until));
            if ($until===false) throw new \RuntimeException('Invalid retention timestamp.');
            if (($hold['LegalHold']['Status']??'OFF')!=='OFF' || $until>time()) $blocked[]=$v+['reason'=>'Object Lock or Legal Hold'];
            else $delete[]=$v;
        }
        // Retire discoverable old records before deleting their data. A new plan can
        // safely discover orphaned old data if execution is interrupted here.
        usort($delete,static function($a,$b){
            $rank=static fn($k)=>str_starts_with($k,'history/')?0:(str_ends_with($k,'/manifest.json')?1:2);
            return [$rank($a['key']),$a['key']]<=>[$rank($b['key']),$b['key']];
        });
        $plan=['cutoff'=>$cutoff,'keep'=>$keep,'through'=>$floor,'delete'=>$delete,'blocked'=>$blocked];
        // All versions, including retained ones, invalidate a stale preview.
        $plan['hash']=hash('sha256',self::json([$this->config['bucket'],$this->config['prefix'],$plan,$versions]));
        return $plan;
    }
    /** Caller must hold the same single-writer lock as publication/Checkpoint. */
    public function cleanup(int $cutoff,string $expectedHash): array {
        $plan=$this->cleanupPlan($cutoff);
        if (!hash_equals($plan['hash'],$expectedHash)) throw new \RuntimeException('Storage changed; preview cleanup again.');
        if ($plan['blocked']) throw new \RuntimeException('Object Lock or Legal Hold blocks cleanup; nothing deleted.');
        $done=[];
        foreach ($plan['delete'] as $v) {
            try {
                $this->s3->deleteObject($this->args($v['key'])+['VersionId'=>$v['version']]);
                $done[]=$v;
            } catch (\Throwable $e) {
                return ['ok'=>false,'deleted'=>$done,'uncertain'=>$v,'error'=>$e->getMessage(),'resume'=>'Rebuild the preview from S3; never bypass retention.'];
            }
        }
        return ['ok'=>true,'deleted'=>$done,'retained'=>$plan['keep']];
    }
    public function prepare(string $asset, string $operation, string $source, array $attributes): array {
        $base='originals/'.$asset.'/'.$operation.'/';
        $until=!empty($this->config['retention_days'])?gmdate('c',time()+86400*(int)$this->config['retention_days']):null;
        return ['schema'=>'owr-md-original-1','asset'=>$asset,'operation'=>$operation,
            'retain_until'=>$until,
            'source'=>$this->put($base.self::sourceName($attributes),$source,self::sourceType($attributes).'; charset=utf-8',$until),
            'metadata'=>$this->put($base.'metadata.json',self::json($attributes),'application/json',$until)];
    }
    public function commit(array $record): void {
        $this->put(sprintf('history/%020d.json',$record['sequence']),self::json($record),'application/json',$record['original']['retain_until']);
    }
}
