<?php
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/Store.php';
require __DIR__.'/../src/CoreStateHistory.php';
require __DIR__.'/../src/NativeHistory.php';
require __DIR__.'/../src/SetupReadiness.php';
use OzekiResilience\M1\{UpdateContract,CoreStateHistory,NativeHistory,Store};
function check($v,$message){if(!$v)throw new RuntimeException($message);}
function determine_locale(){return 'en_US';}
$failed=false;try{UpdateContract::requireArticleConditions([]);}catch(RuntimeException $e){$failed=str_contains($e->getMessage(),'password changes');}check($failed,'Legacy missing conditions cannot silently authorize publication');
$a=['update_contract'=>UpdateContract::SCHEMA,'post_excerpt'=>'','post_parent'=>'0','menu_order'=>'0','comment_status'=>'closed','ping_status'=>'closed','post_password'=>'<a>&[text]','post_author'=>'8','author'=>['display_name'=>'Author B','user_nicename'=>'author-b']];
$d=['authors'=>[]];$values=UpdateContract::apply($a,$d);
check($values['post_password']==='<a>&[text]'&&$d['authors']['8']===$a['author'],'Password is data, not HTML; author definition follows its value');
foreach(['post_password','post_author','author'] as $key){$bad=$a;unset($bad[$key]);$failed=false;try{UpdateContract::apply($bad,$d);}catch(RuntimeException $e){$failed=true;}check($failed,'Missing contract field rejected: '.$key);}
$a['post_password']='';check(UpdateContract::apply($a,$d)['post_password']==='','Explicit removal differs from missing password');
$d=['tables'=>['posts'=>[['ID'=>'10','post_type'=>'post','post_status'=>'publish','post_parent'=>'0']],'postmeta'=>[],'terms'=>[['term_id'=>'1','name'=>'Removed','slug'=>'removed','term_group'=>'0']],'term_taxonomy'=>[['term_taxonomy_id'=>'1','term_id'=>'1','taxonomy'=>'category','description'=>'','parent'=>'0','count'=>'1']],'term_relationships'=>[['object_id'=>'10','term_taxonomy_id'=>'1','term_order'=>'0']],'termmeta'=>[['meta_id'=>'1','term_id'=>'1','meta_key'=>'old','meta_value'=>'old']]]];
$shared=$d;$shared['tables']['term_taxonomy'][]=['term_taxonomy_id'=>'2','term_id'=>'1','taxonomy'=>'another_plugin','description'=>'','parent'=>'0','count'=>'1'];$shared['tables']['term_relationships'][]=['object_id'=>'10','term_taxonomy_id'=>'2','term_order'=>'0'];
$v=['schema'=>UpdateContract::SCHEMA,'kind'=>'taxonomy','terms'=>[],'term_taxonomy'=>[],'term_relationships'=>[]];CoreStateHistory::replay($d,Store::json($v));
check(!$d['tables']['terms']&&!$d['tables']['term_relationships']&&!$d['tables']['termmeta'],'Deleted taxonomy removes definition, assignment and orphan metadata');
CoreStateHistory::replay($shared,Store::json($v));check(count($shared['tables']['terms'])===1&&count($shared['tables']['termmeta'])===1&&array_column($shared['tables']['term_relationships'],'term_taxonomy_id')===['2'],'Deleting a category does not erase another taxonomy sharing its term');
$native=['schema'=>'owr-native-state-2','id'=>10,'type'=>'post','deleted'=>false,'thumbnail'=>0,'terms'=>[['term_id'=>'1','term_taxonomy_id'=>'1','taxonomy'=>'category','name'=>'Stale','slug'=>'stale','term_group'=>'0','description'=>'','parent'=>'0']],'assigned'=>['1']];$files=[];
NativeHistory::replay($d,$files,Store::json($native),['origin_id'=>10]);check(!$d['tables']['terms']&&!$d['tables']['term_relationships'],'Article details cannot revive stale taxonomy');
$v=['schema'=>UpdateContract::SCHEMA,'kind'=>'options','options'=>array_fill_keys(UpdateContract::OPTIONS,'')];$v['options']['active_plugins']=['untrusted/plugin.php'];$failed=false;
try{CoreStateHistory::replay($d,Store::json($v));}catch(RuntimeException $e){$failed=true;}check($failed,'Core option history cannot change installed software');
echo "PASS required article fields, opaque password/removal, author definition, taxonomy deletion/stale-native boundary, option allowlist\n";
