<?php
declare(strict_types=1);
require dirname(__DIR__).'/tools/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
require dirname(__DIR__).'/src/RbrReconstructionPlanner.php';
require dirname(__DIR__).'/tools/rbr-planner-build.php';
require __DIR__.'/support/RbrS3Double.php';
require __DIR__.'/support/RbrPlannerFixture.php';
use Owr\RbrGenerationCoordinator as Gen;
$root=sys_get_temp_dir().'/owr-plan-'.bin2hex(random_bytes(12));mkdir($root,0700);$checks=[];$n=0;
function pcheck(string $name,callable $fn):void{global $checks;$fn();$checks[]=['name'=>$name,'passed'=>true];}
function pok(bool $v):void{if(!$v){throw new RuntimeException('Planner assertion');}}
function pfixture():RbrPlannerFixture{global $root,$n;$d=$root.'/case-'.(++$n);mkdir($d,0700);return new RbrPlannerFixture($d);}
function preject(callable $fn,string $match=''):void{try{$fn();}catch(Throwable $e){if($match!==''&&!str_contains($e->getMessage(),$match)){throw new RuntimeException('Unexpected: '.$e->getMessage());}return;}throw new RuntimeException('Expected rejection');}
try{
 pcheck('existing generation and pinned closure produce bounded plan without WP',function(){
    $f=pfixture();$p=$f->plan();pok(count($p['steps'])===9&&$p['execution_authorized']===false);
    pok(array_column($p['steps'],'operation')===['register_image','create_page_shell','create_page_shell','create_page_shell','populate_page','populate_page','populate_page','configure_preview','verify_scope']);
    pok($p['steps'][4]['body']===[['type'=>'image','target_asset_id'=>'logo','alt'=>''],['type'=>'paragraph','text'=>'Independent company information.'],['type'=>'link','target_asset_id'=>'services','label'=>'Services']]);
    pok($p['steps'][6]['body']===[['type'=>'paragraph','text'=>'Email: contact@example.invalid'],['type'=>'paragraph','text'=>'Telephone: TEST-0001']]);
 });
 pcheck('repeat and independent planner same input yield byte-identical plans',function(){
    $f=pfixture();$before=$f->cache;$a=Gen::encode($f->plan());$b=Gen::encode($f->plan());pok($a===$b&&$before===$f->cache);
 });
 pcheck('source input files absent after storage still plans',function(){
    $f=pfixture();foreach(glob($f->root.'/*.input')as$p){unlink($p);}pok($f->plan()['site_id']==='corporate-test');
 });
 pcheck('cache order and unrelated cache objects cannot alter plan',function(){
    $f=pfixture();$a=Gen::encode($f->plan());$f->cache=array_reverse($f->cache,true);$f->put('Unreferenced malicious ambient material');pok($a===Gen::encode($f->plan()));
 });
 pcheck('missing and changed pinned bytes rejected',function(){
    $f=pfixture();unset($f->cache[$f->definition['rules_ref']['sha256']]);preject(fn()=>$f->plan(),'Missing');
    $f=pfixture();$f->cache[$f->definition['assets_ref']['sha256']]='corrupted';preject(fn()=>$f->plan(),'mismatch');
 });
 pcheck('null version and foreign site rejected',function(){
    $f=pfixture();$f->definition['assets_ref']['locator']['version_id']='null';preject(fn()=>$f->plan(),'reference');
    $f=pfixture();$f->definition['site_id']='another';preject(fn()=>$f->plan(),'generation');
 });
 pcheck('unknown schema and fields rejected',function(){
    $f=pfixture();$f->definition['schema']='future';preject(fn()=>$f->plan());
    $f=pfixture();$f->edit('rules_ref',function(&$r){$r['shell_command']='echo unacceptable';});preject(fn()=>$f->plan(),'fields');
 });
 pcheck('duplicate JSON keys cannot be silently accepted',function(){
    $f=pfixture();$raw=Gen::encode($f->definition);$raw=str_replace('"site_id":"corporate-test"','"site_id":"wrong","site_id":"corporate-test"',$raw);
    $p=new Owr\RbrReconstructionPlanner($f->read(...),hash('sha256',$f->engineBytes));preject(fn()=>$p->plan($raw),'Canonical');
 });
 pcheck('unbound environment package and latest alias rejected',function(){
    $f=pfixture();$f->edit('environment_ref',function(&$e){$e['packages']['wordpress']['version']='latest';});preject(fn()=>$f->plan(),'Unfixed');
    $f=pfixture();$e=json_decode($f->read($f->definition['environment_ref']),true);unset($f->cache[$e['packages']['theme']['artifact_ref']['sha256']]);preject(fn()=>$f->plan(),'Missing');
 });
 pcheck('loaded engine identity must match E',function(){
    $f=pfixture();$new=$f->put('different engine');$f->edit('environment_ref',function(&$e)use($new){$e['packages']['engine']['artifact_ref']=$new;});preject(fn()=>$f->plan(),'engine');
 });
 pcheck('missing role and duplicate slug rejected',function(){
    $f=pfixture();$f->edit('assets_ref',function(&$a){$a['assets'][0]['role']='other';});preject(fn()=>$f->plan(),'role');
    $f=pfixture();$f->editAsset('services',function(&$v){$v['slug']='company';});preject(fn()=>$f->plan(),'slug');
 });
 pcheck('unresolved and out-of-range relations rejected',function(){
    $f=pfixture();$f->editAsset('relations',function(&$v){$v['edges'][0]['to']='missing';});preject(fn()=>$f->plan(),'relation');
    $f=pfixture();$f->editAsset('relations',function(&$v){$v['edges'][0]['position']=2;});preject(fn()=>$f->plan(),'boundary');
 });
 pcheck('duplicate edge and navigation position rejected',function(){
    $f=pfixture();$f->editAsset('relations',function(&$v){$v['edges'][]=$v['edges'][0];});preject(fn()=>$f->plan(),'Duplicate');
    $f=pfixture();$f->editAsset('relations',function(&$v){$v['edges'][]=['from'=>'services','to'=>'company','type'=>'navigation','position'=>0];});preject(fn()=>$f->plan(),'navigation');
 });
 pcheck('informative image and missing image declaration not guessed',function(){
    $f=pfixture();$f->edit('rules_ref',function(&$r){$r['image_declarations']['logo']='informative';});preject(fn()=>$f->plan(),'description');
 });
 pcheck('missing image declaration and weakened containment rejected',function(){
    $f=pfixture();$f->edit('rules_ref',function(&$r){$r['image_declarations']=[];});preject(fn()=>$f->plan(),'coverage');
    $f=pfixture();$f->edit('environment_ref',function(&$e){$e['settings']['containment']='allow-network';});preject(fn()=>$f->plan(),'policy');
 });
 pcheck('required contact values cannot silently disappear',function(){
    $f=pfixture();$f->editAsset('contact',function(&$v){$v['paragraphs']=['Contact missing'];});preject(fn()=>$f->plan(),'business');
 });
 pcheck('expected output is bound but never copied into generated operations',function(){
    $f=pfixture();$before=$f->plan();$f->edit('expected_ref',function(&$q){$q['pages']['company']['title']='Incorrect expected title';});$after=$f->plan();
    pok($before['steps']===$after['steps']&&$before['definition_sha256']!==$after['definition_sha256']);
 });
 pcheck('C and Q dependencies must exist and cover scope',function(){
    $f=pfixture();$c=json_decode($f->read($f->definition['comparison_ref']),true);unset($f->cache[$c['extractor_ref']['sha256']]);preject(fn()=>$f->plan(),'Missing');
    $f=pfixture();$f->edit('expected_ref',function(&$q){unset($q['pages']['contact']);});preject(fn()=>$f->plan(),'coverage');
 });
 pcheck('source format extensions rejected rather than silently dropped',function(){
    $f=pfixture();$f->editAsset('company',function(&$v){$v['shortcode']='[external]';});preject(fn()=>$f->plan(),'fields');
 });
 pcheck('offline CLI in two fresh PHP processes produces identical P; cannot overwrite',function(){
    $f=pfixture();mkdir($f->root.'/cache',0700);
    foreach($f->cache as $sha=>$raw){file_put_contents($f->root.'/cache/'.$sha.'.blob',$raw);}
    file_put_contents($f->root.'/definition.json',Gen::encode($f->definition));
    $run=function($out)use($f){$cmd=[PHP_BINARY,dirname(__DIR__).'/tools/rbr-plan.php','--definition='.$f->root.'/definition.json','--objects='.$f->root.'/cache','--output='.$out];
        $proc=proc_open($cmd,[1=>['pipe','w'],2=>['pipe','w']],$pipes);
        $stdout=stream_get_contents($pipes[1]);$err=stream_get_contents($pipes[2]);fclose($pipes[1]);fclose($pipes[2]);return [proc_close($proc),$stdout,$err];};
    $one=$f->root.'/plan1.json';$two=$f->root.'/plan2.json';
    $a=$run($one);$b=$run($two);pok($a[0]===0&&$b[0]===0&&file_get_contents($one)===file_get_contents($two));
    pok($run($one)[0]!==0);
    unlink($f->root.'/cache/'.$f->definition['rules_ref']['sha256'].'.blob');
    pok($run($f->root.'/failed.json')[0]!==0&&!file_exists($f->root.'/failed.json'));
 });
 echo json_encode(['kind'=>'rbr_planner_offline_tests','checked_at'=>gmdate('c'),'passed'=>true,'checks'=>$checks,
    'wp_invocations'=>0,'network_requests'=>0,'runtime_compatibility_verified'=>false,'logical_site_comparison_executed'=>false,
    'environment_artifacts'=>'synthetic non-executable placeholders except loaded planner source bundle'],JSON_PRETTY_PRINT)."\n";
}finally{
 $walk=function($d)use(&$walk){foreach(scandir($d)as$n){if($n==='.'||$n==='..')continue;$p=$d.'/'.$n;if(is_dir($p)&&!is_link($p)){$walk($p);rmdir($p);}else{unlink($p);}}};$walk($root);rmdir($root);
}
