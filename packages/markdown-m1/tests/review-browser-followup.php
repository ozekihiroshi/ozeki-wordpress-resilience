<?php
$_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot};
if(!str_contains(home_url(),'127.0.0.1:18784')||is_file('/lab/live'))throw new RuntimeException('Not isolated local fixture');
wp_set_current_user(1);
function check_review($v,$m){if(!$v)throw new RuntimeException($m);}
$ids=json_decode(file_get_contents('/lab/review-fixture-ids.json'),true);
$expected=json_decode(file_get_contents('/lab/individual-expected.json'),true);
foreach($expected as $a){
    // Verify the exact posts returned by the successful admin action.
    $matches=array_values(array_filter(get_option('ozeki_resilience_m1_restore_result',[]),fn($r)=>$r['asset']===$a['asset']));
    check_review(count($matches)===1,'Individual UI result missing');$p=get_post($matches[0]['post_id']);
    check_review($p&&$p->post_status==='draft','Individual status changed');
    if($a['type']==='ozmd_document')check_review(get_post_meta($p->ID,'_ozmd_source',true)===$a['source'],'Individual Markdown changed');
    else check_review(!str_contains($p->post_content,'<script')&&str_contains($p->post_content,'24 V'),'Individual article unsafe/missing');
    check_review((new Plugin())->store()->originalSource($a['original'])===$a['source'],'Individual original changed');
}
$raw=get_post_meta($ids['markdown'],'_ozmd_source',true);check_review(str_contains($raw,'Browser Markdown edit 20261124'),'Browser change absent');
$c=(new Plugin())->config();$c['prefix']='browser-resave-'.bin2hex(random_bytes(8)).'/';$c['setup_role']='source';update_option('ozeki_resilience_m1_config',$c,false);
$ref=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);
update_option('home','http://isolated-review-browser-final.invalid');update_option('siteurl','http://isolated-review-browser-final.invalid');
$c['setup_role']='recovery';update_option('ozeki_resilience_m1_config',$c,false);
require_once ABSPATH.'wp-admin/includes/user.php';foreach(get_users() as $u)if(!user_can($u,'manage_options'))wp_delete_user($u->ID,1);
global $wpdb;$before=$wpdb->get_results("SELECT * FROM {$wpdb->posts} ORDER BY ID",ARRAY_A);
$fired=false;$inject=static function($q)use(&$fired,$wpdb){if(!$fired&&str_starts_with($q,'DELETE FROM `'.$wpdb->postmeta.'`')){$fired=true;throw new RuntimeException('Injected replacement interruption');}return $q;};
add_filter('query',$inject);
try{(new SiteSnapshot((new Plugin())->store()))->restore($ref['manifest'],true,'/lab/work');throw new RuntimeException('Injection not exercised');}
catch(RuntimeException $e){check_review($e->getMessage()==='Injected replacement interruption','Unexpected failure: '.$e->getMessage());}
finally{remove_filter('query',$inject);}
check_review($fired,'Fault not reached');check_review($before===$wpdb->get_results("SELECT * FROM {$wpdb->posts} ORDER BY ID",ARRAY_A),'Rollback changed posts');
check_review(glob('/lab/work/owr-recovery-*')===[],'Rolled-back failure left workspace');
(new SiteSnapshot((new Plugin())->store()))->restore($ref['manifest'],true,'/lab/work');
check_review(get_post_meta($ids['markdown'],'_ozmd_source',true)===$raw,'Browser edit changed on next recovery');
check_review(glob('/lab/work/owr-recovery-*')===[],'Successful retry left workspace');
echo json_encode(['individual_admin_restore'=>true,'individual_originals_unchanged'=>true,'browser_edit_recaptured_and_recovered'=>true,'injected_database_interruption'=>true,'rollback_posts_preserved'=>true,'workspace_cleaned'=>true,'retry_completed'=>true]);
