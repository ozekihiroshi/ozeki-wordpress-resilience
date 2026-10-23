<?php
// Generated-data lifecycle harness only; never installed in a production plugin.
function owr_lab_install(string $zip):void {
    require_once ABSPATH.'wp-admin/includes/file.php';require_once ABSPATH.'wp-admin/includes/plugin.php';require_once ABSPATH.'wp-admin/includes/class-wp-upgrader.php';
    ob_start();try{$u=new Plugin_Upgrader(new Automatic_Upgrader_Skin());$result=$u->install($zip,['overwrite_package'=>true]);}finally{ob_end_clean();}
    if(is_wp_error($result)||!$result)throw new RuntimeException('ZIP installation failed: '.(is_wp_error($result)?$result->get_error_code():implode(',', $u->skin->get_errors()->get_error_codes())));
    $result=activate_plugin('ozeki-wordpress-resilience/ozeki-wordpress-resilience.php');if(is_wp_error($result))throw new RuntimeException('Activation failed');
}
function owr_lab_snapshot():array {
    global $wpdb;$options=[];foreach(['owr_notification_settings_v1','owr_legacy_history_fixture','owr_site_editor','owr_site_projection','cron']as $key)$options[$key]=get_option($key);
    $files=[];foreach(['requests','reports']as $dir){foreach(glob('/bundle/bridge/'.$dir.'/*.json')as $p)$files[$p]=hash_file('sha256',$p);}ksort($files);
    return ['options'=>$options,'posts'=>$wpdb->get_results("SELECT * FROM {$wpdb->posts} ORDER BY ID",ARRAY_A),'meta'=>$wpdb->get_results("SELECT * FROM {$wpdb->postmeta} ORDER BY meta_id",ARRAY_A),'bridge'=>$files];
}
function owr_lab_routes():void {
    add_action('rest_api_init',function(){register_rest_route('owr-test/v1','/upgrade',['methods'=>'POST','permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function(){
        $before=owr_lab_snapshot();owr_lab_install('/bundle/plugin.zip');$equal=$before===owr_lab_snapshot();if(!$equal)return new WP_Error('changed','Lifecycle changed',['status'=>500]);
        file_put_contents('/bundle/lifecycle-pending.json',json_encode(['state'=>'PASS','pending_requests_reports_history_settings_preserved'=>true]));return ['state'=>'PASS'];
    }]);});
}
