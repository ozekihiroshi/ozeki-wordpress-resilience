<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require __DIR__.'/checkpoint-lifecycle.php';
require_once $argv[1].'/src/GfsPolicy.php';
use OzekiResilience\M1\{GfsPolicy,Store,SiteSnapshot};
$zone=new DateTimeZone('Asia/Tokyo');
$rules=['weekly'=>['enabled'=>1,'weekday'=>0,'time'=>'02:00','keep'=>2], 'monthly'=>['enabled'=>1,'day'=>1,'time'=>'02:00','keep'=>3], 'yearly'=>['enabled'=>1,'month'=>1,'day'=>1,'time'=>'02:00','keep'=>3]];
$after=(new DateTimeImmutable('2022-12-31 23:00',$zone))->getTimestamp();
$slot=GfsPolicy::next($rules,$after,$zone);ok(count($slot['rules'])===3,'Sunday Jan 1 overlaps all three rules');
ok($slot['at']===(new DateTimeImmutable('2023-01-01 02:00',$zone))->getTimestamp(),'Configured timezone and time');
$labels=GfsPolicy::labels($slot['rules'],$slot['at'],$zone);
ok(GfsPolicy::active($labels,strtotime('2023-05-01')),'Yearly survives weekly and monthly expiry');
ok(!GfsPolicy::active($labels,strtotime('2026-01-02')),'All labels expire');
$other=$rules;$other['monthly']['time']='03:00';$other['yearly']['time']='04:00';
$next=GfsPolicy::next($other,$after,$zone);ok(array_keys($next['rules'])===['weekly'],'Different times not coalesced');
$next=GfsPolicy::next($other,$next['at'],$zone);ok(array_keys($next['rules'])===['monthly'],'Later same day retained');
$month=['monthly'=>['enabled'=>1,'day'=>31,'time'=>'02:00','keep'=>3]];
$feb=GfsPolicy::next($month,strtotime('2024-02-01'),$zone);ok(gmdate('Y-m-d',$feb['at'])==='2024-02-28','Leap month end in UTC is previous day for JST 02:00');
ok((new DateTimeImmutable('@'.$feb['at']))->setTimezone($zone)->format('Y-m-d')==='2024-02-29','Leap month calendar');
ok(GfsPolicy::next([],time(),$zone)===null,'Disabled scheduling');
rejects(fn()=>GfsPolicy::normalize(['weekly'=>['enabled'=>1,'time'=>'25:00','weekday'=>0,'keep'=>2]]));
[$s,$st,$site,$a,$b,$c]=lifecycleFixture();
// Change only this memory fixture's old manifest to model independent W/M/Y expiry.
$key='site/'.$a['manifest']['key'];$old=json_decode($s->objects[$key]['Body'],true);
$old['gfs']=['weekly'=>['expires_at'=>gmdate('c',time()-86400)],'monthly'=>['expires_at'=>gmdate('c',time()-1)],'yearly'=>['expires_at'=>gmdate('c',time()+86400)]];
$s->objects[$key]['Body']=Store::json($old);
$p=$st->siteCleanupPreview(time()-30*86400);
ok(in_array($a['manifest']['key'],array_column($p['keep'],'key')),'Yearly label keeps old full point');
ok($p['from']===0,'No fabricated history required');
ok(!in_array($a['manifest']['key'],array_column($p['candidates'],'key')),'Old GFS point cannot be deleted');
$old['gfs']['yearly']['expires_at']=gmdate('c',time()-1);$s->objects[$key]['Body']=Store::json($old);
$p=$st->siteCleanupPreview(time()-30*86400);ok(in_array($a['manifest']['key'],array_column($p['candidates'],'key')),'Eligible when all labels expire');
// A retained historical GFS point must not pin all intermediate histories.
$s2=new CleanupS3();$st2=new Store($s2,['bucket'=>'fixture','prefix'=>'site/']);$site2=new SiteSnapshot($st2);
$base=['schema'=>'owr-site-snapshot-1','through'=>0,'origin'=>'administrator_initial'];
$oldPoint=$site2->save(['content.json'=>'{}'],$base,['at'=>time()-86400,'timezone'=>'UTC','rules'=>['yearly'=>$rules['yearly']]]);
add($st2,1,'a','history now covered');$base['through']=1;$newPoint=$site2->save(['content.json'=>'{}'],$base);
foreach($s2->dates as $k=>&$d)$d=time()-100*86400;unset($d);
$s2->dates['site/'.$newPoint['manifest']['key']]=time()-40*86400;
$p=$st2->siteCleanupPreview(time()-30*86400);ok($p['from']===1&&in_array('history/00000000000000000001.json',array_column($p['candidates'],'key')),'GFS archive does not pin historical chain');
$done=$st2->siteCleanup($p['cutoff_timestamp'],$p['hash']);ok($done['ok'],'Covered history deleted in memory');$site2->load($oldPoint['manifest']);$site2->load($newPoint['manifest']);
$created=$site2->checkpoint($newPoint['manifest'],$slot);$m=$site2->load($created['manifest'])[0];ok(count($m['gfs'])===3&&$m['scheduled_at']===gmdate('c',$slot['at']),'One manifest holds three labels');
$manual=$site2->checkpoint($created['manifest']);ok(!isset($site2->load($manual['manifest'])[0]['gfs']),'Manual point does not inherit old labels');
echo "PASS GFS: W/M/Y schedule collision, separate times, calendar month, validation, S3 labels, all-label retention, no archive history pin, independent manual point. Memory S3 only.\n";
