<?php
// Isolated fixture bridge: the SAME ordinary APIs on source and replay targets.
wp_set_current_user(1);
$p=json_decode(file_get_contents('/tmp/normal-operation.json'),true,512,JSON_THROW_ON_ERROR);
switch($p['operation']) {
 case 'media':
  require_once ABSPATH.'wp-admin/includes/file.php';
  require_once ABSPATH.'wp-admin/includes/media.php';
  require_once ABSPATH.'wp-admin/includes/image.php';
  file_put_contents('/tmp/normal-image.png',base64_decode($p['input']['base64'],true));
  $id=media_handle_sideload(['name'=>$p['input']['filename'],'tmp_name'=>'/tmp/normal-image.png'],0,$p['input']['title']);
  if(is_wp_error($id))throw new RuntimeException($id->get_error_message());
  $out=['id'=>$id,'url'=>wp_get_attachment_url($id)];break;
 case 'menu':
  $id=wp_create_nav_menu($p['input']['name']);
  if(is_wp_error($id))throw new RuntimeException($id->get_error_message());
  $out=['id'=>$id];break;
 case 'menu-item':
  $id=wp_update_nav_menu_item($p['input']['menu'],0,$p['input']['item']);
  if(is_wp_error($id))throw new RuntimeException($id->get_error_message());
  $out=['id'=>$id];break;
 case 'acf-definition':
  $g=acf_import_field_group($p['input']);
  if(!$g || empty($g['ID']))throw new RuntimeException('Normal ACF import failed');
  $out=['id'=>$g['ID'],'key'=>$g['key']];break;
 default:throw new RuntimeException('Unknown ordinary operation');
}
echo wp_json_encode($out);
