<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/cleanup.php';
require_once $argv[1].'/src/SiteSnapshot.php';
require_once $argv[1].'/src/CheckpointSchedule.php';
use Owr\M1\{Store,SiteSnapshot,CheckpointSchedule};
function lifecycleFixture(){
 $s=new CleanupS3();$st=new Store($s,['bucket'=>'fixture','prefix'=>'site/','retention_days'=>0]);$site=new SiteSnapshot($st);
 $files=['content.json'=>'{}','markdown/old.md'=>"# Unchanged since last year\n",'uploads/old.png'=>'old-image'];
 $a=$site->save($files,['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial']);
 $b=$site->checkpoint($a['manifest']);$c=$site->checkpoint($b['manifest']);
 foreach([$a,$b,$c] as $i=>$cp)foreach($s->dates as $key=>&$date)if(str_starts_with($key,'site/'.dirname($cp['manifest']['key']).'/'))$date=time()-[100,40,10][$i]*86400;unset($date);
 return [$s,$st,$site,$a,$b,$c];
}
[$s,$st,$site,$a,$b,$c]=lifecycleFixture();
ok(count(array_unique([$a['manifest']['key'],$b['manifest']['key'],$c['manifest']['key']]))===3,'Unchanged content produces three independent points');
[$ma,$fa]=$site->load($a['manifest']);[$mc,$fc]=$site->load($c['manifest']);ok($fa===$fc,'Old unchanged original copied unchanged');
foreach($mc['resources'] as $r)ok(str_starts_with($r['key'],dirname($c['manifest']['key']).'/'),'All resources belong to new Checkpoint');
$cutoff=time()-30*86400;$plan=$st->siteCleanupPreview($cutoff);
ok(count($plan['keep'])===2,'Keep boundary Checkpoint and recent Checkpoint');
ok(in_array($a['manifest']['key'],array_column($plan['candidates'],'key')),'Only obsolete point eligible');
$r=$st->siteCleanup($cutoff,$plan['hash']);ok($r['ok']&&count($r['deleted'])>0,'Expired complete point deleted');
ok($site->load($b['manifest'])[1]===$fa&&$site->load($c['manifest'])[1]===$fa,'Retained complete resources independently readable after deletion');
$plan=$st->siteCleanupPreview($cutoff);ok(!$plan['candidates'],'Repeat has no candidates');
[$s,$st,$site,$a,$b,$c]=lifecycleFixture();
$m=$site->load($a['manifest'])[0];$locked=reset($m['resources']);
$s->holds['site/'.$locked['key']]=['ObjectLockRetainUntilDate'=>new DateTimeImmutable('+1 day')];
$plan=$st->siteCleanupPreview(time()-30*86400);ok(!$plan['candidates'],'Lock on one resource blocks whole obsolete point');
$done=$st->siteCleanup($plan['cutoff_timestamp'],$plan['hash']);ok(!$done['deleted']&&count($done['blocked'])>0,'Optional lock wait is explicit; never bypassed');
ok($site->load($a['manifest'])[1]===$fa,'Locked point remains intact');
$s->holds=[];$plan=$st->siteCleanupPreview(time()-30*86400);$s->putObject(['Key'=>'site/unrelated','Body'=>'unknown']);
rejects(fn()=>$st->siteCleanup($plan['cutoff_timestamp'],$plan['hash']));ok(!$s->deleted,'Stale preview refuses deletion');
$plan=$st->siteCleanupPreview(time()-30*86400);$s->failAfter=0;$r=$st->siteCleanup($plan['cutoff_timestamp'],$plan['hash']);ok(!$r['ok']&&!$r['deleted'],'Deletion denied: failure reported');
ok($site->load($c['manifest'])[1]===$fa,'Deletion failure cannot damage latest resources');
$zero=new Store($s,['bucket'=>'fixture','prefix'=>'site/','retention_days'=>0,'cleanup_keep_days'=>365]);ok($zero->requiredRetentionUntil()===null,'Recovery window does not enable AWS lock');
$lockedStore=new Store($s,['bucket'=>'fixture','prefix'=>'site/','retention_days'=>2,'cleanup_keep_days'=>365]);ok(strtotime($lockedStore->requiredRetentionUntil())<time()+3*86400,'AWS protection remains separate from recovery window');
$tz=new DateTimeZone('Asia/Tokyo');$jan=(new DateTimeImmutable('2026-01-31 10:00:00',$tz))->getTimestamp();
$feb=CheckpointSchedule::next($jan,1,'months',$tz,31);$mar=CheckpointSchedule::next($feb,1,'months',$tz,31);
ok((new DateTimeImmutable('@'.$feb))->setTimezone($tz)->format('Y-m-d H:i')==='2026-02-28 10:00','Calendar February clamped');
ok((new DateTimeImmutable('@'.$mar))->setTimezone($tz)->format('Y-m-d H:i')==='2026-03-31 10:00','Calendar anchor retained');
ok(CheckpointSchedule::next($jan,1,'weeks',$tz)===$jan+7*86400,'Weekly interval');
echo "PASS lifecycle: independent unchanged points, complete copied originals, retention boundary, scoped version deletion, lock wait, stale/denied stop, independent AWS lock, calendar month/week. In-memory S3, no cloud writes.\n";
