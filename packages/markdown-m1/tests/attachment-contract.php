<?php
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/SiteSnapshot.php';
use OzekiResilience\M1\{AttachmentHistory,FileScope};
function checkBundle($ok,$why){if(!$ok)throw new RuntimeException($why);}
function rejectsBundle($f){try{$f();}catch(RuntimeException $e){return;}throw new RuntimeException('Missing bundle was accepted');}
$d=['tables'=>['posts'=>[['ID'=>'12','post_type'=>'attachment','post_mime_type'=>'application/pdf','post_status'=>'inherit']], 'postmeta'=>[
 ['post_id'=>'12','meta_key'=>'_wp_attached_file','meta_value'=>'2026/11/manual.pdf'],
 ['post_id'=>'12','meta_key'=>'_wp_attachment_metadata','meta_value'=>serialize(['sizes'=>['full'=>['file'=>'manual-pdf.jpg'],'thumbnail'=>['file'=>'manual-pdf-150x150.jpg']]])]
]]];
$files=['uploads/2026/11/manual.pdf'=>'%PDF-fixture','uploads/2026/11/manual-pdf.jpg'=>'preview','uploads/2026/11/manual-pdf-150x150.jpg'=>'thumbnail'];
$d['media_access']=array_fill_keys(array_keys($files),['state'=>'held']);
AttachmentHistory::assertComplete($d,$files);
foreach(array_keys($files) as $path){$bad=$files;unset($bad[$path]);rejectsBundle(fn()=>AttachmentHistory::assertComplete($d,$bad));}
$bad=$d;unset($bad['media_access']['uploads/2026/11/manual.pdf']);rejectsBundle(fn()=>AttachmentHistory::assertComplete($bad,$files));
$bad=$d;$bad['media_access']['uploads/missing.pdf']=['state'=>'held'];rejectsBundle(fn()=>AttachmentHistory::assertComplete($bad,$files));
checkBundle(count(FileScope::paths($d,true))===3,'PDF and generated previews share the selection contract');
echo "Attachment complete / missing original / missing preview / missing access / orphan rule PASS\n";
