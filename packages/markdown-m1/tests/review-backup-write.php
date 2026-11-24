<?php
namespace OzekiResilience\M1 {
    // Deterministic local I/O failure, without filling any real filesystem.
    function file_put_contents($path,$data) {
        if(($GLOBALS['backup_failure']??'')==='short'&&str_ends_with($path,'/before-content.json'))return \file_put_contents($path,substr($data,0,1));
        return \file_put_contents($path,$data);
    }
    function chmod($path,$mode) {
        if(($GLOBALS['backup_failure']??'')==='mode'&&str_ends_with($path,'/before-content.json'))return false;
        return \chmod($path,$mode);
    }
}
namespace {
    define('ABSPATH',__DIR__.'/');
    require __DIR__.'/../src/RecoveryWorkspace.php';
    use OzekiResilience\M1\RecoveryWorkspace;
    $parent=sys_get_temp_dir().'/owr-backup-write-'.bin2hex(random_bytes(8));mkdir($parent,0700);
    try {
        foreach(['','short','mode'] as $failure){
            $w=new RecoveryWorkspace($parent);$path=$w->path();$GLOBALS['backup_failure']=$failure;$caught=false;
            try {RecoveryWorkspace::writeBackup($path,'before-content.json','{"before":"unchanged"}');}
            catch(\RuntimeException $e){$caught=true;}
            if($caught!==($failure!==''))throw new \RuntimeException('Backup write failure was not correctly detected: '.$failure);
            if($failure===''&&((fileperms($path.'/before-content.json')&0777)!==0600||file_get_contents($path.'/before-content.json')!=='{"before":"unchanged"}'))throw new \RuntimeException('Successful backup changed data or permissions');
            $w->finish();if(is_dir($path))throw new \RuntimeException('Failed preflight backup not cleaned');
        }
    } finally {unset($GLOBALS['backup_failure']);rmdir($parent);}
    echo "Private backup complete write, permissions and failure cleanup PASS\n";
}
