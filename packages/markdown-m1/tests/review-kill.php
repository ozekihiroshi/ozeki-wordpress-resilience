<?php
// Disposable /lab only. The external runner kills this PHP PID, never the server.
$_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,RecoveryWorkspace};
require_once WP_PLUGIN_DIR.'/ozeki-resilience/src/RecoveryWorkspace.php';
if(is_file('/lab/live')||!is_dir('/lab/objects'))throw new RuntimeException('Isolated local fixture required');
wp_set_current_user(1);global $wpdb;
$mode=$argv[1]??'';$phase=$argv[2]??'during-sql';$state='/lab/kill-state.json';
function kill_check($v,$m){if(!$v)throw new RuntimeException($m);}
if($mode==='prepare'){
    $run=bin2hex(random_bytes(8));$from='http://isolated-kill-source-'.$run.'.invalid';
    update_option('home',$from);update_option('siteurl',$from);
    $c=(new Plugin())->config();$c['prefix']='kill-'.$run.'/';$c['bucket']='isolated';unset($c['owner']);$c['setup_role']='source';$c['protect']=false;update_option('ozeki_resilience_m1_config',$c,false);
    $id=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>'Kill trial '.$run,'post_content'=>'<p>Recovered value</p>']);
    $u=wp_upload_dir();$path=$u['path'].'/kill-'.$run.'.png';$bytes=base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=');file_put_contents($path,$bytes);
    $aid=wp_insert_attachment(['post_title'=>'Synthetic image','post_status'=>'inherit','post_mime_type'=>'image/png','post_parent'=>$id],$path);update_attached_file($aid,$path);
    wp_update_attachment_metadata($aid,['width'=>1,'height'=>1,'file'=>get_post_meta($aid,'_wp_attached_file',true),'sizes'=>[]]);
    $ref=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);
    unlink($path); // This case's new fixture file only; archived original remains.
    wp_update_post(['ID'=>$id,'post_content'=>'<p>Destination before recovery</p>']);
    update_option('home','http://isolated-kill-target-'.$run.'.invalid');update_option('siteurl','http://isolated-kill-target-'.$run.'.invalid');
    $c['setup_role']='recovery';update_option('ozeki_resilience_m1_config',$c,false);
    require_once ABSPATH.'wp-admin/includes/user.php';foreach(get_users() as $u)if(!user_can($u,'manage_options'))wp_delete_user($u->ID,1);
    SiteSnapshot::writeOption('ozeki_resilience_site_restore_attempt',['status'=>'running','fixture'=>$run],false);
    file_put_contents($state,json_encode(['id'=>$id,'path'=>$path,'sha256'=>hash('sha256',$bytes),'manifest'=>$ref['manifest']]));echo "prepared\n";exit;
}
$x=json_decode(file_get_contents($state),true);
if($mode==='recover'){
    $commit=false;
    add_filter('query',static function($q)use($phase,&$commit,$wpdb){
        $hit=($phase==='before-sql'&&$q==='START TRANSACTION')||($phase==='during-sql'&&str_starts_with($q,'DELETE FROM `'.$wpdb->postmeta.'`'))||($phase==='after-commit'&&$commit);
        if($q==='COMMIT')$commit=true;
        if($hit){file_put_contents('/lab/kill-ready.json',json_encode(['pid'=>getmypid(),'phase'=>$phase]));while(true)usleep(100000);}
        return $q;
    });
    (new SiteSnapshot((new Plugin())->store()))->restore($x['manifest'],true,sys_get_temp_dir());
    throw new RuntimeException('Kill point not reached');
}
if($mode==='check'){
    $dirs=RecoveryWorkspace::unfinished(sys_get_temp_dir());kill_check(count($dirs)>0,'Interrupted workspace not detected');
    kill_check(get_option('ozeki_resilience_site_restore_attempt')['status']==='running','Killed operation reported success');
    $body=get_post($x['id'])->post_content;
    kill_check(str_contains($body,$phase==='after-commit'?'Recovered value':'Destination before recovery'),'Unexpected DB commit state');
    kill_check(is_file($x['path'])&&hash_file('sha256',$x['path'])===$x['sha256'],'Expected installed synthetic file absent');
    foreach($dirs as $dir){kill_check((fileperms($dir)&0777)===0700,'Staging not private');kill_check(is_file($dir.'/before-content.json')&&is_file($dir.'/before-files.json'),'Rollback evidence missing');}
    (new SiteSnapshot((new Plugin())->store()))->restore($x['manifest'],true,sys_get_temp_dir());
    kill_check(str_contains(get_post($x['id'])->post_content,'Recovered value'),'Retry did not restore content');
    kill_check(!str_contains(apply_filters('the_content',get_post($x['id'])->post_content),'PROBE_EXECUTED'),'Unsafe content on retry');
    // Explicitly remove only this fixture's already-reviewed retained evidence.
    foreach($dirs as $dir){
        kill_check(preg_match('~/owr-recovery-[a-f0-9]{32}$~D',$dir)&&!is_link($dir),'Unexpected fixture staging path');
        kill_check(array_diff(scandir($dir),['.','..','.owner','before-content.json','before-files.json','before-options.json'])===[],'Unexpected evidence file');
        foreach(['before-content.json','before-files.json','before-options.json','.owner'] as $name)if(is_file($dir.'/'.$name))unlink($dir.'/'.$name);
        rmdir($dir);
    }
    echo json_encode(['phase'=>$phase,'interrupted_detected'=>true,'success_not_claimed'=>true,'db_commit_state_correct'=>true,'files_may_precede_db_commit'=>true,'private_evidence_retained'=>true,'same_point_retry_succeeded'=>true]);
}
