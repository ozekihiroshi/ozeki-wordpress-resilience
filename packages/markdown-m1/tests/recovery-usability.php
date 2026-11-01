<?php
// Run inside the existing dm onboarding fixture after deploying the candidate.
require '/var/www/html/owr-guide-run/wp-load.php';
require_once ABSPATH.'wp-admin/includes/template.php';
if($wpdb->prefix!=='owrguide_20261026_target_')throw new RuntimeException('Wrong fixture');
wp_set_current_user(get_user_by('login','guideoperator')->ID);
function verify(bool $ok,string $message): void {if(!$ok)throw new RuntimeException($message);}
$fake=new class {public int $calls=0;public function __call($name,$args){$this->calls++;throw new RuntimeException('Unexpected SDK call');}};
$store=new OzekiResilience\M1\Store($fake,['setup_role'=>'recovery']);
foreach([
    fn()=>$store->put('test','body','text/plain'),
    fn()=>$store->ensureRetention(['key'=>'test'],'2030-01-01T00:00:00Z'),
    fn()=>$store->siteCleanup(0,'invalid'),
    fn()=>$store->cleanup(0,'invalid'),
] as $operation){
    $blocked=false;try{$operation();}catch(RuntimeException $e){$blocked=str_contains($e->getMessage(),'only reads S3');}
    verify($blocked,'Recovery mutation was not rejected');
}
verify($fake->calls===0,'Mutation reached S3');
$old=get_option('ozeki_resilience_m1_config');
try{
    update_option('ozeki_resilience_m1_config',array_merge($old,['setup_role'=>'recovery','protect'=>false]));
    $p=new OzekiResilience\M1\Plugin();ob_start();$p->page();$html=ob_get_clean();
    foreach(['whole_checkpoint','checkpoint','whole_initial','initial_snapshot','site_cleanup_execute','cleanup_execute','site_cleanup_preview','cleanup_preview'] as $operation)verify(!str_contains($html,'id="owr-action-'.$operation.'"'),'Recovery UI exposes '.$operation);
    verify(str_contains($html,'id="owr-action-whole_restore"'),'Recovery button missing');
    verify(str_contains($html,'Prepare the recovery destination'),'Requirements missing');
    $labLocaleFilter=static fn()=>'ja';add_filter('pre_determine_locale',$labLocaleFilter);
    verify(str_contains(OzekiResilience\M1\AdminText::message('Install the recorded dependency version before recovery: example/plugin.php 1.2'),'記録された版'),'Dependency translation');
    verify(str_contains(OzekiResilience\M1\AdminText::recoveryNext('Cannot create private staging directory.'),'サーバー管理者'),'Directory next action');
    ob_start();$p->page();$ja=ob_get_clean();
    verify(str_contains($ja,'復旧先に用意するもの'),'Japanese requirements missing');
    remove_filter('pre_determine_locale',$labLocaleFilter);
    $points=$p->store()->siteSnapshots();
    verify(count($points)>0,'Real S3 points unavailable');
    $before=$GLOBALS['wp_version'];$GLOBALS['wp_version']='0.0.1';
    ob_start();OzekiResilience\M1\RecoveryPreparation::render($points);$missing=ob_get_clean();$GLOBALS['wp_version']=$before;
    verify(str_contains($missing,'Use this release line'),'Wrong WordPress version not identified');
    echo json_encode(['passed'=>true,'s3_mutations_blocked_before_sdk'=>4,'recovery_ui_hides_write_controls'=>true,'requirements_en_ja'=>true,'missing_wordpress_next_action'=>true,'real_s3_points'=>count($points)]);
}finally{while(ob_get_level())ob_end_clean();update_option('ozeki_resilience_m1_config',$old);}
