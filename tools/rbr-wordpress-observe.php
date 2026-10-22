<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'||getenv('OWR_RBR_DISPOSABLE')!=='1')throw new RuntimeException('Dedicated CLI target required');
require '/var/www/html/wp-load.php';
global $wpdb;
$rows=[];
foreach($wpdb->get_results("SELECT * FROM {$wpdb->posts} ORDER BY ID") as $post){
 $item=['id'=>(int)$post->ID,'asset_id'=>get_post_meta($post->ID,'rbr_asset_id',true),'role'=>get_post_meta($post->ID,'rbr_role',true),
 'type'=>$post->post_type,'status'=>$post->post_status,'parent'=>(int)$post->post_parent,'title'=>$post->post_title,'slug'=>$post->post_name,'body'=>$post->post_content,'caption'=>$post->post_excerpt];
 if($post->post_type==='attachment'){$path=get_attached_file($post->ID);$info=getimagesize($path);$item+=['sha256'=>hash_file('sha256',$path),'width'=>$info[0],'height'=>$info[1],'mime'=>$info['mime'],'url'=>wp_get_attachment_url($post->ID),'alt'=>get_post_meta($post->ID,'_wp_attachment_image_alt',true)];}
 $rows[]=$item;
}
echo json_encode(['rows'=>$rows,'map'=>get_option('rbr_map'),'roles'=>get_option('rbr_roles'),'landing'=>get_option('rbr_landing'),'navigation'=>get_option('rbr_navigation'),
 'run_state'=>get_option('rbr_run_state'),'active_plugins'=>get_option('active_plugins'),'side_effect_attempts'=>(int)get_option('rbr_side_effect_attempts',0),
 'bootstrap_blocked_attempts'=>(int)get_option('rbr_bootstrap_attempts',0),'cron_disabled'=>DISABLE_WP_CRON,'attempt_trace'=>get_option('rbr_attempt_trace',[]),'runtime'=>['wordpress'=>$wp_version,'php'=>PHP_VERSION,'database'=>$wpdb->get_var('SELECT VERSION()'),'theme'=>get_stylesheet(),'locale'=>get_locale(),'timezone'=>get_option('timezone_string'),'charset'=>$wpdb->charset,'collation'=>DB_COLLATE]],JSON_THROW_ON_ERROR|JSON_UNESCAPED_SLASHES);
