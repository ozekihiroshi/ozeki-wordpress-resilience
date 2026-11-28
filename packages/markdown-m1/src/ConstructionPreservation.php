<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionOperations.php';
require_once __DIR__.'/ConstructionTransfer.php';
require_once __DIR__.'/ConstructionAuthors.php';
require_once __DIR__.'/ConstructionInitialReferences.php';

/** Confirmed construction stream. Original snapshots and old history stay untouched. */
final class ConstructionPreservation {
    public const KEY='ozeki_resilience_construction_preservation_v1';
    public function __construct(private Store $store,private string $binding){}
    private function state(): ?array {
        $s=get_option(self::KEY,null);
        if($s!==null&&($s['binding']??'')!==$this->binding)throw new \RuntimeException('Construction storage destination changed');
        return $s;
    }
    private function locked(callable $fn): mixed {
        $key=self::KEY.'_lock';$owner=wp_generate_uuid4();
        if(!add_option($key,$owner,'',false))throw new \RuntimeException('Construction transfer already running; inspect unresolved work');
        try{return $fn();}finally{if(get_option($key)===$owner)delete_option($key);}
    }
    private function acknowledge(array $ref,array $journal): array {
        $s=['binding'=>$this->binding,'commit'=>$ref,'through'=>count($journal['entries']),'journal_sha256'=>ConstructionContract::hash($journal),'confirmed_at'=>gmdate('c')];
        if(get_option(self::KEY)!==$s&&!update_option(self::KEY,$s,false))throw new \RuntimeException('Cannot persist transfer acknowledgment');
        if(get_option(self::KEY)!==$s)throw new \RuntimeException('Transfer acknowledgment read-back differs');
        return $s;
    }
    public function initial(callable $capture): array {
        return $this->locked(function()use($capture){
            if($this->state()!==null)throw new \RuntimeException('Initial construction save already exists; do not replace its history');
            $owner=wp_generate_uuid4();$key=self::KEY.'_capture';
            if(!add_option($key,$owner,'',false))throw new \RuntimeException('Initial capture already active or interrupted');
            try {
                $packet=ConstructionOperations::initialSaveWithAuthors($capture);
                $journal=ConstructionOperations::stable();
                $ref=(new ConstructionTransfer($this->store))->flush($packet,$journal);
                ConstructionJournal::assertContinuous();
                return $this->acknowledge($ref,$journal);
            }finally{if(get_option($key)===$owner)delete_option($key);}
        });
    }
    public function flush(): array {
        return $this->locked(function(){
            $s=$this->state();if($s===null)throw new \RuntimeException('Create the construction initial save first');
            $t=new ConstructionTransfer($this->store);$kit=$t->load($s['commit']);$j=ConstructionOperations::stable();
            // A server-side acknowledgment is meaningful only for its exact prefix.
            $prefix=$j;$prefix['entries']=array_slice($j['entries'],0,$s['through']);
            if(ConstructionContract::hash($prefix)!==$s['journal_sha256'])throw new \RuntimeException('Confirmed local construction prefix changed');
            $packet=['manifest'=>$kit['manifest'],'files'=>$kit['files'],'construction_anchor'=>$kit['anchor']];
            $ref=$t->flush($packet,$j);return $this->acknowledge($ref,$j);
        });
    }
    public function status(): array {
        $status=ConstructionJournal::status();
        try{$s=$this->state();}catch(\Throwable $e){return $status+['transfer'=>'destination_changed'];}
        $transfer=$s===null?'initial_required':'pending';
        if($s!==null){
            try{$j=ConstructionOperations::read();$p=$j;$p['entries']=array_slice($j['entries'],0,$s['through']);
                if(ConstructionContract::hash($p)!==$s['journal_sha256'])$transfer='record_error';
                elseif(count($j['entries'])===$s['through'])$transfer='confirmed';
            }catch(\Throwable $e){$transfer='record_error';}
        }
        return $status+['transfer'=>$transfer,'confirmed_through'=>$s['through']??0,'confirmed_at'=>$s['confirmed_at']??null];
    }
}
