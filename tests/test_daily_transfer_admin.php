<?php
require __DIR__.'/../src/ObserverAdmin.php';
require __DIR__.'/../src/DailyAdmin.php';
use Ozeki\Resilience\DailyAdmin;
$report=tempnam(sys_get_temp_dir(),'daily-');$health=tempnam(sys_get_temp_dir(),'health-');
define('OWR_DAILY_SITE_ID','site');define('OWR_DAILY_STATUS_FILE',$report);define('OWR_DAILY_TRANSFER_FILE',$health);
file_put_contents($report,'{}');$checks=0;
function verify($value,$expected) {
    global $health,$checks;
    file_put_contents($health,json_encode($value));
    if(DailyAdmin::transfer()['state']!==$expected){throw new RuntimeException($expected);}
    ++$checks;
}
try {
    $base=['format'=>'owr-daily-transfer-v1','site_id'=>'site','attempted_at'=>gmdate('c'),'report_sha256'=>hash_file('sha256',$report),'state'=>'ok'];
    foreach(['ok','transfer_failed','source_failed','source_stale'] as $state){verify(array_replace($base,['state'=>$state]),$state);}
    verify(array_replace($base,['attempted_at'=>gmdate('c',time()-301)]),'stopped');
    verify(array_replace($base,['attempted_at'=>'2099-01-01T00:00:00Z']),'invalid');
    verify(array_replace($base,['site_id'=>'other']),'invalid');
    verify(array_replace($base,['report_sha256'=>null]),'invalid');
    verify(array_replace($base,['state'=>'transfer_failed','report_sha256'=>null]),'transfer_failed');
    file_put_contents($report,'changed');verify($base,'invalid');
    unlink($health);
    if(DailyAdmin::transfer()['state']!=='unavailable'){throw new RuntimeException();}
    echo 'PASS '.($checks+1)." transfer display checks\n";
} finally {if(file_exists($report)){unlink($report);}if(file_exists($health)){unlink($health);}}
