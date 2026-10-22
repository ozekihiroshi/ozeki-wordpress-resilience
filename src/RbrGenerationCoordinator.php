<?php
declare(strict_types=1);
namespace Owr;

/** Small explicit package -> S3 commit. Not a WP editor/DB apply implementation. */
final class RbrGenerationCoordinator
{
    private string $stage='not_started';
    public function lastConfirmedStage(): string { return $this->stage; }
    public function __construct(private RbrObjectStore $store) {}
    public static function encode(array $value): string {
        $sort=function (&$v) use (&$sort): void {
            if (!is_array($v)) { return; }
            if (!array_is_list($v)) { ksort($v); }
            foreach ($v as &$item) { $sort($item); }
        };
        $sort($value);
        return json_encode($value,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES)."\n";
    }
    private static function id(mixed $value): void {
        if (!is_string($value) || !preg_match('/^[A-Za-z0-9_-]{1,80}$/D',$value)) {
            throw new \InvalidArgumentException('Invalid independent identity');
        }
    }
    private function slot(int $n): string { return $this->store->key('commits/'.sprintf('%012d',$n).'.json'); }
    private function validate(array $job): array {
        self::id($job['operation_id']??null); self::id($job['site_id']??null);
        if ($job['site_id']!==$this->store->siteId()) { throw new \InvalidArgumentException('Site scope mismatch'); }
        if (($job['schema']??null)!=='owr-rbr-save-v1' || !is_int($job['sequence']??null)
            || $job['sequence']<1 || $job['sequence']>1000 || !is_int($job['prepared_at']??null)
            || !is_int($job['deadline']??null) || $job['deadline']<=$job['prepared_at']
            || $job['deadline']>$job['prepared_at']+3600 || $job['prepared_at']>$this->store->now()+300
            || !is_array($job['assets']??null) || count($job['assets'])<6 || count($job['assets'])>16) {
            throw new \InvalidArgumentException('Invalid bounded save intent');
        }
        if (($job['sequence']===1)!==(($job['parent']??null)===null)) {
            throw new \InvalidArgumentException('Parent required except baseline');
        }
        $ids=[]; $roles=[]; $profile=0; $relations=0; $total=0; $pages=0;
        $intent=$job;
        foreach ($job['assets'] as $i=>$a) {
            self::id($a['id']??null); self::id($a['revision']??null);
            if (isset($ids[$a['id']]) || !in_array($a['kind']??null,['page','image','profile','relations'],true)
                || !is_int($a['size_bytes']??null) || $a['size_bytes']<1 || $a['size_bytes']>8*1024*1024
                || !is_string($a['sha256']??null) || !preg_match('/^[a-f0-9]{64}$/D',$a['sha256'])
                || (isset($a['path'])===isset($a['existing']))
                || !in_array($a['provenance']??null,['s3-first','enrolled-baseline'],true)) {
                throw new \InvalidArgumentException('Invalid original');
            }
            $ids[$a['id']]=$a['kind']; $total+=$a['size_bytes'];
            if ($a['kind']==='page') { $pages++; $roles[]=$a['role']??''; }
            if ($a['kind']==='profile') { $profile++; }
            if ($a['kind']==='relations') { $relations++; }
            unset($intent['assets'][$i]['path']); // Byte identity survives movement of a local job folder.
        }
        sort($roles);
        if ($roles!==['company','contact','services'] || $pages!==3 || $profile!==1 || $relations!==1
            || $total>64*1024*1024) { throw new \InvalidArgumentException('Three roles, profile, relations required'); }
        return $intent;
    }
    private function verifyContent(array $assets): void {
        $ids=[]; $roles=[];
        foreach ($assets as $a) { $ids[$a['id']]=$a['kind']; if ($a['kind']==='page') { $roles[$a['role']]=$a['id']; } }
        foreach ($assets as $a) {
            $bytes=$this->store->bytes($a['storage']);
            if ($a['kind']==='image') {
                $info=@getimagesizefromstring($bytes);
                if (!$info || !in_array($info[2],[IMAGETYPE_JPEG,IMAGETYPE_PNG],true)
                    || $info[0]*$info[1]>16000000) { throw new \RuntimeException('Unsupported image'); }
                continue; // Originals preserved; not a malware-free image certification.
            }
            $j=json_decode($bytes,true,64,JSON_THROW_ON_ERROR);
            if (!is_array($j)) { throw new \RuntimeException('Expected typed asset'); }
            if ($a['kind']==='page') {
                if (array_diff(array_keys($j),['title','slug','paragraphs']) || !is_string($j['title']??null)
                    || trim($j['title'])==='' || !is_string($j['slug']??null)
                    || !preg_match('/^[a-z0-9-]+$/D',$j['slug']) || !is_array($j['paragraphs']??null)
                    || !array_is_list($j['paragraphs']) || count($j['paragraphs'])<1) {
                    throw new \RuntimeException('Minimum page supports title, slug and plain-text paragraphs');
                }
                foreach ($j['paragraphs'] as $p) { if (!is_string($p)) { throw new \RuntimeException('Plain text required'); } }
            } elseif ($a['kind']==='profile') {
                $expected=['schema'=>'owr-rbr-profile-v1','roles'=>$roles];
                if (self::encode($j)!==self::encode($expected)) { throw new \RuntimeException('Profile role mismatch'); }
            } else {
                if (array_keys($j)!==['edges'] || !is_array($j['edges']) || !array_is_list($j['edges'])) {
                    throw new \RuntimeException('Invalid relations');
                }
                foreach ($j['edges'] as $edge) {
                    if (!is_array($edge) || array_diff(array_keys($edge),['from','to','type','position'])
                        || ($ids[$edge['from']??'']??null)!=='page'
                        || !in_array($edge['type']??null,['link','image','navigation'],true)
                        || !is_int($edge['position']??null) || $edge['position']<0
                        || ($ids[$edge['to']??'']??null)!==($edge['type']==='image'?'image':'page')) {
                        throw new \RuntimeException('Unresolved or unsupported relation');
                    }
                }
            }
        }
    }
    private function validateParent(array $job): void {
        $ref=$job['parent']??null;
        for ($n=$job['sequence']-1; $n>=1; $n--) {
            if (!is_array($ref) || ($ref['locator']['key']??null)!==$this->slot($n)) {
                throw new \RuntimeException('Broken parent chain');
            }
            $m=$this->store->json($ref);
            if (($m['schema']??null)!=='owr-rbr-generation-v1' || ($m['site_id']??null)!==$job['site_id']
                || ($m['sequence']??null)!==$n) { throw new \RuntimeException('Foreign or invalid parent'); }
            $ref=$m['parent']??null;
        }
        if ($ref!==null) { throw new \RuntimeException('Invalid baseline parent'); }
    }
    public function save(array $job): array {
        $this->stage='not_started';
        $intent=$this->validate($job); $body=self::encode($intent); $digest=hash('sha256',$body);
        $this->store->preflight();
        $this->validateParent($job);
        // Durable intent makes a restarted operation immutable, including its dependency set.
        $this->store->ensureBytes($this->store->key('operations/'.$job['operation_id'].'.json'),$body);
        $this->stage='intent_stored';
        $slot=$this->slot($job['sequence']);
        $existing=$this->store->record($slot);
        $required=$job['deadline']+35*86400;
        if ($existing!==null) {
            $m=$existing['data'];
            if (($m['intent_sha256']??null)!==$digest || ($m['operation_id']??null)!==$job['operation_id']
                || ($m['schema']??null)!=='owr-rbr-generation-v1' || ($m['sequence']??null)!==$job['sequence']
                || ($m['site_id']??null)!==$job['site_id']) { throw new \RuntimeException('Generation conflict; review newer version'); }
            if ($existing['reference']['retain_until']<$required) { throw new \RuntimeException('Committed slot protection-error'); }
            if ($existing['reference']['stored_at']>$job['deadline']) { throw new \RuntimeException('Late committed slot; do not apply'); }
            if (($m['deadline']??null)!==$job['deadline'] || ($m['protect_until']??null)!==$required
                || self::encode($m['parent']??[])!==self::encode($job['parent']??[])
                || count($m['assets']??[])!==count($intent['assets'])) {
                throw new \RuntimeException('Committed manifest differs from immutable intent');
            }
            foreach ($intent['assets'] as $i=>$expected) {
                unset($expected['existing']); $seen=$m['assets'][$i];
                $storage=$seen['storage']??[];unset($seen['storage']);
                if (self::encode($seen)!==self::encode($expected)
                    || ($storage['sha256']??null)!==$expected['sha256']
                    || ($storage['size_bytes']??null)!==$expected['size_bytes']) {
                    throw new \RuntimeException('Committed asset differs from immutable intent');
                }
            }
            $this->verifyContent($m['assets']);
            foreach ($m['assets'] as $asset) {
                if ($this->store->protection($asset['storage'])<$required) { throw new \RuntimeException('Committed dependency protection-error'); }
            }
            $this->stage='committed';
            return ['schema'=>'owr-rbr-save-result-v1','state'=>'committed','wp_state'=>'not_applied',
                'operation_id'=>$job['operation_id'],'generation'=>$existing['reference'],'manifest'=>$m];
        }
        if ($this->store->now()>=$job['deadline']) {
            throw new \RuntimeException('Intent expired; reconcile before preparing a new operation');
        }
        $assets=[];
        foreach ($job['assets'] as $a) {
            $ref=$this->store->protectedOriginal($a,$job['operation_id'],$required);
            unset($a['path'],$a['existing']); $a['storage']=$ref; $assets[]=$a;
        }
        $this->verifyContent($assets);
        $this->stage='originals_confirmed';
        $manifest=['schema'=>'owr-rbr-generation-v1','site_id'=>$job['site_id'],
            'sequence'=>$job['sequence'],'operation_id'=>$job['operation_id'],'intent_sha256'=>$digest,
            'parent'=>$job['parent']??null,'protect_until'=>$required,'deadline'=>$job['deadline'],
            'assets'=>$assets];
        $manifestBody=self::encode($manifest);
        if ($existing===null && $this->store->now()>=$job['deadline']) {
            throw new \RuntimeException('Deadline elapsed before commit');
        }
        $commit=$this->store->ensureBytes($slot,$manifestBody);
        if ($commit['retain_until']<$required) { throw new \RuntimeException('Committed slot protection-error; do not apply'); }
        $this->stage='committed';
        if ($commit['stored_at']>$job['deadline']) {
            throw new \RuntimeException('Late committed slot; do not apply');
        }
        // End of this component: no source WP writes or publication happen here.
        return ['schema'=>'owr-rbr-save-result-v1','state'=>'committed','wp_state'=>'not_applied',
            'operation_id'=>$job['operation_id'],'generation'=>$commit,'manifest'=>$manifest];
    }
}
