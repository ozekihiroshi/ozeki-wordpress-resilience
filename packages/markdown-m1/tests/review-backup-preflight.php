<?php
namespace OzekiResilience\M1 {
    function file_put_contents($path,$data) {
        if(str_ends_with($path,'/'.($GLOBALS['backup_fail_name']??'never')))return 0;
        return \file_put_contents($path,$data);
    }
}
namespace {
    // Use only the fresh synthetic fixture produced by review-kill.php prepare.
    $_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
    use OzekiResilience\M1\{Plugin,SiteSnapshot,RecoveryWorkspace};
    if(!str_contains(home_url(),'isolated-kill-target-')||is_file('/lab/live'))throw new \RuntimeException('Not the isolated local fixture');
    wp_set_current_user(1);$x=json_decode(file_get_contents('/lab/kill-state.json'),true);
    $before=get_post($x['id'])->post_content;
    if(is_file($x['path']))throw new \RuntimeException('Expected fresh destination without fixture image');
    $results=[];
    foreach(['before-content.json','before-files.json','before-options.json'] as $name){
        $GLOBALS['backup_fail_name']=$name;$caught=false;
        try{(new SiteSnapshot((new Plugin())->store()))->restore($x['manifest'],true,sys_get_temp_dir());}
        catch(\RuntimeException $e){if(!str_contains($e->getMessage(),'Cannot complete private recovery backup'))throw $e;$caught=true;}
        clean_post_cache($x['id']);
        if(!$caught||get_post($x['id'])->post_content!==$before||is_file($x['path'])||RecoveryWorkspace::unfinished(sys_get_temp_dir()))throw new \RuntimeException('Preflight failure modified content or leaked staging: '.$name);
        $results[]=['file'=>$name,'stopped_before_replacement'=>true,'cleanup'=>true];
    }
    unset($GLOBALS['backup_fail_name']);echo json_encode($results,JSON_PRETTY_PRINT).PHP_EOL;
}
