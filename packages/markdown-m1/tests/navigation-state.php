<?php
require __DIR__.'/core-update-contract.php';
use OzekiResilience\M1\{CoreStateHistory,UpdateContract,Store};
function get_option($key,$default=false){return $default;}
$options=UpdateContract::options();$options['sticky_posts']=[10];$options['permalink_structure']='/articles/%postname%/';
$data=['options'=>[],'tables'=>['posts'=>[['ID'=>'10','post_type'=>'post'],['ID'=>'20','post_type'=>'nav_menu_item']],'postmeta'=>[['meta_id'=>'1','post_id'=>'20','meta_key'=>'_menu_item_url','meta_value'=>'https://example.invalid/old']],'terms'=>[['term_id'=>'1','name'=>'Old','slug'=>'old','term_group'=>'0']],'term_taxonomy'=>[['term_taxonomy_id'=>'1','term_id'=>'1','taxonomy'=>'nav_menu','parent'=>'0']],'term_relationships'=>[['object_id'=>'20','term_taxonomy_id'=>'1','term_order'=>'0']],'termmeta'=>[]]];
CoreStateHistory::replay($data,Store::json(['schema'=>UpdateContract::SCHEMA,'kind'=>'options','options'=>$options]));
check($data['options']===$options,'Complete scalar and list settings survive replay');
$v=['schema'=>UpdateContract::SCHEMA,'kind'=>'menus','posts'=>[['ID'=>'21','post_type'=>'nav_menu_item','post_title'=>'New','menu_order'=>'1']],'postmeta'=>[['post_id'=>'21','meta_key'=>'_menu_item_url','meta_value'=>'https://example.invalid/new']],'terms'=>[['term_id'=>'2','name'=>'New','slug'=>'new','term_group'=>'0']],'term_taxonomy'=>[['term_taxonomy_id'=>'2','term_id'=>'2','taxonomy'=>'nav_menu','parent'=>'0']],'term_relationships'=>[['object_id'=>'21','term_taxonomy_id'=>'2','term_order'=>'0']]];
CoreStateHistory::replay($data,Store::json($v));
check(array_column($data['tables']['posts'],'ID')===['10','21'],'Menu replacement preserves articles and removes deleted menu item');
check(count($data['tables']['postmeta'])===1&&$data['tables']['postmeta'][0]['post_id']==='21','Menu metadata replaced together');
check($data['tables']['terms'][0]['term_id']==='2','Menu definitions replaced');
$bad=$v;$bad['posts'][0]['ID']='10';$failed=false;try{CoreStateHistory::replay($data,Store::json($bad));}catch(Throwable $e){$failed=true;}check($failed,'Menu cannot overwrite article identity');
$bad=$options;$bad['sticky_posts']=['not-an-id'];$failed=false;try{CoreStateHistory::replay($data,Store::json(['schema'=>UpdateContract::SCHEMA,'kind'=>'options','options'=>$bad]));}catch(Throwable $e){$failed=true;}check($failed,'Invalid sticky identity rejected');
foreach(['posts','postmeta','terms','term_taxonomy','term_relationships'] as $key)$v[$key]=[];
CoreStateHistory::replay($data,Store::json($v));check(count($data['tables']['posts'])===1&&!$data['tables']['term_taxonomy'],'Deleting all menus preserves article');
echo "PASS complete navigation state and settings\n";
$failed=false;try{CoreStateHistory::replay($data,Store::json(['schema'=>'owr-core-updates-2','kind'=>'menus']));}catch(Throwable $e){$failed=true;}check($failed,'Previous unpublished update contract rejected');
