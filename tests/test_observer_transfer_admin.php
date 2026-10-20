<?php
require __DIR__.'/../src/ObserverAdmin.php';
require __DIR__.'/../src/DailyWatchdogAdmin.php';
use Ozeki\Resilience\DailyWatchdogAdmin;
$p=tempnam(sys_get_temp_dir(),'owr-health-');
define('OWR_DAILY_SITE_ID','site');
define('OWR_DAILY_WATCHDOG_REPORTS',['source'=>['monitor_id'=>'source','transfer_file'=>$p]]);
$n=0;function check($v){global $n;if(!$v)throw new RuntimeException('failed');++$n;}
try {
 $v=['format'=>'owr-observer-transfer-v1','site_id'=>'site','monitor_id'=>'source','attempted_at'=>gmdate('c'),'state'=>'ok'];
 foreach(['ok','transfer_failed','source_stale'] as $state){$v['state']=$state;file_put_contents($p,json_encode($v));check(DailyWatchdogAdmin::transfer('source')['state']===$state);}
 $v['attempted_at']=gmdate('c',time()-310);file_put_contents($p,json_encode($v));check(DailyWatchdogAdmin::transfer('source')['state']==='stopped');
 $v['attempted_at']=gmdate('c',time()+3600);file_put_contents($p,json_encode($v));check(DailyWatchdogAdmin::transfer('source')['state']==='invalid');
 $v['attempted_at']=gmdate('c');$v['monitor_id']='wrong';file_put_contents($p,json_encode($v));check(DailyWatchdogAdmin::transfer('source')['state']==='invalid');
 $v['monitor_id']='source';$v['site_id']='wrong';file_put_contents($p,json_encode($v));check(DailyWatchdogAdmin::transfer('source')['state']==='invalid');
 file_put_contents($p,'{');check(DailyWatchdogAdmin::transfer('source')['state']==='invalid');
 file_put_contents($p,str_repeat('x',8193));check(DailyWatchdogAdmin::transfer('source')['state']==='invalid');
 check(DailyWatchdogAdmin::transfer('receiver')['state']==='unavailable');
 echo "PASS $n transfer display contracts\n";
}finally{unlink($p);}
