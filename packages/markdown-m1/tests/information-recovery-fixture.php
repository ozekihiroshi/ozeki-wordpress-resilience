<?php
// Disposable WordPress only; requires separately installed CF7, Flamingo and TablePress.
wp_set_current_user(1);
function information_assert($value,$message){if(!$value)throw new RuntimeException($message);}
if(($args[0]??'')==='check'){
    $post=get_page_by_path('asset-fixture',OBJECT,'page');
    information_assert($post&&$post->post_content==='Preserved page <img src="'.wp_upload_dir()['baseurl'].'/asset.png">','Page missing');
    information_assert(get_post_meta($post->ID,'unknown_fixture',true)==='','Unknown metadata applied');
    information_assert(!get_page_by_path('unknown-executable',OBJECT,'unknown_code'),'Unknown executable post restored');
    $messages=get_posts(['post_type'=>'flamingo_inbound','post_status'=>'any','numberposts'=>-1]);
    information_assert(count($messages)>0,'Inquiry missing');
    $found=false;foreach($messages as $message)if(get_post_meta($message->ID,'_subject',true)==='Preserved inquiry')$found=true;
    information_assert($found,'Inquiry subject missing');
    $tables=TablePress::$model_table->_debug_get_tables();$found=false;
    foreach($tables['table_post'] as $id=>$pid){$table=TablePress::$model_table->load((string)$id,true,true);if(!is_wp_error($table)&&$table['data']===[['Preserved table']])$found=true;}
    information_assert($found,'Table data missing');
    information_assert(file_get_contents(wp_upload_dir()['basedir'].'/asset.png')===base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='),'Image bytes changed');
    echo "PASS page, image, inquiry, table and selective metadata recovery using preinstalled plugins.
";
    return;
}
wp_insert_post(['post_title'=>'Unknown executable','post_name'=>'unknown-executable','post_type'=>'unknown_code','post_content'=>'<?php echo 1;','post_status'=>'publish']);
$id=wp_insert_post(['post_title'=>'Asset fixture','post_name'=>'asset-fixture','post_type'=>'page','post_status'=>'publish','post_content'=>'Preserved page <img src="'.wp_upload_dir()['baseurl'].'/asset.png">']);
update_post_meta($id,'unknown_fixture','do not apply');
Flamingo_Inbound_Message::add(['posted_data_hash'=>hash('sha256','fixture'),'subject'=>'Preserved inquiry','from'=>'Generated <generated@example.invalid>','fields'=>['message'=>'Preserved inquiry body']]);
$table=TablePress::$model_table->get_table_template();$table['name']='Preserved table';$table['data']=[['Preserved table']];
information_assert(!is_wp_error(TablePress::$model_table->add($table)),'Cannot create table');
$path=wp_upload_dir()['basedir'].'/asset.png';
file_put_contents($path,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='));
$attachment=wp_insert_attachment(['post_title'=>'Preserved image','post_mime_type'=>'image/png','post_status'=>'inherit'],$path,$id);
update_attached_file($attachment,$path);
set_post_thumbnail($id,$attachment);
echo "Created information assets.
";
