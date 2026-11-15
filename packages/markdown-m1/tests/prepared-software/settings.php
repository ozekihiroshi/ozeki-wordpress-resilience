<?php
require '/var/www/html/wp-load.php';
if(!str_starts_with(home_url(),'http://owr-noinit-'))throw new RuntimeException('Not isolated');
wp_set_current_user(1);$mode=$argv[1];$side=getenv('TRIAL_SIDE');
function settingsNeed($v,$m){if(!$v)throw new RuntimeException($m);}
function settingsState(){return ['global'=>get_option('tablepress_plugin_options'),'mods'=>get_theme_mods(),'css'=>wp_get_custom_css(),'text'=>get_option('widget_text'),'image'=>get_option('widget_media_image'),'sidebars'=>get_option('sidebars_widgets')];}
if($mode==='prepare'){
 $options=json_decode(get_option('tablepress_plugin_options'),true);$options['custom_css']='.tablepress { color: #135790; }';$options['use_custom_css']=true;$options['use_custom_css_file']=false;$options['prepared_marker']=$side;update_option('tablepress_plugin_options',wp_json_encode($options));
 set_theme_mod('prepared_marker',$side);set_theme_mod('prepared_url','Keep https://source.invalid/path');set_theme_mod('background_color','ffffff');
 wp_update_custom_css_post('.prepared-'.$side.' { color: #123456; }');
 $id=wp_insert_post(['import_id'=>700,'post_type'=>'attachment','post_status'=>'inherit','post_title'=>'Prepared image','guid'=>home_url('/prepared.png')]);
 update_post_meta($id,'_wp_attached_file','prepared.png');
 // Only destination reference checks use this synthetic image; it is not a source original.
 if($side!=='source')set_theme_mod('custom_logo',$id);
 update_option('widget_text',[2=>['title'=>'Prepared '.$side,'text'=>'Prepared explanation '.$side,'filter'=>false], '_multiwidget'=>1]);
 update_option('widget_media_image',[3=>['attachment_id'=>$id,'url'=>home_url('/prepared.png')], '_multiwidget'=>1]);
 update_option('sidebars_widgets',['trial-sidebar'=>$side==='source'?['text-2']:['text-2','media_image-3'],'wp_inactive_widgets'=>[],'array_version'=>3]);
 if($side==='source'){delete_post_meta($id,'_wp_attached_file');wp_delete_post($id,true);}
 file_put_contents('/lab/'.$side.'-settings-prepared.json',wp_json_encode(settingsState()));echo '{}';exit;
}
if($mode==='seed'){
 set_theme_mod('background_color','123456');set_theme_mod('source_only','not imported');
 // Use the same numeric ID for unrelated content: it must not retain destination image references.
 wp_insert_post(['import_id'=>700,'post_type'=>'page','post_status'=>'publish','post_title'=>'Unrelated source page','guid'=>home_url('/unrelated')]);
 echo '{}';exit;
}
if($mode==='check'){
 $before=json_decode(file_get_contents('/lab/'.$side.'-settings-prepared.json'),true);$after=settingsState();
 settingsNeed($after['global']===$before['global'],'Prepared TablePress settings changed');
 settingsNeed($after['css']===$before['css']&&str_contains($after['css'],'.prepared-'.$side),'Prepared theme CSS content changed');
 foreach(['prepared_marker','prepared_url'] as $key)settingsNeed($after['mods'][$key]===$before['mods'][$key],'Prepared theme value changed: '.$key);
 settingsNeed($after['mods']['background_color']===($argv[2]??'123456'),'Source theme color missing');
 settingsNeed(!isset($after['mods']['custom_logo']),'Unrelated object reused as logo');
 settingsNeed(!isset($after['mods']['source_only']),'Unknown source theme setting applied');
 settingsNeed($after['text']===$before['text']&&$after['image']===$before['image'],'Widget configuration erased');
 settingsNeed($after['sidebars']['trial-sidebar']===['text-2'],'Prepared usable widget placement lost');
 settingsNeed(in_array('media_image-3',$after['sidebars']['wp_inactive_widgets'],true),'Ambiguous media widget not held');
 register_sidebar(['id'=>'trial-sidebar','name'=>'Trial']);ob_start();dynamic_sidebar('trial-sidebar');$html=ob_get_clean();
 settingsNeed(str_contains($html,$after['text'][2]['text']),'Prepared widget not usable');
 $result=get_option('ozeki_resilience_site_restore_result');settingsNeed(str_contains(wp_json_encode($result['application_report']),'widgets.media_image-3'),'Held placement not reported');
 echo wp_json_encode(['pass'=>true,'prepared'=>$after,'widget_rendered'=>true,'held_placement_reported'=>true]);exit;
}
if($mode==='edit'){
 set_theme_mod('background_color','654321');$options=get_option('widget_text');$options[2]['text']='Edited prepared explanation '.$side;update_option('widget_text',$options);
 $state=settingsState();file_put_contents('/lab/'.$side.'-settings-prepared.json',wp_json_encode($state));echo '{}';exit;
}
throw new RuntimeException('Unknown mode');
