<?php
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/SiteSnapshot.php';
use OzekiResilience\M1\FileScope;
function checkScope($ok,$why){if(!$ok)throw new RuntimeException($why);}
$d=['tables'=>['posts'=>[['ID'=>1,'post_type'=>'attachment','post_status'=>'inherit','post_parent'=>0,'post_password'=>'']], 'postmeta'=>[['post_id'=>1,'meta_key'=>'_wp_attached_file','meta_value'=>'2026/11/public.png']]]];
checkScope(class_exists(FileScope::class),'Shared file scope contract missing');
$allowed=FileScope::paths($d);
checkScope(isset($allowed['uploads/2026/11/public.png']),'Normal registered media must survive');
foreach(['C:private.pdf',"bad\\private.pdf","bad\0.pdf",'../private.pdf'] as $bad){
 $invalid=$d;$invalid['tables']['postmeta'][0]['meta_value']=$bad;
 checkScope(!FileScope::paths($invalid),'Invalid attachment paths must be excluded without blocking other content');
}
$icon=$d;$icon['tables']['postmeta'][]=['post_id'=>1,'meta_key'=>'_wp_attachment_context','meta_value'=>'site-icon'];
checkScope(isset(FileScope::paths($icon)['uploads/2026/11/public.png']),'Core site-icon context must not exclude public media');
$variants=$d;$variants['tables']['postmeta'][]=['post_id'=>1,'meta_key'=>'_wp_attachment_metadata','meta_value'=>serialize(['sizes'=>['small'=>['file'=>'public-150.png']],'original_image'=>'public-original.png'])];
checkScope(count(FileScope::paths($variants))===3,'Public original and generated images must stay together');
$variants['tables']['posts'][0]['post_status']='private';
checkScope(!FileScope::paths($variants),'Private image derivatives must not become public');
$external=$d;$external['tables']['posts'][]=['ID'=>2,'post_type'=>'dlm_download_version'];
$external['tables']['postmeta'][]=['post_id'=>2,'meta_key'=>'_files','meta_value'=>serialize(['https://source.invalid/wp-content/uploads/2026/11/public.png'])];
checkScope(!FileScope::paths($external),'An unknown plugin reference must not be relabeled public by media registration');
$duplicate=$d;$duplicate['tables']['posts'][]=['ID'=>2,'post_type'=>'attachment','post_status'=>'private','post_parent'=>0];
$duplicate['tables']['postmeta'][]=['post_id'=>2,'meta_key'=>'_wp_attached_file','meta_value'=>'2026/11/public.png'];
checkScope(!FileScope::paths($duplicate),'A second public registration must not override private ownership');
foreach(['uploads/dlm_uploads/private.pdf','uploads/unregistered.pdf','uploads/wpcf7_uploads/private.pdf'] as $p)checkScope(!isset($allowed[$p]),'Unknown file must not become public');
$d['tables']['postmeta'][0]['meta_value']='dlm_uploads/private.pdf';
checkScope(!FileScope::paths($d),'Registration alone must not allow private plugin storage');
$d['tables']['postmeta'][0]['meta_value']='2026/11/private.pdf';
$d['tables']['postmeta'][]=['post_id'=>1,'meta_key'=>'_members_only','meta_value'=>'yes'];
checkScope(!FileScope::paths($d),'Unknown access metadata must fail closed');
array_pop($d['tables']['postmeta']);$d['tables']['posts'][0]['post_status']='private';
checkScope(!FileScope::paths($d),'Private attachment must not become public');
echo "File ownership and access boundary PASS\n";
