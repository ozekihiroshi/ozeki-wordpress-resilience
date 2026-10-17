<?php
if (getenv('OWR_FIXTURE') !== '1') { throw new RuntimeException('Fixture required.'); }
$_SERVER['HTTP_HOST']='localhost:18081'; $_SERVER['SERVER_PORT']='18081'; $_SERVER['REQUEST_URI']='/';
require '/var/www/html/wp-load.php';
require_once ABSPATH.'wp-admin/includes/plugin.php';
$checks=[];
function checkFixture(bool $ok,string $name):void {global $checks;$checks[]=['name'=>$name,'passed'=>$ok];}
$ids=get_option('owr_fixture_ids');
checkFixture(is_array($ids),'baseline_ids');
if(!is_array($ids)){throw new RuntimeException('Baseline not seeded.');}
foreach(['home'=>'OWR-HOME','services'=>'OWR-SERVICES','contact'=>'OWR-CONTACT','post'=>'OWR-NEWS'] as $key=>$marker){
    $p=get_post($ids[$key]);checkFixture($p && $p->post_status==='publish' && str_contains($p->post_content,$marker),'db_'.$key);
}
checkFixture(get_option('owr_fixture_nested')===['message'=>'復旧基準 🌱','enabled'=>true,'count'=>7],'serialized_option');
checkFixture((int)get_option('page_on_front')===$ids['home'],'front_page');
checkFixture(is_plugin_active('ozeki-database-backup-for-s3/ozeki-database-backup-for-s3.php'),'backup_plugin_active');
checkFixture(get_stylesheet()==='twentytwentyfive','theme');
checkFixture(DISABLE_WP_CRON && WP_HTTP_BLOCK_EXTERNAL,'fixture_controls');
checkFixture(is_wp_error(wp_remote_get('https://example.invalid')),'external_http_blocked');
checkFixture(wp_mail('nobody@example.invalid','test','test')===false,'mail_blocked');
$media=[];
foreach($ids['assets'] as $name=>$asset){
    $path=get_attached_file($asset['id']);
    checkFixture(is_file($path) && hash_file('sha256',$path)===$asset['sha256'],'media_hash_'.$name);
    checkFixture((int)get_post($asset['id'])->post_parent===$ids['home'],'attachment_parent_'.$name);
    $media[$name]=$asset;
}
$databaseBaseline=[];
foreach(['home','services','contact','post'] as $key){
    $p=get_post($ids[$key]);
    $databaseBaseline[$key]=array_intersect_key((array)$p,array_flip(['ID','post_title','post_content','post_status','post_type','post_parent','post_author']));
}
$uploads=wp_get_upload_dir()['basedir'];$inventory=[];
foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator($uploads,FilesystemIterator::SKIP_DOTS)) as $file){
    if($file->isLink()){throw new RuntimeException('Unexpected symlink in fixture uploads.');}
    if($file->isFile()){$inventory[]=['path'=>substr($file->getPathname(),strlen($uploads)+1),'bytes'=>$file->getSize(),'sha256'=>hash_file('sha256',$file->getPathname())];}
}
usort($inventory,static fn($a,$b)=>strcmp($a['path'],$b['path']));
// Report is baseline verification, never an E3 recovery claim.
$theme=wp_get_theme();$plugins=get_plugins();
$report=['schema_version'=>1,'kind'=>'phase1_source_baseline','checked_at'=>gmdate('c'),'environment'=>['wordpress'=>$GLOBALS['wp_version'],'php'=>PHP_VERSION,'database'=>$GLOBALS['wpdb']->db_server_info(),'theme'=>['name'=>get_stylesheet(),'version'=>$theme->get('Version')],'backup_plugin'=>$plugins['ozeki-database-backup-for-s3/ozeki-database-backup-for-s3.php']['Version']], 'ids'=>$ids,'database_baseline'=>$databaseBaseline,'upload_inventory'=>$inventory,'media'=>$media,'checks'=>$checks,'passed'=>!in_array(false,array_column($checks,'passed'),true)];
echo json_encode($report,JSON_THROW_ON_ERROR|JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT)."\n";
exit($report['passed']?0:1);
