<?php
define('ABSPATH',__DIR__.'/');
require __DIR__.'/../src/RecoveryWorkspace.php';
use OzekiResilience\M1\RecoveryWorkspace;
$parent=sys_get_temp_dir().'/owr-workspace-test-'.bin2hex(random_bytes(8));mkdir($parent,0700);
file_put_contents($parent.'/unrelated','keep');
$w=new RecoveryWorkspace($parent);$path=$w->path();file_put_contents($path.'/before-content.json','private');
if(RecoveryWorkspace::unfinished($parent))throw new RuntimeException('Active workspace marked abandoned');
$w->finish();
if(is_dir($path)||file_get_contents($parent.'/unrelated')!=='keep')throw new RuntimeException('Ownership cleanup failed');
$w=new RecoveryWorkspace($parent);$path=$w->path();file_put_contents($path.'/before-content.json','rollback');$w->retain();unset($w);
if(!is_file($path.'/before-content.json'))throw new RuntimeException('Rollback evidence erased');
if(RecoveryWorkspace::unfinished($parent)!==[$path])throw new RuntimeException('Interrupted workspace not detected');
unlink($path.'/before-content.json');unlink($path.'/.owner');rmdir($path);unlink($parent.'/unrelated');rmdir($parent);
echo "Workspace cleanup and rollback retention PASS\n";
