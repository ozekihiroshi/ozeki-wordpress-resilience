<?php
declare(strict_types=1);
use Owr\RbrGenerationCoordinator as Gen;
/** Dedicated fixture; runs existing storage coordinator against local S3 double only. */
final class RbrPlannerFixture {
    public array $cache=[];
    public array $definition;
    public string $engineBytes;
    public function __construct(public string $root){
        mkdir($root.'/objects',0700);mkdir($root.'/scratch',0700);
        $s=new RbrS3Double($root,2000000000);
        $store=new Owr\RbrObjectStore($s->request(...),'owr-offline-rbr-test','ap-northeast-1','123456789012',
            'sites/corporate-test/',$root.'/scratch',fn()=>$s->now);
        $assets=[];
        $add=function(string $id,string $kind,string $raw,?string $role=null)use(&$assets,$root){
            $path=$root.'/'.$id.'.input';file_put_contents($path,$raw);
            $a=['id'=>$id,'revision'=>'rev1','kind'=>$kind,'provenance'=>'s3-first','path'=>$path,'sha256'=>hash('sha256',$raw),'size_bytes'=>strlen($raw)];
            if($role!==null){$a['role']=$role;}$assets[]=$a;
        };
        $add('company','page',Gen::encode(['title'=>'Example Company','slug'=>'company','paragraphs'=>['Independent company information.']]),'company');
        $add('services','page',Gen::encode(['title'=>'Services','slug'=>'services','paragraphs'=>['Inspection and maintenance.']]),'services');
        $add('contact','page',Gen::encode(['title'=>'Contact','slug'=>'contact','paragraphs'=>['Email: contact@example.invalid','Telephone: TEST-0001']]),'contact');
        $im=imagecreatetruecolor(2,2);ob_start();imagepng($im);$png=ob_get_clean();imagedestroy($im);$add('logo','image',$png);
        $add('profile','profile',Gen::encode(['schema'=>'owr-rbr-profile-v1','roles'=>['company'=>'company','services'=>'services','contact'=>'contact']]));
        $edges=[['from'=>'company','to'=>'logo','type'=>'image','position'=>0],
            ['from'=>'company','to'=>'services','type'=>'link','position'=>1],['from'=>'services','to'=>'contact','type'=>'navigation','position'=>0]];
        $add('relations','relations',Gen::encode(['edges'=>$edges]));
        $result=(new Gen($store))->save(['schema'=>'owr-rbr-save-v1','site_id'=>'corporate-test','sequence'=>1,'parent'=>null,
            'operation_id'=>'planner-fixture','prepared_at'=>$s->now,'deadline'=>$s->now+3600,'assets'=>$assets]);
        foreach($s->objects() as $o){$raw=base64_decode($o['raw']);$this->cache[hash('sha256',$raw)]=$raw;}
        $rules=['schema'=>'owr-rbr-rules-v1','rule_id'=>'corporate-pages-text-v1','role_order'=>['company','services','contact'],
            'landing_role'=>'company','body_policy'=>'plain-text-preserve-whitespace','placement_policy'=>'paragraph-boundary-image-before-link',
            'image_declarations'=>['logo'=>'decorative'],'actual_status'=>'draft','activation_intent'=>'public-after-approval'];
        $this->engineBytes=rbrPlannerBuildBytes();$packages=[];
        foreach(['wordpress','theme','engine','php','database'] as $kind){$packages[$kind]=['version'=>'fixture-1',
            'artifact_ref'=>$this->put($kind==='engine'?$this->engineBytes:'SYNTHETIC-NONEXECUTABLE-'.$kind)];}
        $env=['schema'=>'owr-rbr-environment-v1','mode'=>'synthetic-plan-only','packages'=>$packages,
            'settings'=>['locale'=>'en_US','timezone'=>'UTC','charset'=>'utf8mb4','collation'=>'utf8mb4_unicode_ci','extensions'=>['gd','json'],
                'plugins'=>['reconstruction-engine'],'permalinks'=>'target-resolved','image_handler'=>'fixture-original-bytes',
                'initialization'=>'empty-draft-preview-v1','containment'=>'no-egress-no-mail-no-cron-v1']];
        $scope=['roles'=>['company','services','contact'],'images'=>['logo'],'business_expectations'=>[
            'company'=>['Independent company information.'],'services'=>['Inspection and maintenance.'],
            'contact'=>['contact@example.invalid','TEST-0001']]];
        // Independent expected constants: never obtained from the planner's operations or output.
        $expected=['schema'=>'owr-rbr-expected-v1','scope'=>$scope,'actual_status'=>'draft','pages'=>[
            'company'=>['role'=>'company','title'=>'Example Company','slug'=>'company','paragraphs'=>['Independent company information.']],
            'services'=>['role'=>'services','title'=>'Services','slug'=>'services','paragraphs'=>['Inspection and maintenance.']],
            'contact'=>['role'=>'contact','title'=>'Contact','slug'=>'contact','paragraphs'=>['Email: contact@example.invalid','Telephone: TEST-0001']]],
            'images'=>['logo'=>['sha256'=>hash('sha256',$png),'width'=>2,'height'=>2,'alt'=>'']],
            'relations'=>[['from'=>'company','to'=>'logo','type'=>'image','position'=>0],
                ['from'=>'company','to'=>'services','type'=>'link','position'=>1],['from'=>'services','to'=>'contact','type'=>'navigation','position'=>0]]];
        $c=['schema'=>'owr-rbr-comparison-v1','contract'=>'corporate-logical-v1','serializer'=>'owr-json-v1',
            'extractor_ref'=>$this->put('SYNTHETIC-NONEXECUTABLE-COMPARATOR')];
        $this->definition=['schema'=>'owr-rbr-definition-v1','site_id'=>'corporate-test','assets_ref'=>$result['generation'],
            'rules_ref'=>$this->putJson($rules),'environment_ref'=>$this->putJson($env),'comparison_ref'=>$this->putJson($c),
            'required_scope'=>$scope,'expected_ref'=>$this->putJson($expected)];
    }
    public function put(string $raw):array {
        $sha=hash('sha256',$raw);$this->cache[$sha]=$raw;
        return ['locator'=>['kind'=>'s3','bucket'=>'owr-offline-rbr-test','region'=>'ap-northeast-1','key'=>'definitions/'.$sha,'version_id'=>'fixture-'.$sha],
            'sha256'=>$sha,'size_bytes'=>strlen($raw)];
    }
    public function putJson(array $value):array{return $this->put(Gen::encode($value));}
    public function read(array $ref):string{if(!isset($this->cache[$ref['sha256']])){throw new RuntimeException('Missing offline pinned object');}return $this->cache[$ref['sha256']];}
    public function edit(string $field,callable $change):void{$v=json_decode($this->read($this->definition[$field]),true);$change($v);$this->definition[$field]=$this->putJson($v);}
    public function editAsset(string $id,callable $change):void{
        $this->edit('assets_ref',function(&$a)use($id,$change){foreach($a['assets']as &$asset){if($asset['id']===$id){
            $v=json_decode($this->read($asset['storage']),true);$change($v);$ref=$this->putJson($v);
            $asset['storage']=$ref;$asset['sha256']=$ref['sha256'];$asset['size_bytes']=$ref['size_bytes'];}}});
    }
    public function plan():array{return (new Owr\RbrReconstructionPlanner($this->read(...),hash('sha256',$this->engineBytes)))->plan(Gen::encode($this->definition));}
}
