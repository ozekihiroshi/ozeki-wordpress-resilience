<?php
declare(strict_types=1);
namespace Owr\M1;
require_once __DIR__.'/AssetFormat.php';
require_once __DIR__.'/GfsPolicy.php';

/** S3 is the authority. The database is never used to discover recovery history. */
final class Store
{
    private static function sourceName(array $a): string {return match($a['content_format']??'markdown'){'comment-json','form-json','member-json','table-json','native-state-json'=>'source.json','wordpress-block-html'=>'source.html',default=>'source.md'};}
    private static function sourceType(array $a): string {return match($a['content_format']??'markdown'){'comment-json','form-json','member-json','table-json','native-state-json'=>'application/json','wordpress-block-html'=>'text/html',default=>'text/markdown'};}
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
    /** Disabled retention remains explicit; never silently claim deletion protection. */
    public function requiredRetentionUntil(): ?string {
        $days=(int)($this->config['retention_days']??0);
        if($days<=0)return null;
        // Five minutes to finish confirmation; a longer operation must be retried.
        return gmdate('c',time()+$days*86400+300);
    }
    public function assertRetentionWindow(?string $until): void {
        if($until===null)return;
        $days=(int)($this->config['retention_days']??0);
        if(strtotime($until)<time()+$days*86400)throw new \RuntimeException('Retention confirmation window expired; retry the operation.');
    }
    /** Extend only this fixed version; never shorten, change an existing mode or bypass Governance. */
    public function ensureRetention(array $ref,?string $until): void {
        if($until===null)return;
        if(empty($ref['key'])||empty($ref['version'])||$ref['version']==='null'||str_contains($ref['key'],'..')||str_starts_with($ref['key'],'/'))throw new \RuntimeException('Invalid retention reference.');
        $target=strtotime($until);if($target===false||$target<=time())throw new \RuntimeException('Invalid required retention deadline.');
        $args=$this->args($ref['key'])+['VersionId'=>$ref['version']];
        $read=function()use($args): array{
            $r=$this->s3->getObjectRetention($args);$ret=$r['Retention']??[];$mode=$ret['Mode']??null;$date=$ret['RetainUntilDate']??null;
            if(!$ret)return [null,0];
            $time=$date instanceof \DateTimeInterface?$date->getTimestamp():(is_string($date)?strtotime($date):false);
            if(!in_array($mode,['GOVERNANCE','COMPLIANCE'],true)||$time===false)throw new \RuntimeException('Invalid stored retention information.');
            return [$mode,$time];
        };
        try{
            [$mode,$current]=$read();if($current>=$target)return;
            $this->s3->putObjectRetention($args+['Retention'=>['Mode'=>$mode??'GOVERNANCE','RetainUntilDate'=>new \DateTimeImmutable($until)]]);
            [, $actual]=$read();if($actual<$target)throw new \RuntimeException('Retention remains shorter than required after extension.');
        }catch(\Throwable $e){throw new \RuntimeException('Retention check/extension failed: '.$ref['key'].' — '.$e->getMessage(),0,$e);}
    }
    /** References in original indexes and structured adapter payloads share the same policy. */
    public function retainReferences(array $value,?string $until,array &$seen=[]): void {
        if($until===null)return;
        if(isset($value['key'],$value['version'],$value['sha256'])){
            $id=self::json([$value['key'],$value['version']]);if(isset($seen[$id]))return;$seen[$id]=true;
            $body=$this->get($value);
            if(str_ends_with($value['key'],'.json')){$nested=json_decode($body,true);if(is_array($nested))$this->retainReferences($nested,$until,$seen);}
            $this->ensureRetention($value,$until);return;
        }
        foreach($value as $child)if(is_array($child))$this->retainReferences($child,$until,$seen);
    }
    public function put(string $key, string $body, string $type, ?string $until=null): array {
        $args=$this->args($key)+['Body'=>$body,'ContentType'=>$type,'IfNoneMatch'=>'*',
            'ServerSideEncryption'=>'AES256','ChecksumSHA256'=>base64_encode(hash('sha256',$body,true))];
        if (!empty($this->config['retention_days'])) {
            $args['ObjectLockMode']='GOVERNANCE';
            $args['ObjectLockRetainUntilDate']=new \DateTimeImmutable($until??'+'.(int)$this->config['retention_days'].' days');
        }
        $reused=false;
        try { $r=$this->s3->putObject($args); }
        catch (\Throwable $error) {
            // A lost response is not permission to overwrite or duplicate an operation.
            try { $r=$this->s3->getObject($this->args($key)); }
            catch (\Throwable $readError) { throw $error; }
            if ((string)$r['Body'] !== $body) throw new \RuntimeException('S3 write failed or key conflict.',0,$error);
            $reused=true;
        }
        $version=(string)($r['VersionId']??'');
        if ($version==='' || $version==='null') throw new \RuntimeException('S3 versioning must be enabled.');
        $ref=['key'=>$key,'version'=>$version,'sha256'=>hash('sha256',$body)];
        if($reused&&!empty($this->config['retention_days']))$this->ensureRetention($ref,$args['ObjectLockRetainUntilDate']->format('c'));
        return $ref;
    }
    public function get(array $ref): string {
        if (!isset($ref['key'],$ref['version'],$ref['sha256']) || str_contains($ref['key'],'..') || str_starts_with($ref['key'],'/')) throw new \RuntimeException('Invalid S3 reference.');
        $r=$this->s3->getObject($this->args($ref['key'])+['VersionId'=>$ref['version']]);
        $body=(string)$r['Body'];
        if (!hash_equals($ref['sha256'],hash('sha256',$body))) throw new \RuntimeException('S3 content mismatch.');
        return $body;
    }
    public function history(int $after=0,?int $through=null): array {
        $rows=[];$token=null;
        do {
            $a=$this->args()+['Prefix'=>$this->config['prefix'].'history/'];
            if ($after>0) $a['StartAfter']=$this->config['prefix'].sprintf('history/%020d.json',$after);
            if ($token) $a['ContinuationToken']=$token;
            $list=$this->s3->listObjectsV2($a);
            foreach ($list['Contents']??[] as $entry) {
                $key=substr($entry['Key'],strlen($this->config['prefix']));
                if (!preg_match('~^history/[0-9]{20}\.json$~D',$key)) continue;
                if ($through!==null && (int)basename($key,'.json')>$through) continue;
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
                $created=$r['LastModified']??($m['created_at']??'1970-01-01T00:00:00Z');
                $created=$created instanceof \DateTimeInterface?$created->getTimestamp():strtotime((string)$created);
                $out[]=['ref'=>['key'=>$key,'version'=>$r['VersionId'],'sha256'=>hash('sha256',$body)],'through'=>$m['through'],'origin'=>$m['origin'],'created'=>$created?:0,'gfs'=>$m['gfs']??[],'scheduled_at'=>$m['scheduled_at']??null];
            }$token=$list['NextContinuationToken']??null;
        }while($token);usort($out,fn($a,$b)=>[$a['through'],$a['created'],$a['ref']['key']]<=>[$b['through'],$b['created'],$b['ref']['key']]);return $out;
    }
    /** Manual renewal, not a new recovery point: latest boundary and its confirmed tail. */
    public function renewLatestSiteRetention(): array {
        $until=$this->requiredRetentionUntil();if($until===null)throw new \RuntimeException('Enable a positive retention period before renewing protection.');
        $snapshots=$this->siteSnapshots();if(!$snapshots)throw new \RuntimeException('No complete-site Checkpoint to renew.');
        foreach($snapshots as $s)if(!is_int($s['through']??null)||$s['through']<0)throw new \RuntimeException('Invalid Checkpoint boundary.');
        usort($snapshots,fn($a,$b)=>[$a['through'],$a['ref']['key']]<=>[$b['through'],$b['ref']['key']]);
        $latest=end($snapshots);[$manifest]=(new SiteSnapshot($this))->load($latest['ref']);
        $through=$manifest['through'];$refs=[$latest['ref']];$sources=[];
        foreach($this->history($through) as $row){
            if(($row['sequence']??null)!==$through+1)throw new \RuntimeException('Formal history gap; retention renewal stopped.');
            $key=sprintf('history/%020d.json',$row['sequence']);$r=$this->s3->getObject($this->args($key));$body=(string)$r['Body'];
            if(empty($r['VersionId'])||$r['VersionId']==='null'||json_decode($body,true,512,JSON_THROW_ON_ERROR)!==$row)throw new \RuntimeException('History changed while preparing retention renewal.');
            $refs[]=['key'=>$key,'version'=>$r['VersionId'],'sha256'=>hash('sha256',$body)];$through=$row['sequence'];
            $source=json_decode($this->originalSource($row['original']),true);if(is_array($source))$sources[]=$source;
        }
        $seen=[];foreach($sources as $source)$this->retainReferences($source,$until,$seen);
        foreach($refs as $ref)$this->retainReferences($ref,$until,$seen);
        $this->assertRetentionWindow($until);
        return ['status'=>'success','at'=>gmdate('c'),'manifest'=>$latest['ref'],'checkpoint_through'=>$manifest['through'],'through'=>$through,'retain_until'=>$until,'versions_checked'=>count($seen)];
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
            foreach (array_merge([$row['original']['source']??[],$row['original']['metadata']??[]],array_values($row['original']['parts']??[])) as $ref) {
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
            $row['original']=$this->saveOriginal($where,$asset,basename(rtrim($base,'/')),$item['source'],$row['attributes'],$plan['retain_until']);
            // Read back exact newly saved versions before adopting the snapshot.
            $this->originalSource($row['original']);$this->get($row['original']['metadata']);$assets[$asset]=$row;
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
            foreach ($materials as $id=>$item) if (!isset($cp['assets'][$id]) || $cp['assets'][$id]['attributes']!==$item['row']['attributes'] || $this->originalSource($cp['assets'][$id]['original'])!==$item['source']) throw new \RuntimeException('Initial state changed; refusing reset.');
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
            $materials[$asset]=['row'=>$row,'source'=>$this->originalSource($row['original'])];
        }
        return $this->saveSnapshot($materials,$state['through'],'confirmed_s3');
    }
    public function latestState(): array {
        $keys=$this->checkpoints();return $this->recoveryState($keys?end($keys):null);
    }
    /** Complete-site audit only. This result is deliberately incompatible with cleanup(). */
    public function siteCleanupPreview(int $cutoff): array {
        if ($cutoff<0 || $cutoff>time()) throw new \RuntimeException('Invalid retention cutoff.');
        $versions=[];$km=null;$vm=null;$inventoryComplete=true;
        try {
        do {
            $a=$this->args()+['Prefix'=>$this->config['prefix']];
            if($km!==null)$a['KeyMarker']=$km;
            if($vm!==null)$a['VersionIdMarker']=$vm;
            $list=$this->s3->listObjectVersions($a);
            if(!empty($list['DeleteMarkers']))throw new \RuntimeException('Delete markers require separate review; no candidates calculated.');
            foreach($list['Versions']??[] as $v){
                if(!str_starts_with($v['Key'],$this->config['prefix']))throw new \RuntimeException('Version outside configured prefix.');
                $key=substr($v['Key'],strlen($this->config['prefix']));
                if(isset($versions[$key]) || empty($v['VersionId']) || $v['VersionId']==='null')throw new \RuntimeException('Multiple or unversioned objects require separate review; no candidates calculated.');
                $date=$v['LastModified'] instanceof \DateTimeInterface?$v['LastModified']->getTimestamp():strtotime((string)$v['LastModified']);
                if($date===false)throw new \RuntimeException('Missing fixed-version modification time.');
                $versions[$key]=['key'=>$key,'version'=>(string)$v['VersionId'],'modified'=>$date];
            }
            $km=$list['NextKeyMarker']??null;$vm=$list['NextVersionIdMarker']??null;
        }while(!empty($list['IsTruncated']));
        }catch(\Aws\Exception\AwsException $e){
            if($e->getAwsErrorCode()!=='AccessDenied')throw $e;
            // Read-only fallback can explain required assets, but cannot authorize candidates.
            $inventoryComplete=false;$versions=[];$token=null;
            do {
                $a=$this->args()+['Prefix'=>$this->config['prefix']];if($token)$a['ContinuationToken']=$token;
                $list=$this->s3->listObjectsV2($a);
                foreach($list['Contents']??[] as $item){
                    if(!str_starts_with($item['Key'],$this->config['prefix']))throw new \RuntimeException('Object outside configured prefix.');
                    $key=substr($item['Key'],strlen($this->config['prefix']));$h=$this->s3->headObject($this->args($key));
                    $date=$h['LastModified'] instanceof \DateTimeInterface?$h['LastModified']->getTimestamp():strtotime((string)$h['LastModified']);
                    if(empty($h['VersionId'])||$h['VersionId']==='null'||$date===false)throw new \RuntimeException('Fixed-version metadata unavailable.');
                    $versions[$key]=['key'=>$key,'version'=>(string)$h['VersionId'],'modified'=>$date];
                }
                $token=$list['NextContinuationToken']??null;
            }while($token);
        }
        // Mixing an older recovery model requires its own dependency calculation.
        foreach($versions as $key=>$v)if(str_starts_with($key,'snapshots/'))throw new \RuntimeException('Legacy asset snapshots coexist: retained without deletion candidates; separate review required.');
        $snapshots=$this->siteSnapshots();
        if(!$snapshots)throw new \RuntimeException('No complete-site Checkpoint; no candidates calculated.');
        $protect=[];$eligible=[];$seen=[];
        $read=function(array $ref) use (&$versions): string {
            if(!isset($versions[$ref['key']]) || $versions[$ref['key']]['version']!==$ref['version'])throw new \RuntimeException('Missing or changed referenced version; no candidates calculated.');
            return $this->get($ref);
        };
        // Traverse nested media references, including references in adapter JSON sources.
        $walk=function(array $value,bool $keep) use (&$walk,&$protect,&$eligible,&$seen,$read): void {
            if(isset($value['key'],$value['version'],$value['sha256'])){
                $key=$value['key'];if($keep)$protect[$key]='Required by retained Checkpoint or history';else $eligible[$key]=true;
                $visit=$key.($keep?' keep':' retire');if(isset($seen[$visit]))return;$seen[$visit]=true;
                $body=$read($value);
                if(str_ends_with($key,'.json')){ $decoded=json_decode($body,true);if(is_array($decoded))$walk($decoded,$keep); }
                return;
            }
            foreach($value as $part)if(is_array($part))$walk($part,$keep);
        };
        foreach($snapshots as &$s){
            $m=json_decode($read($s['ref']),true,512,JSON_THROW_ON_ERROR);
            if(!is_int($m['through']??null)||$m['through']<0||!is_array($m['resources']??null))throw new \RuntimeException('Invalid complete-site manifest.');
            $base=dirname($s['ref']['key']).'/resources/';
            foreach($m['resources'] as $path=>$ref){SiteSnapshot::safePath($path);if(($ref['key']??'')!==$base.$path)throw new \RuntimeException('Checkpoint depends on external resources.');}
            $s['manifest']=$m;$s['created']=$versions[$s['ref']['key']]['modified'];
        }unset($s);
        usort($snapshots,fn($a,$b)=>[$a['through'],$a['created'],$a['ref']['key']]<=>[$b['through'],$b['created'],$b['ref']['key']]);
        $latest=end($snapshots)['ref']['key'];$floor=PHP_INT_MAX;$keep=[];$anchor=null;
        // Keep the baseline immediately before the requested recovery window too.
        foreach($snapshots as $s)if($s['created']<=$cutoff)$anchor=$s['ref']['key'];
        foreach($snapshots as $s){
            $chain=$s['ref']['key']===$latest || $s['ref']['key']===$anchor || $s['created']>$cutoff;
            $gfs=GfsPolicy::active($s['manifest']['gfs']??[],time());$retain=$chain||$gfs;
            // Archived GFS points are self-contained: they do not pin every intervening history.
            if($chain)$floor=min($floor,$s['through']);
            if($retain)$keep[]=['key'=>$s['ref']['key'],'through'=>$s['through'],'created_at'=>gmdate('c',$s['created']),'gfs'=>$s['manifest']['gfs']??[],'reason'=>$chain?'Recent recovery chain': 'GFS retention'];
            $walk($s['ref'],$retain);
        }
        $through=$floor;$tail=0;
        foreach($this->history() as $row){
            $key=sprintf('history/%020d.json',$row['sequence']);
            if(!isset($versions[$key]))throw new \RuntimeException('History inventory changed.');
            $retain=$row['sequence']>$floor || $versions[$key]['modified']>$cutoff;
            if($row['sequence']>$floor){if($row['sequence']!==$through+1)throw new \RuntimeException('Formal history gap; no candidates calculated.');$through=$row['sequence'];$tail++;}
            if($retain)$protect[$key]='Required or within retention window';else $eligible[$key]=true;
            $walk($row,$retain);
        }
        if($through<max(array_column($snapshots,'through')))throw new \RuntimeException('History does not reach retained Checkpoint boundary.');
        $lockEnabled=null;
        try{$lock=$this->s3->getObjectLockConfiguration($this->args());$lockEnabled=($lock['ObjectLockConfiguration']['ObjectLockEnabled']??'')==='Enabled';}
        catch(\Throwable $e){if($e instanceof \Aws\Exception\AwsException && $e->getAwsErrorCode()==='ObjectLockConfigurationNotFoundError')$lockEnabled=false;}
        $retained=[];$candidates=[];$blocked=[];
        foreach($versions as $key=>$v){
            if(isset($protect[$key])){$retained[]=$v+['reason'=>$protect[$key]];continue;}
            if($v['modified']>$cutoff){$retained[]=$v+['reason'=>'Within retention window'];continue;}
            if(!isset($eligible[$key])){$blocked[]=$v+['reason'=>'Unreferenced or unsupported asset; retained for separate review'];continue;}
            try {
                if(!$inventoryComplete)throw new \RuntimeException('s3:ListBucketVersions unavailable; all versions not inspected');
                if($lockEnabled===null)throw new \RuntimeException('Cannot inspect bucket Object Lock configuration');
                $r=$lockEnabled?$this->s3->getObjectRetention($this->args($key)+['VersionId'=>$v['version']]):[];
                $h=$lockEnabled?$this->s3->getObjectLegalHold($this->args($key)+['VersionId'=>$v['version']]):[];
                $until=$r['Retention']['RetainUntilDate']??null;
                $until=$until instanceof \DateTimeInterface?$until->getTimestamp():($until===null?0:strtotime((string)$until));
                if($until===false)throw new \RuntimeException('Invalid retention time');
                if(($h['LegalHold']['Status']??'OFF')!=='OFF' || $until>time())throw new \RuntimeException('Object Lock or Legal Hold still active');
                $candidates[]=$v+['reason'=>'Covered by retained recovery chain and outside retention window'];
            }catch(\Throwable $e){$blocked[]=$v+['reason'=>'Deletion not established: '.$e->getMessage()];}
        }
        // A locked member keeps the entire retired Checkpoint discoverable and intact.
        $blockedGroups=[];
        foreach($blocked as $v)if(preg_match('~^(site-snapshots/[a-f0-9]{64}/)~',$v['key'],$g))$blockedGroups[$g[1]]=true;
        $ready=[];foreach($candidates as $v){
            if(preg_match('~^(site-snapshots/[a-f0-9]{64}/)~',$v['key'],$g)&&isset($blockedGroups[$g[1]]))$blocked[]=array_merge($v,['reason'=>'Another member of this Checkpoint cannot be deleted yet']);
            else $ready[]=$v;
        }$candidates=$ready;
        $hash=hash('sha256',self::json([$this->config['bucket'],$this->config['prefix'],$cutoff,$versions,$keep,$candidates,$blocked]));
        return ['schema'=>'owr-site-retention-preview-1','read_only'=>true,'hash'=>$hash,'cutoff_timestamp'=>$cutoff,'inventory_complete'=>$inventoryComplete,
            'inventory_note'=>$inventoryComplete?'All listed versions inspected':'s3:ListBucketVersions unavailable: current fixed versions only; hidden older versions are unassessed and no deletion candidates are authorized',
            'at'=>gmdate('c'),'cutoff'=>gmdate('c',$cutoff),
            'time_basis'=>'S3 fixed-version LastModified; latest baseline selected by confirmed history boundary',
            'keep'=>$keep,'from'=>$floor,'through'=>$through,'tail_count'=>$tail,'retained'=>$retained,'candidates'=>$candidates,'blocked'=>$blocked,
            'limitation'=>'Preview only until explicitly executed; IAM DeleteObjectVersion is required. Unknown assets are retained.'];
    }
    /** Same policy for scheduled and administrator-requested deletion. Never bypass a lock. */
    public function siteCleanup(int $cutoff,string $expectedHash): array {
        $plan=$this->siteCleanupPreview($cutoff);
        if(!$plan['inventory_complete']||!hash_equals($plan['hash'],$expectedHash))throw new \RuntimeException('Storage changed or version inventory incomplete; preview again.');
        $delete=$plan['candidates'];
        // Withdraw retired markers before their payloads, so no incomplete point is advertised.
        usort($delete,static function($a,$b){
            $rank=static fn($k)=>str_starts_with($k,'history/')?0:(str_ends_with($k,'/manifest.json')?1:2);
            return [$rank($a['key']),$a['key']]<=>[$rank($b['key']),$b['key']];
        });
        $done=[];
        foreach($delete as $v){
            try{$this->s3->deleteObject($this->args($v['key'])+['VersionId'=>$v['version']]);$done[]=$v;}
            catch(\Throwable $e){return ['ok'=>false,'deleted'=>$done,'uncertain'=>$v,'error'=>$e->getMessage(),'blocked'=>$plan['blocked']];}
        }
        return ['ok'=>true,'deleted'=>$done,'blocked'=>$plan['blocked'],'retained'=>$plan['keep']];
    }
    /** Read-only cleanup preview. A timestamp fixes the policy across preview/execute. */
    public function cleanupPlan(int $cutoff): array {
        if ($cutoff<0 || $cutoff>time()) throw new \RuntimeException('Invalid cleanup cutoff.');
        if($this->siteSnapshots())throw new \RuntimeException('Complete-site assets present: use the read-only complete-site preview. Legacy deletion is disabled for this stream.');
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
        return $this->saveOriginal($base,$asset,$operation,$source,$attributes,$until);
    }
    private function saveOriginal(string $base,string $asset,string $operation,string $source,array $attributes,?string $until): array {
        $meta=['schema'=>AssetFormat::SCHEMA,'attributes'=>$attributes];$parts=[];$body=$source;
        if(self::sourceName($attributes)==='source.json'){
            $layout=AssetFormat::split(json_decode($source,true,512,JSON_THROW_ON_ERROR));
            foreach($layout['files'] as $path=>$bytes)$parts[$path]=$this->put($base.$path,$bytes,'text/plain; charset=utf-8',$until);
            unset($layout['files']);$meta['structure']=$layout;
            $body=self::json(['schema'=>AssetFormat::SCHEMA,'data'=>$parts]);
        }
        return ['schema'=>'owr-md-original-2','asset'=>$asset,'operation'=>$operation,'retain_until'=>$until,
            'source_sha256'=>hash('sha256',$source),'parts'=>$parts,
            'source'=>$this->put($base.self::sourceName($attributes),$body,self::sourceType($attributes).'; charset=utf-8',$until),
            'metadata'=>$this->put($base.'metadata.json',self::json($meta),'application/json',$until)];
    }
    /** Decode only for existing typed replay; S3 stores readable independent originals. */
    public function originalSource(array $original): string {
        if(($original['schema']??'owr-md-original-1')==='owr-md-original-1')return $this->get($original['source']);
        if(($original['schema']??'')!=='owr-md-original-2')throw new \RuntimeException('Unsupported original format.');
        $meta=json_decode($this->get($original['metadata']),true,512,JSON_THROW_ON_ERROR);
        if(($meta['schema']??'')!==AssetFormat::SCHEMA)throw new \RuntimeException('Invalid original metadata.');
        $raw=$this->get($original['source']);
        if(isset($meta['structure'])){
            $index=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
            if(($index['schema']??'')!==AssetFormat::SCHEMA||($index['data']??null)!==($original['parts']??null))throw new \RuntimeException('Original index mismatch.');
            $files=[];$base=dirname($original['source']['key']).'/';
            foreach($original['parts'] as $path=>$ref){if(($ref['key']??'')!==$base.$path)throw new \RuntimeException('Original depends on another resource scope.');$files[$path]=$this->get($ref);}
            $raw=self::json(AssetFormat::join($meta['structure'],$files));
        }
        if(!hash_equals($original['source_sha256'],hash('sha256',$raw)))throw new \RuntimeException('Reassembled original mismatch.');
        return $raw;
    }
    public function commit(array $record): void {
        $until=$this->requiredRetentionUntil();
        // Use this operation's fixed references and the existing client, never a site scan.
        // originalSource checks metadata, split parts, their hashes and reassembly.
        $source=$this->originalSource($record['original']);
        if(($record['original']['schema']??'owr-md-original-1')==='owr-md-original-1')
            $this->get($record['original']['metadata']);
        $seen=[];
        $verify=function(array $value) use (&$verify,&$seen): void {
            if(isset($value['key'],$value['version'],$value['sha256'])){
                $id=self::json([$value['key'],$value['version'],$value['sha256']]);
                if(!isset($seen[$id])){$this->get($value);$seen[$id]=true;}
                return;
            }
            foreach($value as $child)if(is_array($child))$verify($child);
        };
        $verify($record['attributes']['media']??[]);
        $seen=[];$nested=json_decode($source,true);if(is_array($nested))$this->retainReferences($nested,$until,$seen);
        $this->retainReferences($record,$until,$seen);
        $this->assertRetentionWindow($until);
        // Any read/hash failure above leaves the operation unconfirmed for existing resume.
        $this->put(sprintf('history/%020d.json',$record['sequence']),self::json($record),'application/json',$until);
    }
}
