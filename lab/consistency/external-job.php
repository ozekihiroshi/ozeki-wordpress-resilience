<?php
// Immutable allowed task: its child is awaited while the outer service holds the gate.
require '/var/www/html/wp-load.php';
global $wpdb;
$id=$argv[1]; $kind=$argv[2];
if (!preg_match('/^[a-zA-Z0-9_-]{1,48}$/D',$id) || !in_array($kind,['write','deploy','slow'],true)) { exit(2); }
$wpdb->query('START TRANSACTION');
try {
    $insert=$wpdb->query($wpdb->prepare('INSERT IGNORE INTO owr_external_jobs(job_id,kind,path,sha256) VALUES(%s,%s,%s,%s)',$id,$kind,'',''));
    if ($insert===false) { throw new RuntimeException('job insert failed'); }
    if ($insert===0) {
        $previous=$wpdb->get_var($wpdb->prepare('SELECT kind FROM owr_external_jobs WHERE job_id=%s',$id));
        $wpdb->query('ROLLBACK');
        if ($previous!==$kind) { throw new RuntimeException('job identity conflict'); }
        echo '{"state":"done","duplicate":true}'; exit;
    }
    $relative='external-'.$id.'.txt';
    $path=WP_CONTENT_DIR.'/uploads/'.$relative;
    $payload='job:'.$id.':'.$kind;
    file_put_contents('/tmp/owr-external-active-'.$id,'1');
    $child=proc_open(['/usr/local/bin/php','-r','usleep((int)$argv[3]); if(file_put_contents($argv[1],$argv[2])===false) exit(1);',$path,$payload,$kind==='slow'?'3000000':'0'],[0=>['file','/dev/null','r'],1=>['file','/dev/null','w'],2=>['file','/dev/null','w']],$pipes);
    if (!is_resource($child) || proc_close($child)!==0) { throw new RuntimeException('child failed'); }
    $post=wp_insert_post(['post_title'=>'External '.$id,'post_status'=>'publish'],true);
    if (is_wp_error($post)) { throw new RuntimeException('post failed'); }
    if ($wpdb->query($wpdb->prepare('UPDATE owr_external_jobs SET path=%s,sha256=%s WHERE job_id=%s',$relative,hash_file('sha256',$path),$id))===false) { throw new RuntimeException('job update failed'); }
    $wpdb->query('COMMIT');echo '{"state":"done","duplicate":false}';
} finally { $wpdb->query('ROLLBACK'); @unlink('/tmp/owr-external-active-'.$id); }
