<?php
define('ABSPATH',__DIR__.'/');
$options=[];
function home_url(){return 'https://fixture.invalid';}
function get_current_user_id(){return 7;}
function current_user_can($cap){return true;}
function wp_doing_ajax(){return false;}
function wp_json_encode($v,$flags=0){return json_encode($v,$flags);}
function wp_generate_uuid4(){return 'synthetic-operation-lock';}
function get_option($k,$default=false){global $options;return $options[$k]??$default;}
function add_option($k,$v,$unused='',$autoload=false){global $options;if(array_key_exists($k,$options))return false;$options[$k]=$v;return true;}
function update_option($k,$v,$autoload=false){global $options;$options[$k]=$v;return true;}
function delete_option($k){global $options;unset($options[$k]);}
function is_wp_error($v){return $v instanceof RuntimeException;}
require_once __DIR__.'/../src/ConstructionCapture.php';
use OzekiResilience\M1\{ConstructionOperations as C,ConstructionCapture};
function check($v,$message){if(!$v)throw new RuntimeException($message);}
function rejects($fn){try{$fn();}catch(RuntimeException $e){return true;}return false;}
$n=C::begin('rest',['body'=>['title'=>'Original']]);check(C::read()['entries'][0]['state']==='attempting','Input not persisted before operation');
check(rejects(fn()=>C::begin('other',[])),'Concurrent/unconfirmed operation accepted');
check(rejects(fn()=>C::initialSave(fn()=>[[],[]])),'Pending outcome allowed in initial save');
C::finish($n,['id'=>10]);
$manifest=['through'=>7];$files=['content.json'=>'original material'];
$p=C::initialSave(fn()=>[$manifest,$files]);check($p['files']===$files&&$p['manifest']===$manifest,'Original was altered');
$n=C::begin('rest',['body'=>['title'=>'Edited']]);C::finish($n,['id'=>10]);
$tail=C::afterInitialSave($p['construction_anchor'],$manifest,$files,C::stable());check(count($tail)===1&&$tail[0]['sequence']===2,'Wrong initial-save boundary');
check(rejects(fn()=>C::afterInitialSave([],$manifest,$files,C::stable())),'Old boundary inferred');
check(rejects(fn()=>C::afterInitialSave($p['construction_anchor'],$manifest,['content.json'=>'changed'],C::stable())),'Changed original accepted');
$changed=C::stable();$changed['entries'][0]['input']['body']['title']='Changed';
check(rejects(fn()=>C::afterInitialSave($p['construction_anchor'],$manifest,$files,$changed)),'Changed prefix accepted');
check(rejects(fn()=>C::initialSave(function()use($manifest,$files){$n=C::begin('rest',[]);C::finish($n,[]);return [$manifest,$files];})),'Concurrent initial-save mutation accepted');
$filtered=(new ReflectionMethod(ConstructionCapture::class,'withoutCredentials'))->invoke(null,['pass1'=>'secret','user_pass'=>'hash','_wpnonce'=>'nonce','post_password'=>'page-access','content'=>'Unchanged']);
check($filtered===['post_password'=>'page-access','content'=>'Unchanged'],'Credential/content access distinction lost');
$request=new class {
    public function get_method(){return 'POST';}
    public function get_route(){return '/wp/v2/posts';}
    public function get_json_params(){return ['title'=>'Actual actor'];}
};
(new ConstructionCapture())->restBefore(null,null,$request);
$entries=C::read()['entries'];$entry=end($entries);
check($entry['input']['actor']===7,'Actual operation actor was not captured');
C::finish($entry['sequence'],[]);
foreach([true,false] as $complete){
    $observer=new ConstructionCapture();$groups=[['key'=>'group_one']];if(!$complete)$groups[]=['key'=>'group_two'];
    $n=C::begin('admin',['query'=>['page'=>'acf-tools'],'body'=>['import_type'=>'json'],'files'=>['acf_import_file'=>['base64'=>base64_encode(json_encode($groups))]]]);
    foreach(['active'=>$n,'kind'=>'admin'] as $key=>$value)(new ReflectionProperty($observer,$key))->setValue($observer,$value);
    $observer->acfImported(['key'=>'group_one','ID'=>50]);$observer->shutdown();
    check(C::read()['entries'][$n-1]['state']===($complete?'registered':'attempting'),'Import completion confused with partial import');
    if(!$complete)C::finish($n,[],false); // Fixture cleanup, not a runtime recovery path.
}
$observer=new ConstructionCapture();$request=new stdClass();$pending=C::begin('rest',[]);
foreach(['active'=>$pending,'kind'=>'rest','restRequest'=>spl_object_id($request),'effects'=>[['type'=>'post','id'=>77]]] as $key=>$value)(new ReflectionProperty($observer,$key))->setValue($observer,$value);
$observer->restAfter(new RuntimeException('Response failed after a write'),null,$request);
check(C::read()['entries'][$pending-1]['state']==='attempting','Partial failure was discarded');
echo "PASS: before-operation input, unresolved outcome, initial-save cutoff, unchanged originals, changed-prefix refusal, capture drift, credential boundary, partial failure\n";
