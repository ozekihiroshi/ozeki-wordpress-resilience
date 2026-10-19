<?php
// Test callbacks, not the barrier. Real WordPress cron/admin-ajax dispatch these.
add_filter('use_block_editor_for_post', '__return_false');
add_action('owr_route_tick', function () {
    file_put_contents('/tmp/owr-route-cron-active', '1');
    usleep(3000000);
    $id=wp_insert_post(['post_title'=>'Cron route', 'post_status'=>'publish']);
    update_option('owr_route_cron_count', (int)get_option('owr_route_cron_count',0)+1);
    @unlink('/tmp/owr-route-cron-active');
});
add_action('wp_ajax_owr_shutdown_probe', function () {
    if (!current_user_can('manage_options')) { wp_die('forbidden',403); }
    check_ajax_referer('owr_shutdown');
    register_shutdown_function(function () {
        file_put_contents('/tmp/owr-route-shutdown-active', '1');
        usleep(3000000);
        update_option('owr_route_shutdown_done', 'yes');
        @unlink('/tmp/owr-route-shutdown-active');
    });
    wp_die('scheduled');
});
