<?php
declare(strict_types=1);
// Dedicated-lab entry. The host runner verifies E, isolation and P before WP bootstrap.
if (PHP_SAPI !== 'cli' || getenv('OWR_RBR_DISPOSABLE') !== '1') { throw new RuntimeException('Dedicated CLI target required'); }
require '/var/www/html/wp-load.php';
require '/kit/src/RbrGenerationCoordinator.php';
require '/kit/src/RbrReconstructionPlanner.php';
require '/kit/tools/rbr-planner-build.php';
function rbr_checked($value) { if(is_wp_error($value)) throw new RuntimeException($value->get_error_message()); return $value; }
$read=static function(array $ref):string { $p='/bundle/cache/'.$ref['sha256'].'.blob'; if(!is_file($p)||is_link($p))throw new RuntimeException('Missing object'); return file_get_contents($p); };
$d=file_get_contents('/bundle/definition.json');
$p=(new Owr\RbrReconstructionPlanner($read,hash('sha256',rbrPlannerBuildBytes())))->plan($d);
if(Owr\RbrGenerationCoordinator::encode($p)!==file_get_contents('/bundle/plan.json') || $p['environment_mode']!=='pinned-runtime')throw new RuntimeException('Plan mismatch');
if(!defined('DISABLE_WP_CRON') || !DISABLE_WP_CRON || !defined('WP_HTTP_BLOCK_EXTERNAL') || !WP_HTTP_BLOCK_EXTERNAL)throw new RuntimeException('Containment missing');
global $wpdb;
if((int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts}")!==0 || get_option('rbr_run_state'))throw new RuntimeException('Require fresh empty target; interrupted runs are not retried');
add_option('rbr_run_state','started','','no');
try {
$map=[];$roles=[];
foreach($p['steps'] as $step){
 switch($step['operation']){
 case 'register_image':
  $raw=$read($step['source']);if(hash('sha256',$raw)!==$step['sha256'])throw new RuntimeException('Media mismatch');
  $up=wp_upload_dir();if($up['error'])throw new RuntimeException($up['error']);
  $path=$up['path'].'/'.$step['asset_id'].($step['mime']==='image/png'?'.png':'.jpg');
  $fp=fopen($path,'xb');if(!$fp)throw new RuntimeException('Existing media');if(fwrite($fp,$raw)!==strlen($raw))throw new RuntimeException('Media write');fclose($fp);
  $id=rbr_checked(wp_insert_attachment(['post_title'=>$step['asset_id'],'post_status'=>'inherit','post_mime_type'=>$step['mime'],'post_excerpt'=>''],$path,0,true));
  update_attached_file($id,$path);update_post_meta($id,'_wp_attachment_image_alt','');
  update_post_meta($id,'rbr_asset_id',$step['asset_id']);$map[$step['asset_id']]=$id;break;
 case 'create_page_shell':
  $id=rbr_checked(wp_insert_post(['post_type'=>'page','post_title'=>wp_slash($step['title']),'post_name'=>$step['slug'],'post_status'=>'draft','post_parent'=>0],true));
  update_post_meta($id,'rbr_asset_id',$step['asset_id']);update_post_meta($id,'rbr_role',$step['role']);$roles[$step['role']]=$step['asset_id'];$map[$step['asset_id']]=$id;break;
 case 'populate_page':
  $html='';foreach($step['body'] as $node){
   if($node['type']==='paragraph')$html.='<p>'.esc_html($node['text']).'</p>';
   elseif($node['type']==='image')$html.='<img src="'.esc_url(wp_get_attachment_url($map[$node['target_asset_id']])).'" alt="">';
   else $html.='<a href="'.esc_url(home_url('/?page_id='.$map[$node['target_asset_id']])).'">'.esc_html($node['label']).'</a>';
  }
  $html.='<nav class="related">';foreach($step['related_navigation'] as $node)$html.='<a href="'.esc_url(home_url('/?page_id='.$map[$node['target_asset_id']])).'">'.esc_html($node['label']).'</a>';
  $html.='</nav>';rbr_checked(wp_update_post(['ID'=>$map[$step['asset_id']],'post_content'=>wp_slash($html)],true));break;
 case 'configure_preview': update_option('rbr_navigation',$step['navigation']);update_option('rbr_landing',$step['landing_asset_id']);break;
 case 'verify_scope': break;
 default: throw new RuntimeException('Unsupported operation');
 }
}
update_option('rbr_map',$map);update_option('rbr_roles',$roles);update_option('rbr_plan_sha256',hash('sha256',file_get_contents('/bundle/plan.json')));update_option('rbr_run_state','applied');
echo json_encode(['state'=>'applied-private','map'=>$map,'public_activation'=>false],JSON_THROW_ON_ERROR);
} catch(Throwable $e){update_option('rbr_run_state','failed-discard-target');throw $e;}
