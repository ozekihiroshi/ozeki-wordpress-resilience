<?php
require __DIR__.'/../src/ObserverAdmin.php';
require __DIR__.'/../src/DailyWatchdogAdmin.php';
use Ozeki\Resilience\DailyWatchdogAdmin;
$p=tempnam(sys_get_temp_dir(),'owr-watchdog-');
define('OWR_DAILY_SITE_ID','site');
define('OWR_DAILY_WATCHDOG_REPORTS',['source'=>['path'=>$p,'monitor_id'=>'daily-source'],'receiver'=>['path'=>$p,'monitor_id'=>'daily-receiver']]);
$n=0;
function check($ok) {global $n;if(!$ok)throw new RuntimeException('contract failed');++$n;}
try {
 $v=['format'=>'owr-observer-status-v1','site_id'=>'site','monitor_id'=>'daily-source','observed_at'=>gmdate('c'),'simulated'=>true,
 'targets'=>['reachability'=>['last_seen'=>null,'active'=>[],'pending'=>0,'observation'=>'missing'],
 'watchdog'=>['last_seen'=>null,'active'=>[],'pending'=>0,'observation'=>'missing']],
 'delivery'=>['state'=>'unknown','pending'=>0],'history'=>[],'secret'=>'not public'];
 file_put_contents($p,json_encode($v));$before=hash_file('sha256',$p);
 check(DailyWatchdogAdmin::read('source')['state']==='current');
 check(DailyWatchdogAdmin::read('receiver')['state']==='invalid');
 check(DailyWatchdogAdmin::read('other')['state']==='unavailable');
 check(!isset(DailyWatchdogAdmin::read('source')['secret']));
 check(hash_file('sha256',$p)===$before);
 foreach (['site_id'=>'other','monitor_id'=>'daily-receiver','observed_at'=>'2999-01-01T00:00:00Z'] as $k=>$x) {
  $bad=$v;$bad[$k]=$x;file_put_contents($p,json_encode($bad));
  check(DailyWatchdogAdmin::read('source')['state']==='invalid');
 }
 file_put_contents($p,'{bad');check(DailyWatchdogAdmin::read('source')['state']==='invalid');
 unlink($p);check(DailyWatchdogAdmin::read('source')['state']==='unavailable');
 echo "PASS $n daily-watchdog contracts\n";
} finally {if(is_file($p))unlink($p);}
