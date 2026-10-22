<?php
declare(strict_types=1);
namespace Owr;

/** Closed-input planning only. Reader supplies pinned bytes; never boots WP or executes artifacts. */
final class RbrReconstructionPlanner
{
    private array $reads=[];
    private int $total=0;
    public function __construct(private \Closure $reader, private string $engineDigest) {
        if (!preg_match('/^[a-f0-9]{64}$/D',$engineDigest)) { self::fail('Loaded planner build digest required'); }
    }
    private static function fail(string $why): never { throw new \InvalidArgumentException($why); }
    private static function fields(array $v,array $required,array $optional=[]): void {
        if (array_diff($required,array_keys($v)) || array_diff(array_keys($v),array_merge($required,$optional))) {
            self::fail('Unknown or missing contract fields');
        }
    }
    private static function id(mixed $s): string {
        if (!is_string($s)||!preg_match('/^[A-Za-z0-9_-]{1,80}$/D',$s)) { self::fail('Invalid stable identity'); }
        return $s;
    }
    private static function text(mixed $s): string {
        if (!is_string($s)||!preg_match('//u',$s)||str_contains($s,"\0")) { self::fail('UTF-8 text required'); }
        return str_replace("\r\n","\n",$s);
    }
    private static function json(string $raw): array {
        if (strlen($raw)>2*1024*1024) { self::fail('JSON limit'); }
        $j=json_decode($raw,true,64,JSON_THROW_ON_ERROR);
        if (!is_array($j)||array_is_list($j)) { self::fail('JSON object required'); }
        $walk=function($v)use(&$walk):void{
            if(is_float($v)){self::fail('Floating-point values unsupported');}
            if(is_array($v)){foreach($v as $k=>$x){if(is_string($k)&&!preg_match('/^[A-Za-z0-9_-]+$/D',$k)){self::fail('Unsupported object key');}$walk($x);}}
        };$walk($j);
        // An explicit wire profile using the existing serializer, not a claim of universal JSON canonicalization.
        // This also rejects duplicate keys, trailing data and ambiguous numeric encodings.
        if (RbrGenerationCoordinator::encode($j)!==$raw) { self::fail('Canonical owr-json-v1 encoding required'); }
        return $j;
    }
    private function read(array $ref): string {
        self::fields($ref,['locator','size_bytes','sha256'],['stored_at','retain_until','copied_from']);
        $l=$ref['locator']; if(!is_array($l)){self::fail('Missing locator');}
        self::fields($l,['kind','bucket','region','key','version_id']);
        if ($l['kind']!=='s3' || !is_string($l['bucket']) || !preg_match('/^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$/D',$l['bucket'])
            || !is_string($l['region']) || !preg_match('/^[a-z0-9-]+$/D',$l['region'])
            || !is_string($l['key']) || !preg_match('~^[A-Za-z0-9_./-]+$~D',$l['key'])
            || in_array('..',explode('/',$l['key']),true) || !is_string($l['version_id'])
            || $l['version_id']==='' || in_array(strtolower($l['version_id']),['null','latest','current'],true) || strlen($l['version_id'])>1024
            || !is_int($ref['size_bytes']) || $ref['size_bytes']<1 || $ref['size_bytes']>8*1024*1024
            || !is_string($ref['sha256']) || !preg_match('/^[a-f0-9]{64}$/D',$ref['sha256'])) {self::fail('Unbound or invalid fixed reference');}
        $identity=RbrGenerationCoordinator::encode($l);
        if(isset($this->reads[$identity]) && $this->reads[$identity]!==$ref['sha256']) {self::fail('One fixed version has contradictory digests');}
        $raw=($this->reader)($ref);
        if(!is_string($raw) || strlen($raw)!==$ref['size_bytes'] || hash('sha256',$raw)!==$ref['sha256']) {self::fail('Referenced bytes mismatch');}
        if(!isset($this->reads[$identity])){$this->total+=strlen($raw);}
        if($this->total>64*1024*1024 || count($this->reads)>128){self::fail('Dependency closure limit');}
        $this->reads[$identity]=$ref['sha256'];return $raw;
    }
    private function object(array $ref): array {return self::json($this->read($ref));}
    private function environment(array $e): void {
        self::fields($e,['schema','mode','packages','settings']);
        if($e['schema']!=='owr-rbr-environment-v1' || !in_array($e['mode'],['synthetic-plan-only','pinned-runtime'],true)){self::fail('Unsupported environment');}
        $packages=$e['packages'];if(!is_array($packages)){self::fail('Unbound packages');}
        self::fields($packages,['wordpress','theme','engine','php','database']);
        foreach($packages as $p){
            if(!is_array($p)){self::fail('Unbound package');}self::fields($p,['version','artifact_ref']);
            if(!is_string($p['version'])||!preg_match('/^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$/D',$p['version'])
                || in_array(strtolower($p['version']),['latest','stable','current','unknown','placeholder'],true)){self::fail('Unfixed package version');}
            $this->read($p['artifact_ref']); // Availability and bytes only, never execute or unpack.
        }
        if ($e['packages']['engine']['artifact_ref']['sha256']!==$this->engineDigest) {self::fail('Loaded planner differs from E engine');}
        $s=$e['settings'];if(!is_array($s)){self::fail('Environment settings required');}
        self::fields($s,['locale','timezone','charset','collation','extensions','plugins','permalinks','image_handler','initialization','containment']);
        foreach(['locale','timezone','charset','collation','image_handler'] as $k){if(trim(self::text($s[$k]))===''){self::fail('Unbound environment setting');}}
        if(!is_array($s['extensions'])||!array_is_list($s['extensions'])||count($s['extensions'])<1){self::fail('Explicit extensions required');}
        foreach($s['extensions'] as $extension){self::id($extension);}
        if(count(array_unique($s['extensions']))!==count($s['extensions']) || $s['plugins']!==['reconstruction-engine']
            || $s['permalinks']!=='target-resolved' || $s['initialization']!=='empty-draft-preview-v1'
            || $s['containment']!=='no-egress-no-mail-no-cron-v1'){self::fail('Unsupported environment policy');}
    }
    public function plan(string $definition): array {
        $this->reads=[];$this->total=0;
        $d=self::json($definition);
        self::fields($d,['schema','site_id','assets_ref','rules_ref','environment_ref','comparison_ref','required_scope','expected_ref']);
        if($d['schema']!=='owr-rbr-definition-v1'){self::fail('Unknown definition schema');}self::id($d['site_id']);
        $a=$this->object($d['assets_ref']);$r=$this->object($d['rules_ref']);$e=$this->object($d['environment_ref']);
        $c=$this->object($d['comparison_ref']);$q=$this->object($d['expected_ref']);
        self::fields($a,['schema','site_id','sequence','operation_id','intent_sha256','parent','protect_until','deadline','assets']);
        if($a['schema']!=='owr-rbr-generation-v1'||$a['site_id']!==$d['site_id']||!is_int($a['sequence'])||$a['sequence']<1
            || !is_array($a['assets'])||!array_is_list($a['assets'])||count($a['assets'])<6||count($a['assets'])>16){self::fail('Invalid selected generation');}
        // Parent history is provenance, not an input to reconstruct this full logical snapshot.
        self::id($a['operation_id']);
        if(!is_string($a['intent_sha256'])||!preg_match('/^[a-f0-9]{64}$/D',$a['intent_sha256'])
            || !is_int($a['deadline'])||!is_int($a['protect_until'])||$a['protect_until']<$a['deadline']){self::fail('Malformed generation metadata');}
        $pages=[];$images=[];$roles=[];$relations=null;$profile=null;$ids=[];$slugs=[];
        foreach($a['assets'] as $asset){
            if(!is_array($asset)){self::fail('Invalid asset');}
            self::fields($asset,['id','revision','kind','provenance','size_bytes','sha256','storage'],['role']);
            $id=self::id($asset['id']);self::id($asset['revision']);
            if(isset($ids[$id])||!in_array($asset['kind'],['page','image','relations','profile'],true)
                || !in_array($asset['provenance'],['s3-first','enrolled-baseline'],true)
                || ($asset['storage']['sha256']??null)!==$asset['sha256'] || ($asset['storage']['size_bytes']??null)!==$asset['size_bytes']){self::fail('Asset identity mismatch');}
            $ids[$id]=$asset['kind'];$raw=$this->read($asset['storage']);
            if($asset['kind']==='image'){
                if(isset($asset['role'])){self::fail('Unexpected image role');}
                $info=@getimagesizefromstring($raw);
                if(!$info||!in_array($info[2],[IMAGETYPE_PNG,IMAGETYPE_JPEG],true)||$info[0]*$info[1]>16000000){self::fail('Unsupported image');}
                $images[$id]=['asset_id'=>$id,'revision'=>$asset['revision'],'sha256'=>$asset['sha256'],'size_bytes'=>$asset['size_bytes'],
                    'width'=>$info[0],'height'=>$info[1],'mime'=>$info['mime'],'source'=>$asset['storage']];continue;
            }
            $value=self::json($raw);
            if($asset['kind']==='page'){
                $role=$asset['role']??null;
                if(!in_array($role,['company','services','contact'],true)||isset($roles[$role])){self::fail('Missing or duplicate page role');}
                self::fields($value,['title','slug','paragraphs']);$title=self::text($value['title']);
                if(trim($title)===''||!is_string($value['slug'])||!preg_match('/^[a-z0-9-]+$/D',$value['slug'])||isset($slugs[$value['slug']])
                    ||!is_array($value['paragraphs'])||!array_is_list($value['paragraphs'])||count($value['paragraphs'])<1){self::fail('Invalid page or duplicate slug');}
                $paragraphs=array_map(self::text(...),$value['paragraphs']);
                $roles[$role]=$id;$slugs[$value['slug']]=true;
                $pages[$id]=['asset_id'=>$id,'role'=>$role,'title'=>$title,'slug'=>$value['slug'],'paragraphs'=>$paragraphs];
            }elseif($asset['kind']==='relations'){
                if($relations!==null||isset($asset['role'])){self::fail('Duplicate relations');}self::fields($value,['edges']);$relations=$value['edges'];
            }else{
                if($profile!==null||isset($asset['role'])){self::fail('Duplicate profile');}self::fields($value,['schema','roles']);$profile=$value;
            }
        }
        if(count($pages)!==3||count($images)<1||$relations===null||$profile===null||$profile['schema']!=='owr-rbr-profile-v1'
            || RbrGenerationCoordinator::encode($profile['roles'])!==RbrGenerationCoordinator::encode($roles)){self::fail('Incomplete corporate scope');}
        ksort($images);ksort($pages);
        $scope=$d['required_scope'];if(!is_array($scope)){self::fail('Scope required');}self::fields($scope,['roles','images','business_expectations']);
        if($scope['roles']!==['company','services','contact']||$scope['images']!==array_keys($images)){self::fail('Scope omits or adds assets');}
        if(!is_array($scope['business_expectations'])){self::fail('Business expectations required');}
        self::fields($scope['business_expectations'],['company','services','contact']);
        foreach($scope['business_expectations'] as $role=>$texts){
            if(!is_array($texts)||!array_is_list($texts)||count($texts)<1){self::fail('Business expectation missing');}
            foreach($texts as $t){$t=self::text($t);if(trim($t)===''||!str_contains(implode("\n",$pages[$roles[$role]]['paragraphs']),$t)){self::fail('Required business information missing');}}
        }
        self::fields($r,['schema','rule_id','role_order','landing_role','body_policy','placement_policy','image_declarations','actual_status','activation_intent']);
        if($r['schema']!=='owr-rbr-rules-v1'||$r['rule_id']!=='corporate-pages-text-v1'||$r['role_order']!==$scope['roles']
            ||$r['landing_role']!=='company'||$r['body_policy']!=='plain-text-preserve-whitespace'
            ||$r['placement_policy']!=='paragraph-boundary-image-before-link'
            ||$r['actual_status']!=='draft'||$r['activation_intent']!=='public-after-approval'){self::fail('Unsupported rule policy');}
        if(!is_array($r['image_declarations'])){self::fail('Image meaning must be declared');}
        $declared=$r['image_declarations'];ksort($declared);
        if(array_keys($declared)!==array_keys($images)){self::fail('Image declaration coverage');}
        foreach($declared as $meaning){if($meaning!=='decorative'){self::fail('Informative image needs description schema');}}
        $this->environment($e);
        self::fields($c,['schema','contract','serializer','extractor_ref']);
        if($c['schema']!=='owr-rbr-comparison-v1'||$c['contract']!=='corporate-logical-v1'||$c['serializer']!=='owr-json-v1'){self::fail('Unsupported comparison contract');}
        $this->read($c['extractor_ref']); // Bytes bound; comparator is not run by this planner.
        self::fields($q,['schema','scope','pages','images','relations','actual_status']);
        if($q['schema']!=='owr-rbr-expected-v1'||$q['actual_status']!=='draft'
            ||RbrGenerationCoordinator::encode($q['scope'])!==RbrGenerationCoordinator::encode($scope)
            ||!is_array($q['pages'])||!is_array($q['images'])||!is_array($q['relations'])){self::fail('Invalid expected-state contract');}
        $expectedIds=array_keys($q['pages']);sort($expectedIds);
        $expectedImages=array_keys($q['images']);sort($expectedImages);
        if($expectedIds!==array_keys($pages)||$expectedImages!==array_keys($images)){self::fail('Expected-state coverage');}
        // Q is bound and checked for completeness, never used to generate page operations.
        foreach($q['pages'] as $id=>$page){
            if(!is_array($page)){self::fail('Expected page required');}self::fields($page,['role','title','slug','paragraphs']);
            if($page['role']!==$pages[$id]['role']||!is_array($page['paragraphs'])||!array_is_list($page['paragraphs'])||!count($page['paragraphs'])){self::fail('Incomplete expected page');}
            self::text($page['title']);self::text($page['slug']);foreach($page['paragraphs'] as $p){self::text($p);}
        }
        foreach($q['images'] as $im){if(!is_array($im)){self::fail('Expected image required');}self::fields($im,['sha256','width','height','alt']);
            if(!is_string($im['sha256'])||!preg_match('/^[a-f0-9]{64}$/D',$im['sha256'])||!is_int($im['width'])||$im['width']<1||!is_int($im['height'])||$im['height']<1||$im['alt']!==''){self::fail('Incomplete expected image');}}
        if(!array_is_list($q['relations'])||count($q['relations'])>1000){self::fail('Invalid expected relations');}
        foreach($q['relations'] as $edge){
            if(!is_array($edge)){self::fail('Invalid expected relation');}self::fields($edge,['from','to','type','position']);
            if(!isset($pages[$edge['from']??''])||!in_array($edge['type'],['image','link','navigation'],true)
                ||($ids[$edge['to']??'']??null)!==($edge['type']==='image'?'image':'page')
                ||!is_int($edge['position'])||$edge['position']<0
                ||($edge['type']!=='navigation'&&$edge['position']>count($q['pages'][$edge['from']]['paragraphs']))){self::fail('Invalid expected relation');}
        }
        if(!is_array($relations)||!array_is_list($relations)||count($relations)>1000){self::fail('Invalid relation list');}
        $seen=[];$nav=[];
        foreach($relations as $edge){
            if(!is_array($edge)){self::fail('Invalid relation');}self::fields($edge,['from','to','type','position']);
            if(!isset($pages[$edge['from']??''])||!is_int($edge['position'])||$edge['position']<0
                ||!in_array($edge['type'],['link','image','navigation'],true)
                ||($ids[$edge['to']??'']??null)!==($edge['type']==='image'?'image':'page')){self::fail('Unresolved relation');}
            if($edge['type']!=='navigation'&&$edge['position']>count($pages[$edge['from']]['paragraphs'])){self::fail('Paragraph boundary out of range');}
            $token=RbrGenerationCoordinator::encode($edge);
            if(isset($seen[$token])){self::fail('Duplicate edge');}$seen[$token]=true;
            if($edge['type']==='navigation'){$k=$edge['from'].':'.$edge['position'];if(isset($nav[$k])){self::fail('Duplicate navigation position');}$nav[$k]=true;}
        }
        usort($relations,static function($a,$b){$rank=['image'=>0,'link'=>1,'navigation'=>2];return [$a['from'],$a['position'],$rank[$a['type']],$a['to']]<=>[$b['from'],$b['position'],$rank[$b['type']],$b['to']];});
        $steps=[];
        foreach($images as $im){$steps[]=['operation'=>'register_image','asset_id'=>$im['asset_id'],'source'=>$im['source'],
            'sha256'=>$im['sha256'],'width'=>$im['width'],'height'=>$im['height'],'mime'=>$im['mime'],'alt'=>'','caption'=>'','use_original'=>true];}
        foreach($scope['roles'] as $role){$page=$pages[$roles[$role]];$steps[]=['operation'=>'create_page_shell','asset_id'=>$page['asset_id'],'role'=>$role,
            'title'=>$page['title'],'slug'=>$page['slug'],'parent'=>null,'status'=>'draft'];}
        foreach($scope['roles'] as $role){
            $page=$pages[$roles[$role]];$body=[];$related=[];
            for($i=0;$i<=count($page['paragraphs']);$i++){
                foreach($relations as $edge){if($edge['from']!==$page['asset_id']||$edge['position']!==$i||$edge['type']==='navigation'){continue;}
                    $node=['type'=>$edge['type'],'target_asset_id'=>$edge['to']];if($edge['type']==='link'){$node['label']=$pages[$edge['to']]['title'];}else{$node['alt']='';}$body[]=$node;}
                if($i<count($page['paragraphs'])){$body[]=['type'=>'paragraph','text'=>$page['paragraphs'][$i]];}
            }
            foreach($relations as $edge){if($edge['from']===$page['asset_id']&&$edge['type']==='navigation'){$related[]=['target_asset_id'=>$edge['to'],'label'=>$pages[$edge['to']]['title']];}}
            $steps[]=['operation'=>'populate_page','asset_id'=>$page['asset_id'],'body'=>$body,'related_navigation'=>$related];
        }
        $menu=[];foreach($scope['roles'] as $role){$id=$roles[$role];$menu[]=['target_asset_id'=>$id,'label'=>$pages[$id]['title']];}
        $steps[]=['operation'=>'configure_preview','landing_asset_id'=>$roles['company'],'navigation'=>$menu,'authentication_required'=>true];
        $steps[]=['operation'=>'verify_scope','roles'=>$roles,'image_ids'=>array_keys($images),'public_activation'=>false,'side_effects_allowed'=>false];
        return ['schema'=>'owr-rbr-plan-v1','planner_contract'=>'corporate-pages-text-v1','serializer'=>'owr-json-v1',
            'engine_sha256'=>$this->engineDigest,'definition_sha256'=>hash('sha256',$definition),'site_id'=>$d['site_id'],'environment_mode'=>$e['mode'],
            'execution_authorized'=>false,'input_refs'=>['A'=>$d['assets_ref'],'R'=>$d['rules_ref'],'E'=>$d['environment_ref'],
                'C'=>$d['comparison_ref'],'Q'=>$d['expected_ref']], 'steps'=>$steps,
            'evidence_scope'=>'closed-bytes-plan-only; runtime-compatibility-and-logical-output-unverified'];
    }
}
