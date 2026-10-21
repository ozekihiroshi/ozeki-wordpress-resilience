<?php
require __DIR__.'/../src/ObserverAdmin.php';
require __DIR__.'/../src/DailyWatchdogAdmin.php';
require __DIR__.'/../src/PreflightWatchdogAdmin.php';
use Ozeki\Resilience\PreflightWatchdogAdmin;
$p=tempnam(sys_get_temp_dir(),'owr-watchdog-');
define('OWR_PREFLIGHT_SITE_ID','site');
define('OWR_PREFLIGHT_WATCHDOG_REPORTS',['source'=>['path'=>$p,'monitor_id'=>'preflight-source'],'receiver'=>['path'=>$p,'monitor_id'=>'preflight-receiver']]);
$n=0;
function check($ok) {global $n;if(!$ok)throw new RuntimeException('contract failed');++$n;}
try {
 $v=['format'=>'owr-observer-status-v1','site_id'=>'site','monitor_id'=>'preflight-source','observed_at'=>gmdate('c'),'simulated'=>true,
 'targets'=>['reachability'=>['last_seen'=>null,'active'=>[],'pending'=>0,'observation'=>'missing'],
 'watchdog'=>['last_seen'=>null,'active'=>[],'pending'=>0,'observation'=>'missing']],
 'delivery'=>['state'=>'unknown','pending'=>0],'history'=>[],'secret'=>'not public'];
 file_put_contents($p,json_encode($v));$before=hash_file('sha256',$p);
 check(PreflightWatchdogAdmin::read('source')['state']==='current');
 check(PreflightWatchdogAdmin::read('receiver')['state']==='invalid');
 check(PreflightWatchdogAdmin::read('other')['state']==='unavailable');
 check(!isset(PreflightWatchdogAdmin::read('source')['secret']));
 check(hash_file('sha256',$p)===$before);
 foreach (['site_id'=>'other','monitor_id'=>'preflight-receiver','observed_at'=>'2999-01-01T00:00:00Z'] as $k=>$x) {
  $bad=$v;$bad[$k]=$x;file_put_contents($p,json_encode($bad));
  check(PreflightWatchdogAdmin::read('source')['state']==='invalid');
 }
 file_put_contents($p,'{bad');check(PreflightWatchdogAdmin::read('source')['state']==='invalid');
 unlink($p);check(PreflightWatchdogAdmin::read('source')['state']==='unavailable');
 echo "PASS $n daily-watchdog contracts\n";
} finally {if(is_file($p))unlink($p);}
