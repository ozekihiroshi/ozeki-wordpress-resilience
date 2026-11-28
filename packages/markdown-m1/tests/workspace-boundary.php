<?php
$base=sys_get_temp_dir().'/owr-path-'.bin2hex(random_bytes(8));mkdir($base);mkdir($base.'/wp');mkdir($base.'/wp-child');mkdir($base.'/wp/internal');define('ABSPATH',$base.'/wp/');
require __DIR__.'/../src/RecoveryWorkspace.php';
use OzekiResilience\M1\RecoveryWorkspace;
try {
    RecoveryWorkspace::requirePrivateParent($base.'/wp-child');
    $w=new RecoveryWorkspace($base.'/wp-child');RecoveryWorkspace::requirePrivateParent($w->path());$w->finish();
    foreach([$base.'/wp',$base.'/wp/internal'] as $bad){$rejected=false;try{RecoveryWorkspace::requirePrivateParent($bad);}catch(RuntimeException $e){$rejected=true;}if(!$rejected)throw new RuntimeException('Internal path accepted');}
    if(symlink($base.'/wp/internal',$base.'/linked')){try{RecoveryWorkspace::requirePrivateParent($base.'/linked');throw new LogicException('Symlink accepted');}catch(RuntimeException $e){}unlink($base.'/linked');}
    echo "Directory boundary PASS\n";
}finally{rmdir($base.'/wp/internal');rmdir($base.'/wp');rmdir($base.'/wp-child');rmdir($base);}
