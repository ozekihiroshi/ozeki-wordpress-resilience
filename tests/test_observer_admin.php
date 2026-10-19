<?php
require __DIR__.'/../src/ObserverAdmin.php';
use Ozeki\Resilience\ObserverAdmin;
$path=tempnam(sys_get_temp_dir(),'owr-ui-');define('OWR_OBSERVER_STATUS_FILE',$path);
$settings=['site_id'=>'site'];$checks=0;
function check($expected,$label) { global $checks,$settings;if(ObserverAdmin::status($settings)['state']!==$expected){throw new RuntimeException($label);}++$checks; }
try {
 $report=['format'=>'owr-observer-status-v1','site_id'=>'site','monitor_id'=>'watchdog','observed_at'=>gmdate('c'),'simulated'=>true,'targets'=>[],'delivery'=>['state'=>'ok','pending'=>0],'history'=>[]];
 foreach(['reachability','watchdog'] as $key){$report['targets'][$key]=['last_seen'=>gmdate('c'),'active'=>[],'pending'=>0,'observation'=>'confirmed'];}
 file_put_contents($path,json_encode($report));check('current','healthy');
 $report['history'][]=['target'=>'watchdog','kind'=>'monitor_stopped','transition'=>'resolved','at'=>gmdate('c')];
 file_put_contents($path,json_encode($report));check('current','recovery');
 if(ObserverAdmin::status($settings)['history'][0]['transition']!=='resolved'){throw new RuntimeException('history lost');}
 $bad=$report;$bad['targets']['watchdog']['pending']=-1;file_put_contents($path,json_encode($bad));check('invalid','negative');
 $bad=$report;$bad['targets']['watchdog']['active']=['<script>evil</script>'];file_put_contents($path,json_encode($bad));check('invalid','alarm injection');
 $bad=$report;$bad['observed_at']='tomorrow';file_put_contents($path,json_encode($bad));check('invalid','relative timestamp');
 $bad=$report;$bad['targets']['watchdog']['active']=[[]];file_put_contents($path,json_encode($bad));check('invalid','wrong type');
 $bad=$report;$bad['observed_at']=gmdate('c',time()-301);foreach($bad['targets'] as &$t){$t['last_seen']=null;}unset($t);$bad['history']=[];file_put_contents($path,json_encode($bad));check('stale','stale');
 file_put_contents($path,str_repeat('x',32769));check('invalid','oversize');
 unlink($path);check('unavailable','missing');
 echo "PASS $checks PHP status checks\n";
} finally {if(file_exists($path)){unlink($path);}}
