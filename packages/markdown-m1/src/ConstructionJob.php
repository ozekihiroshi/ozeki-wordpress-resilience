<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionTransfer.php';
require_once __DIR__.'/ConstructionBundle.php';
require_once __DIR__.'/ConstructionReadiness.php';
require_once __DIR__.'/ConstructionAuthors.php';
require_once __DIR__.'/ConstructionInitialReferences.php';
require_once __DIR__.'/TableReconstruction.php';
require_once __DIR__.'/ContactFormReconstruction.php';
require_once __DIR__.'/MemberReconstruction.php';
require_once __DIR__.'/AcfReconstruction.php';
require_once __DIR__.'/ConstructionSafety.php';

/** Durable destination job; a prepared worker performs only ordinary registration. */
final class ConstructionJob {
    public const KEY='ozeki_resilience_construction_job_v1';
    public function __construct(private Store $store,private string $binding){}
    private function destination(): string {return hash('sha256',home_url());}
    private function read(): array {
        $s=get_option(self::KEY,null);
        if(!is_array($s)||($s['binding']??'')!==$this->binding||($s['destination']??'')!==$this->destination())throw new \RuntimeException('Reconstruction job destination/storage differs');
        return $s;
    }
    public function queue(array $ref): array {
        if(get_option(self::KEY,null)!==null)throw new \RuntimeException('Existing reconstruction job must not be replaced');
        $kit=(new ConstructionTransfer($this->store))->load($ref);
        if(rtrim($kit['manifest']['source_url'],'/')===rtrim(home_url(),'/'))throw new \RuntimeException('Cannot reconstruct over the source site');
        $ready=ConstructionReadiness::inspect($kit);$plan=ConstructionBundle::plan($kit);
        $assetHolds=array_filter(array_keys($plan['tables']['held']??[]),fn($key)=>str_starts_with((string)$key,'table:'));
        $assetHolds=array_merge($assetHolds,array_filter(array_keys($plan['forms']['held']??[]),fn($key)=>str_starts_with((string)$key,'form:')));
        if($ready['blocking']||$plan['held']||$assetHolds||($plan['acf']['held']??[])||($plan['members']['held']??[])||ConstructionSafety::inspect($plan))throw new \RuntimeException('Reconstruction material requires resolution before registration');
        foreach($kit['manifest']['software_inventory']['plugins']??[] as $file=>$header)FormHistory::checkDependency($file,$header['version']);
        $s=['state'=>'queued','binding'=>$this->binding,'destination'=>$this->destination(),'commit'=>$ref,'plan_sha256'=>ConstructionContract::hash($plan),'actor'=>get_current_user_id(),'created_at'=>gmdate('c')];
        if(!add_option(self::KEY,$s,'',false)||get_option(self::KEY)!==$s)throw new \RuntimeException('Cannot persist reconstruction request');
        return $s;
    }
    public function claim(): array {
        $s=$this->read();
        if($s['state']!=='queued'||$s['actor']!==get_current_user_id())throw new \RuntimeException('Reconstruction outcome unresolved or operator differs');
        // Never expire a claim automatically: the previous worker may have registered data.
        if(!add_option(self::KEY.'_claim',wp_generate_uuid4(),'',false))throw new \RuntimeException('Reconstruction worker already claimed');
        $kit=(new ConstructionTransfer($this->store))->load($s['commit']);$plan=ConstructionBundle::plan($kit);
        if(ConstructionContract::hash($plan)!==$s['plan_sha256'])throw new \RuntimeException('Reconstruction plan changed');
        if(ConstructionSafety::inspect($plan))throw new \RuntimeException('Reconstruction application requires review');
        $s['state']='running';
        if(!update_option(self::KEY,$s,false)||get_option(self::KEY)!==$s)throw new \RuntimeException('Cannot persist reconstruction start');
        return ['plan'=>$plan,'kit'=>$kit,'url'=>home_url(),'actor'=>$s['actor']];
    }
    public function finish(array $result): void {
        $s=$this->read();if($s['state']!=='running'||$s['actor']!==get_current_user_id())throw new \RuntimeException('No owned running reconstruction');
        if(!is_array($result['operations']??null))throw new \RuntimeException('Reconstruction result missing');
        // Ordinary registration is not the final browser-use acceptance result.
        $s['state']=($result['state']??'')==='registered_pending_remaining_scope_review'?'registered_pending_use_check':'held';
        $s['result']=$result;$s['finished_at']=gmdate('c');
        if(!update_option(self::KEY,$s,false)||get_option(self::KEY)!==$s)throw new \RuntimeException('Cannot persist reconstruction outcome');
    }
    public static function summary(): array {
        $s=get_option(self::KEY,null);if(!is_array($s))return ['state'=>'not_requested'];
        if(($s['state']??'')==='queued'&&get_option(self::KEY.'_claim',null)!==null)$s['state']='claim_outcome_unknown';
        return array_intersect_key($s,array_flip(['state','created_at','finished_at']));
    }
}
