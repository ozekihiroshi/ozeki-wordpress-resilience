<?php
require __DIR__.'/../src/ObserverAdmin.php';require __DIR__.'/../src/PreflightAdmin.php';
use Ozeki\Resilience\PreflightAdmin;
$n=0;function check($v){global $n;if(!$v)throw new RuntimeException('review contract');$n++;}
$v=['format'=>'owr-operator-review-status-v1','state'=>'valid','reviewed_at'=>gmdate('c',time()-86400),'expires_at'=>gmdate('c',time()+86400),'reasons'=>[],'automatic_checks_passed'=>true,'secret'=>'NEVER_RENDER_SECRET'];
check(PreflightAdmin::review($v)['state']==='valid');check(!isset(PreflightAdmin::review($v)['secret']));
foreach(['revoked','expired','reconfirmation_required','missing','invalid'] as $state){$x=$v;$x['state']=$state;check(PreflightAdmin::review($x)['state']===$state);}
$x=$v;$x['expires_at']=gmdate('c',time()-1);check(PreflightAdmin::review($x)['state']==='expired');
$x=$v;$x['reasons']=['<script>evil</script>'];check(PreflightAdmin::review($x)['state']==='invalid');
$x=$v;$x['expires_at']=gmdate('c',time()+604800);check(PreflightAdmin::review($x)['state']==='invalid');
check(PreflightAdmin::review(null)['state']==='missing');echo "PASS $n review contracts\n";
