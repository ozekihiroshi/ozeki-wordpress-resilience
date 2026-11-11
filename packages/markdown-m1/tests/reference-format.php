<?php
if(!function_exists('wp_parse_url')){function wp_parse_url($url,$component=-1){return parse_url($url,$component);}}
require __DIR__.'/separated-assets.php';
use OzekiResilience\M1\{ReferenceContext as R,SiteSnapshot,Store};
$s3->fail=null;$s3->objects=[];
$ctx=[['site'=>'https://a.test','uploads'=>'https://a.test/wp-content/uploads'],['site'=>'https://b.test','uploads'=>'https://b.test/media']];
$frozen=$s3->objects;reject(fn()=>$store->prepare('bad-context','1','raw',['reference_origins'=>[]]));check($s3->objects===$frozen,'Empty context rejected before writing');
$a=['post_type'=>'ozmd_document','content_format'=>'markdown','reference_origins'=>$ctx];
$raw='[page](https://a.test/?page_id=1)';
$o=$store->prepare('context-test','1',$raw,$a);
check($o['schema']===R::ORIGINAL_FORMAT,'New originals require context-aware reader');
check($store->originalSource($o)===$raw,'Context does not alter original bytes');
$old=$store->prepare('legacy-test','1',$raw,['content_format'=>'markdown']);
check($old['schema']==='owr-md-original-2'&&$store->originalSource($old)===$raw,'Unchanged original format without context');
$legacyPoint=$site->save($files,$manifest);
$manifest['reference_origins']=$ctx;
$point=$site->save($files,$manifest);[$m,$restored]=$site->load($point['manifest']);
check($m['asset_format']===R::SNAPSHOT_FORMAT&&$m['reference_origins']===$ctx,'Snapshot carries mandatory provenance');
$cp=$site->checkpoint($point['manifest']);[$after,$content]=$site->load($cp['manifest']);
check($after['reference_origins']===$ctx&&$content['markdown/2.md']===$md,'Checkpoint retains provenance and untouched Markdown');
// A missing required field must fail even when the manifest itself has a valid hash.
$bad=$m;unset($bad['reference_origins']);$badref=$point['manifest'];$key='trial/'.$badref['key'];$saved=$s3->objects[$key];
$s3->objects[$key]['Body']=Store::json($bad);$badref['sha256']=hash('sha256',Store::json($bad));
$stopped=false;try{$site->load($badref);}catch(RuntimeException $e){$stopped=$e->getMessage()==='Missing required reference context.';}
check($stopped,'Missing required context must specifically stop loading');$s3->objects[$key]=$saved;
if(isset($argv[2]))file_put_contents($argv[2],Store::json(['objects'=>$s3->objects,'old_original'=>$old,'new_original'=>$o,'old_point'=>$legacyPoint['manifest'],'new_point'=>$point['manifest']]));
echo "PASS: old originals readable, contextual original/snapshot format guards, byte-identical Markdown and Checkpoint provenance\n";
