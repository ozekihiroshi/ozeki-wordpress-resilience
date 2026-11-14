<?php
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/SiteSnapshot.php';
use OzekiResilience\M1\{MediaAccess,FileScope};
function expectAccess($ok,$why){if(!$ok)throw new RuntimeException($why);}
$p='uploads/2026/11/image.png';
$d=['tables'=>['posts'=>[['ID'=>1,'post_type'=>'attachment','post_status'=>'inherit','post_parent'=>2],['ID'=>2,'post_type'=>'page','post_status'=>'private','post_password'=>'secret']], 'postmeta'=>[['post_id'=>1,'meta_key'=>'_wp_attached_file','meta_value'=>'2026/11/image.png'],['post_id'=>2,'meta_key'=>'_wpmem_block','meta_value'=>'1']]]];
expectAccess(isset(FileScope::paths($d)[$p]),'Page restrictions are not file restrictions');
$a=MediaAccess::classify($d,[]);
expectAccess($a[$p]['state']==='public','Ordinary media stays public independently of parent page');
$d['tables']['postmeta'][]=['post_id'=>1,'meta_key'=>'_members_only','meta_value'=>'yes'];
$a=MediaAccess::classify($d,[]);
expectAccess($a[$p]['state']==='held','Unknown attachment conditions must be retained as a hold');
array_pop($d['tables']['postmeta']);
expectAccess(MediaAccess::classify($d,[$p])[$p]['state']==='held','Filesystem guard must hold media');
expectAccess(MediaAccess::classify($d,[],[$p=>['state'=>'unknown']])[$p]['state']==='unknown','Recovered uncertainty must survive metadata projection');
expectAccess(MediaAccess::effective([],[$p=>'bytes'])[$p]['state']==='unknown','Legacy resources must not acquire public permission');
foreach([['state'=>'public'],['state'=>'unknown'],['state'=>'held']] as $rule)expectAccess(MediaAccess::validate([$p=>$rule])===[$p=>$rule],'Valid contract');
foreach([['state'=>'anything'],['state'=>true],['state'=>'public','execute'=>'yes']] as $rule){$blocked=false;try{MediaAccess::validate([$p=>$rule]);}catch(RuntimeException $e){$blocked=true;}expectAccess($blocked,'Invalid conditions must fail before installation');}
echo "Media access contract PASS\n";
