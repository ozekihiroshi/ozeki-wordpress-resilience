<?php
require __DIR__.'/../src/ObserverAdmin.php';
require __DIR__.'/../src/DailyAdmin.php';
use Ozeki\Resilience\DailyAdmin;
$path=tempnam(sys_get_temp_dir(),'owr-daily-ui-');
define('OWR_DAILY_STATUS_FILE',$path);define('OWR_DAILY_SITE_ID','site');
$checks=0;
function verify($value,$expected) {
    global $path,$checks;
    file_put_contents($path,json_encode($value));
    if (DailyAdmin::read()['state']!==$expected) { throw new RuntimeException('status mismatch'); }
    ++$checks;
}
try {
    $base=['format'=>'owr-daily-admin-v1','site_id'=>'site','observed_at'=>gmdate('c'),
           'missing_due_slot'=>false,'runs'=>[],'attempts'=>[],'secret'=>'NEVER-RENDER-SECRET'];
    foreach (['awaiting_approval','approved','restore_verified','restore_failed','recovery_interrupted',
              'recovery_reviewed_closed','registration_pending','evidence_error','approval_expired','running','unknown'] as $phase) {
        $v=$base;
        $v['runs'][]=['day'=>'2026-10-20','phase'=>$phase,'storage_complete'=>true,'approval_state'=>'approved','restore_state'=>'verified'];
        foreach (['not_recorded','incomplete','closed','automatic_removed','invalid'] as $cleanup) {
            $v['attempts']=[['request_id'=>'trial','day'=>'2026-10-20','state'=>'interrupted','outcome'=>'unknown','registration'=>'unavailable','cleanup'=>$cleanup]];
            verify($v,'current');
        }
    }
    if (isset(DailyAdmin::read()['secret'])) { throw new RuntimeException('secret exposed'); }
    $bad=$base;$bad['site_id']='other';verify($bad,'invalid');
    $bad=$base;$bad['observed_at']='2099-01-01T00:00:00Z';verify($bad,'invalid');
    $bad=$base;$bad['observed_at']=gmdate('c',time()-301);verify($bad,'stale');
    $bad=$base;$bad['missing_due_slot']='false';verify($bad,'invalid');
    $bad=$v;$bad['attempts'][0]['request_id']='<script>evil</script>';verify($bad,'invalid');
    $bad=$v;$bad['runs'][0]['phase']='invented_success';verify($bad,'invalid');
    $bad=$base;$bad['secret']=str_repeat('x',65537);verify($bad,'invalid');
    $bad=$v;$bad['runs']=array_fill(0,31,$v['runs'][0]);verify($bad,'invalid');
    file_put_contents($path,'{bad');if(DailyAdmin::read()['state']!=='invalid'){throw new RuntimeException();}
    unlink($path);if(DailyAdmin::read()['state']!=='unavailable'){throw new RuntimeException();}
    echo "PASS ".($checks+2)." daily admin validation checks\n";
} finally {if(file_exists($path)){unlink($path);}}
