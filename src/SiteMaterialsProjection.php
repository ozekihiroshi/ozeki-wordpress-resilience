<?php
declare(strict_types=1);
function owr_material_body(array $row,array $map):string{
    $body='';foreach($row['nodes'] as $node){
        switch($node['type']){
            case 'paragraph':$body.='<p>'.esc_html($node['text']).'</p>';break;
            case 'heading':$n=(int)$node['level'];$body.='<h'.$n.'>'.esc_html($node['text']).'</h'.$n.'>';break;
            case 'link':$target=$map[$node['target']];$body.='<p><a href="'.esc_url(home_url('/?p='.$target)).'">'.esc_html($node['text']).'</a></p>';break;
            case 'image':$target=$map[$node['target']];$body.='<figure><img src="'.esc_url(wp_get_attachment_url($target)).'" alt="'.esc_attr(get_post_meta($target,'_wp_attachment_image_alt',true)).'"></figure>';break;
            default:throw new RuntimeException('Unsupported node');
        }
    }return $body;
}

function owr_site_materials_apply(array $input,bool $incremental=false):array {
if (getenv('OWR_RBR_DISPOSABLE')!=='1' || !defined('DISABLE_WP_CRON') || !DISABLE_WP_CRON || !defined('WP_HTTP_BLOCK_EXTERNAL') || !WP_HTTP_BLOCK_EXTERNAL) {throw new RuntimeException('Dedicated guarded environment required');}
if (($input['schema']??null)!=='owr-site-received-v1') { throw new RuntimeException('Verified received materials required'); }
$site=$input['site'];$fingerprint=hash('sha256',json_encode($input,JSON_THROW_ON_ERROR));
$previous=get_option('owr_site_projection');
if ($previous && $previous['fingerprint']!==$fingerprint && (!$incremental || ($input['parent']??null)!==($previous['receipt']??null))) { throw new RuntimeException('Fresh target or exact parent required'); }
global $wpdb;
if (!$previous && (int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ('post','page','attachment')")!==0) { throw new RuntimeException('Empty target required'); }
$map=$previous['map']??[];
// All DB projection changes are atomic; new content-addressed files may remain after rollback.
foreach ([$wpdb->posts,$wpdb->postmeta,$wpdb->options,$wpdb->term_relationships] as $table) { $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));if($engine!=='InnoDB'){throw new RuntimeException('Transactional tables required');}}
$wpdb->query('START TRANSACTION');
try {
register_shutdown_function(function()use($wpdb){$wpdb->query('ROLLBACK');});
$record=function(string $state)use(&$map,$fingerprint,$input){update_option('owr_site_projection',['fingerprint'=>$fingerprint,'map'=>$map,'receipt'=>$input['receipt'],'state'=>$state],false);};
$wanted=array_column($site['entries'],'id');
foreach($map as $id=>$wpid){if(!in_array($id,$wanted,true)){
    // Retain files; only remove this projection's DB objects. No filesystem deletion.
    $wpdb->delete($wpdb->term_relationships,['object_id'=>$wpid]);$wpdb->delete($wpdb->postmeta,['post_id'=>$wpid]);$wpdb->delete($wpdb->posts,['ID'=>$wpid]);unset($map[$id]);
}}
$record('applying');
require_once ABSPATH.'wp-admin/includes/image.php';
foreach($site['entries'] as $row){
    $id=$row['id'];if(isset($map[$id])){
        if($row['kind']!=='image'){continue;}
        $raw=base64_decode($row['data'],true);$old=get_attached_file($map[$id]);
        if(is_file($old) && hash_file('sha256',$old)===hash('sha256',$raw)){update_post_meta($map[$id],'_wp_attachment_image_alt',wp_slash($row['alt']));continue;}
        $wpdb->delete($wpdb->postmeta,['post_id'=>$map[$id]]);$wpdb->delete($wpdb->posts,['ID'=>$map[$id]]);unset($map[$id]);
    }
    // Stable metadata permits restart after insertion but before the map was persisted.
    $found=get_posts(['post_type'=>'any','post_status'=>'any','meta_key'=>'owr_material_id','meta_value'=>$id,'fields'=>'ids','numberposts'=>2]);
    if(count($found)>1){throw new RuntimeException('Duplicate material');}
    if($found){$map[$id]=(int)$found[0];$record('applying');continue;}
    if($row['kind']==='image'){
        $raw=base64_decode($row['data'],true);$image=getimagesizefromstring($raw);
        if(!$image || $image['mime']!==$row['mime'] || $image[0]>10000 || $image[1]>10000){throw new RuntimeException('Invalid image');}
        $upload=wp_upload_dir();$ext=$row['mime']==='image/png'?'png':'jpg';$name=hash('sha256',$raw).'.'.$ext;$path=$upload['path'].'/'.$name;
        if(is_file($path) && hash_file('sha256',$path)!==hash('sha256',$raw)){throw new RuntimeException('Image collision');}
        if(!is_file($path) && file_put_contents($path,$raw)!==strlen($raw)){throw new RuntimeException('Image write failed');}
        $new=wp_insert_attachment(wp_slash(['post_mime_type'=>$row['mime'],'post_title'=>$id,'post_status'=>'inherit','meta_input'=>['owr_material_id'=>$id]]),$path,0,true);
        if(is_wp_error($new)){throw new RuntimeException('Attachment failed');}
        update_post_meta($new,'_wp_attachment_image_alt',wp_slash($row['alt']));
    }else{
        $new=wp_insert_post(wp_slash(['post_type'=>$row['kind'],'post_status'=>'draft','post_title'=>$row['title'],'post_name'=>$row['slug'],'meta_input'=>['owr_material_id'=>$id]]),true);
        if(is_wp_error($new)){throw new RuntimeException('Post shell failed');}
    }
    $map[$id]=(int)$new;$record('applying');
}
foreach($site['entries'] as $row){if($row['kind']==='image'){continue;}
    $result=wp_update_post(wp_slash(['ID'=>$map[$row['id']],'post_title'=>$row['title'],'post_name'=>$row['slug'],'post_content'=>owr_material_body($row,$map),'post_parent'=>$row['parent']===null?0:$map[$row['parent']],'post_status'=>'draft']),true);
    if(is_wp_error($result)){throw new RuntimeException('Post content failed');}
}
update_option('blogname',$site['title']);update_option('show_on_front','page');update_option('page_on_front',$map[$site['landing']]);
// Compare actual DB fields and image bytes to the request-derived expectation, not to a copied result.
$checks=[];
foreach($input['expected']['entries'] as $row){
    $p=get_post($map[$row['id']]);if(!$p || $p->post_type!==($row['kind']==='image'?'attachment':$row['kind'])){throw new RuntimeException('Missing/wrong type');}
    if($row['kind']==='image'){
        if(hash_file('sha256',get_attached_file($p->ID))!==$row['sha256'] || get_post_meta($p->ID,'_wp_attachment_image_alt',true)!==$row['alt']){throw new RuntimeException('Image comparison failed');}
    }else{
        if($p->post_title!==$row['title'] || $p->post_name!==$row['slug'] || $p->post_content!==owr_material_body($row,$map) || (int)$p->post_parent!==($row['parent']===null?0:$map[$row['parent']]) || $p->post_status!=='draft'){throw new RuntimeException('Content comparison failed');}
    }$checks[]=$row['id'];
}
if((int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ('post','page','attachment')")!==count($map)){throw new RuntimeException('Unexpected target objects');}
$record('verified-private');$wpdb->query('COMMIT');return ['state'=>'verified-private','verified_ids'=>$checks,'map'=>$map,'public_activation'=>false,'side_effect_attempts'=>(int)get_option('rbr_side_effect_attempts',0)];

} catch (\Throwable $e) {$wpdb->query('ROLLBACK');wp_cache_flush();throw $e;}

}
