<?php
// Runs only in disposable WordPress before and after replacing the old ZIP.
$mode=$args[0]??'';
if($mode==='seed'){
    update_post_meta(1,'_owr_m1_asset','retained-asset');
    update_post_meta(1,'_owr_m1_origin_url','https://example.invalid/source');
    update_user_meta(1,'_owr_member_origin','retained-member');
    update_user_meta(1,'_owr_member_source','https://example.invalid');
    $c=get_option('owr_m1_config');$c['checkpoint_interval_days']=7;update_option('owr_m1_config',$c);
    $at=time()+7200;wp_clear_scheduled_hook('owr_m1_checkpoint');wp_schedule_single_event($at,'owr_m1_checkpoint');
    update_option('ozeki_resilience_test_expected_cron',$at,false);
    echo "PASS legacy migration fixtures seeded\n";return;
}
$assert=static function($ok,$message){if(!$ok)throw new RuntimeException($message);};
$assert(get_post_meta(1,'_ozeki_resilience_m1_asset',true)==='retained-asset','Asset mapping lost');
$assert(get_post_meta(1,'_ozeki_resilience_m1_origin_url',true)==='https://example.invalid/source','Origin mapping lost');
$assert(get_user_meta(1,'_ozeki_resilience_member_origin',true)==='retained-member','Member mapping lost');
$assert(get_user_meta(1,'_ozeki_resilience_member_source',true)==='https://example.invalid','Member source lost');
$assert(!metadata_exists('post',1,'_owr_m1_asset'),'Legacy post key remains active');
$assert(!get_option('owr_m1_config'),'Legacy setting not renamed');
$assert(wp_next_scheduled('ozeki_resilience_m1_checkpoint')==get_option('ozeki_resilience_test_expected_cron'),'Checkpoint time changed');
$assert(!wp_next_scheduled('owr_m1_checkpoint'),'Duplicate legacy Checkpoint');
$assert(!has_action('owr_m1_checkpoint')&&!has_action('admin_post_owr_m1'),'Legacy hook still registered');
$before=get_option('ozeki_resilience_m1_pending');
\OzekiResilience\M1\Identifiers::migrate();
$assert(get_option('ozeki_resilience_m1_pending')===$before,'Repeated migration changed pending data');
echo "PASS option, post/member metadata and single Checkpoint migration; idempotent repeat; no legacy hooks\n";

// A failed partial run must remain retryable and must not overwrite already-current values.
update_option('owr_m1_notice','legacy notice');
update_option('ozeki_resilience_m1_notice','current notice');
delete_option('ozeki_resilience_identifiers_v1');
global $wpdb;$table=$wpdb->postmeta;$quiet=$wpdb->suppress_errors(true);
try {
    $wpdb->postmeta=$wpdb->prefix.'nonexistent_migration_fixture';
    try {\OzekiResilience\M1\Identifiers::migrate();throw new LogicException('Failure was not detected');}
    catch(RuntimeException $e){$assert(!get_option('ozeki_resilience_identifiers_v1'),'Failed migration marked complete');}
} finally {$wpdb->postmeta=$table;$wpdb->suppress_errors($quiet);}
\OzekiResilience\M1\Identifiers::migrate();
$assert(get_option('ozeki_resilience_identifiers_v1')==1,'Retry did not finish');
$assert(get_option('ozeki_resilience_m1_notice')==='current notice','Current value was overwritten');
$assert(get_option('owr_m1_notice')==='legacy notice','Conflicting legacy value was destroyed');
$assert(get_option('ozeki_resilience_m1_pending')===$before,'Failure/retry changed pending data');
delete_option('owr_m1_notice');delete_option('ozeki_resilience_m1_notice');
echo "PASS partial migration failure/retry, existing-current value precedence and queue preservation\n";
