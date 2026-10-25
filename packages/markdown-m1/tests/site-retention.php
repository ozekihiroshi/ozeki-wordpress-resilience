<?php
require __DIR__.'/cleanup.php';
require_once $argv[1].'/src/SiteSnapshot.php';
require_once $argv[1].'/src/Plugin.php';
use Owr\M1\Store;
use Owr\M1\SiteSnapshot;
function get_option($key,$default=false){return $GLOBALS['test_options'][$key]??$default;}
function update_option($key,$value,$autoload=false){$GLOBALS['test_options'][$key]=$value;}
class PreviewDb {
 public string $prefix='test_',$posts='posts',$postmeta='postmeta',$options='options';
 function prepare($sql,...$args){return $sql;}
 function get_var($sql){return str_contains($sql,'ENGINE')?'InnoDB':1;}
}
$s=new CleanupS3();$store=new Store($s,['bucket'=>'test','prefix'=>'site/']);
$site=new SiteSnapshot($store);
$m=['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial'];
$a=$site->save(['content.json'=>'{}','uploads/a.png'=>'first'],$m);
add($store,1,'a','first change');
$m['through']=1;$m['origin']='confirmed_s3';
$b=$site->save(['content.json'=>'{}','uploads/a.png'=>'second'],$m);
$image=$store->put('originals/a/tail/media/b.png','tail-image','image/png');
$attrs=material('tail','a')['row']['attributes'];$attrs['media']=[['files'=>['uploads/b.png'=>$image]]];
$o=$store->prepare('a','tail','tail',$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>2,'original'=>$o,'attributes'=>$attrs]);
$store->put('unknown/resource','unknown','text/plain');
$before=$s->objects;$p=$store->siteCleanupPreview(time());
ok($p['from']===1&&$p['through']===2&&$p['tail_count']===1,'latest baseline and contiguous tail');
ok(count($p['keep'])===1&&$p['keep'][0]['key']===$b['manifest']['key'],'latest by boundary');
ok(in_array($image['key'],array_column($p['retained'],'key'),true),'nested tail image retained');
ok(in_array($a['manifest']['key'],array_column($p['candidates'],'key'),true),'old complete snapshot candidate');
ok(in_array('unknown/resource',array_column($p['blocked'],'key'),true),'unknown retained');
ok($before===$s->objects&&!$s->deleted,'preview has no S3 mutation');
rejects(fn()=>$store->cleanupPlan(time()));
$s->holds['site/'.$a['manifest']['key']]=['ObjectLockLegalHoldStatus'=>'ON'];
$p=$store->siteCleanupPreview(time());ok(in_array($a['manifest']['key'],array_column($p['blocked'],'key'),true),'hold blocks candidate');
$s->denyLockRead=true;$p=$store->siteCleanupPreview(time());ok(!$p['candidates'],'unknown retention never eligible');$s->denyLockRead=false;
$s->dates['site/'.$a['manifest']['key']]=time();$p=$store->siteCleanupPreview(time()-1);ok(count($p['keep'])===2&&$p['from']===0,'window uses S3 timestamp');
$saved=$s->objects['site/history/00000000000000000001.json'];unset($s->objects['site/history/00000000000000000001.json']);rejects(fn()=>$store->siteCleanupPreview(time()-1));$s->objects['site/history/00000000000000000001.json']=$saved;
$s->duplicate=true;rejects(fn()=>$store->siteCleanupPreview(time()));$s->duplicate=false;
function esc_html($s){return htmlspecialchars((string)$s,ENT_QUOTES,'UTF-8');}
ob_start();Owr\M1\Plugin::renderSiteCleanup($p);$html=ob_get_clean();ok(str_contains($html,'Assets to retain')&&str_contains($html,'Deletion candidates')&&!str_contains($html,'cleanup_execute'),'read-only UI');
ob_start();Owr\M1\Plugin::renderSiteCleanup(['error'=>'Pending <operation>']);$html=ob_get_clean();ok(str_contains($html,'Candidates not calculated')&&str_contains($html,'&lt;operation&gt;'),'failure is not zero candidates and escaped');
echo "PASS complete-site retention: independent baselines, fixed-version time, media tail, holds, unknowns, missing history, ambiguity, no writes/deletion, display.\n";
$wpdb=new PreviewDb();foreach(['owr_m1_pending','owr_m1_comment_pending'] as $queue){$GLOBALS['test_options']=[$queue=>['operation'=>'pending']];$r=(new Owr\M1\Plugin())->previewSiteCleanup();ok(str_contains($r['error'],'pending'),'both pending queues stop before S3');}
echo "PASS both pending queues prevent calculation and replace stale preview.\n";
