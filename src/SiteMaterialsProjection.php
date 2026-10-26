<?php
declare(strict_types=1);
if (!defined('ABSPATH')) { exit; }

function owr_material_block(array $node,array $map):string {
    $html=preg_replace_callback('~(href|src)="asset:([a-z][a-z0-9_-]{0,79})"~',function($m)use($map){
        if(!isset($map[$m[2]]))throw new RuntimeException('Missing material');$id=$map[$m[2]];
        return $m[1].'="'.esc_url(get_post_type($id)==='attachment'?wp_get_attachment_url($id):home_url('/?p='.$id)).'"';
    },$node['html']);
    $name=substr($node['name'],5);$attrs=$node['attrs']??[];
    if($name==='heading'&&preg_match('/<h([1-6])/', $html,$match)){
        $attrs=['level'=>(int)$match[1]];$html=preg_replace('/<h([1-6])>/', '<h$1 class="wp-block-heading">',$html,1);
    }
    if($name==='image'&&preg_match('/<img[^>]*\bsrc="asset:([a-z][a-z0-9_-]*)"/', $node['html'],$match)){
        $size=$attrs['sizeSlug']??'full';$attrs=['id'=>$map[$match[1]],'sizeSlug'=>$size,'linkDestination'=>'none'];
        $html=str_replace('<figure>','<figure class="wp-block-image size-'.esc_attr($size).'">',$html);
        $html=preg_replace('~<img ([^>]*?)/?>~','<img $1 class="wp-image-'.$map[$match[1]].'"/>',$html);
    }
    if($name==='quote')$html=str_replace('<blockquote>','<blockquote class="wp-block-quote">',$html);
    if($name==='list'){
        if(str_starts_with($html,'<ol')){$attrs['ordered']=true;if(preg_match('/<ol start="([0-9]+)"/',$html,$match))$attrs['start']=(int)$match[1];}
        $html=preg_replace('/^<(ul|ol)([^>]*)>/', '<$1$2 class="wp-block-list">',$html,1);
    }
    // Canonicalize before writing: CLI KSES and an unfiltered editor must store identical bytes.
    return wp_kses_post(get_comment_delimited_block_content('core/'.$name,$attrs,$html));
}
function owr_material_body(array $row,array $map):string{
    $body='';foreach($row['nodes'] as $node){
        switch($node['type']){
            case 'block':$body.=owr_material_block($node,$map);break;
            case 'paragraph':$body.='<p>'.esc_html($node['text']).'</p>';break;
            case 'heading':$n=(int)$node['level'];$body.='<h'.$n.'>'.esc_html($node['text']).'</h'.$n.'>';break;
            case 'link':$target=$map[$node['target']];$body.='<p><a href="'.esc_url(home_url('/?p='.$target)).'">'.esc_html($node['text']).'</a></p>';break;
            case 'image':$target=$map[$node['target']];$body.='<figure><img src="'.esc_url(wp_get_attachment_url($target)).'" alt="'.esc_attr(get_post_meta($target,'_wp_attachment_image_alt',true)).'"></figure>';break;
            default:throw new RuntimeException('Unsupported node');
        }
    }return $body;
}

function owr_site_materials_apply(array $input,bool $incremental=false,bool $source=false):array {
if (PHP_SAPI!=='cli' && !current_user_can('manage_options')) {throw new RuntimeException('Recovery administrator required');}
if (($input['schema']??null)!=='owr-site-received-v1') { throw new RuntimeException('Verified received materials required'); }
$site=$input['site'];$fingerprint=hash('sha256',json_encode($input,JSON_THROW_ON_ERROR));
$previous=get_option('owr_site_projection');
if ($previous && $previous['fingerprint']!==$fingerprint && (!$incremental || ($input['parent']??null)!==($previous['receipt']??null))) { throw new RuntimeException('Fresh target or exact parent required'); }
global $wpdb;
if (!$previous && (int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ('post','page','attachment')")!==0) { throw new RuntimeException('Empty target required'); }
$map=$previous['map']??[];
if($source){foreach($site['entries'] as $row){if(!isset($map[$row['id']])&&preg_match('/^native-([0-9]+)$/',$row['id'],$match)){$p=get_post((int)$match[1]);if(!$p||$p->post_status!=='auto-draft'||$p->post_content!==''||$p->post_type!==$row['kind'])throw new RuntimeException('New editor shell changed');$map[$row['id']]=(int)$p->ID;}}}
// All DB projection changes are atomic; new content-addressed files may remain after rollback.
foreach ([$wpdb->posts,$wpdb->postmeta,$wpdb->options,$wpdb->term_relationships] as $table) { $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));if($engine!=='InnoDB'){throw new RuntimeException('Transactional tables required');}}
$wpdb->query('START TRANSACTION');
try {
register_shutdown_function(function()use($wpdb){$wpdb->query('ROLLBACK');});
$record=function(string $state)use(&$map,$fingerprint,$input){update_option('owr_site_projection',['fingerprint'=>$fingerprint,'map'=>$map,'receipt'=>$input['receipt'],'state'=>$state],false);};
$wanted=array_column($site['entries'],'id');
if($source){foreach($map as $asset=>$wpid)update_post_meta($wpid,'owr_material_id',$asset);}
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
        $new=wp_insert_attachment(wp_slash(['post_mime_type'=>$row['mime'],'post_title'=>$id,'post_status'=>'inherit','comment_status'=>'closed','ping_status'=>'closed','meta_input'=>['owr_material_id'=>$id]]),$path,0,true);
        if(is_wp_error($new)){throw new RuntimeException('Attachment failed');}
        update_post_meta($new,'_wp_attachment_image_alt',wp_slash($row['alt']));
        wp_update_attachment_metadata($new,['width'=>$image[0],'height'=>$image[1],'file'=>_wp_relative_upload_path($path),'filesize'=>strlen($raw),'sizes'=>[]]);
    }else{
        $new=wp_insert_post(wp_slash(['post_type'=>$row['kind'],'post_status'=>'draft','post_title'=>$row['title'],'post_name'=>$row['slug'],'meta_input'=>['owr_material_id'=>$id]]),true);
        if(is_wp_error($new)){throw new RuntimeException('Post shell failed');}
    }
    $map[$id]=(int)$new;$record('applying');
}
foreach($site['entries'] as $row){if($row['kind']==='image'){continue;}
    $current=get_post($map[$row['id']]);$status=$row['status']??'draft';
    if($current&&$current->post_title===$row['title']&&$current->post_name===$row['slug']&&$current->post_content===owr_material_body($row,$map)&&(int)$current->post_parent===($row['parent']===null?0:$map[$row['parent']])&&$current->post_status===$status&&$current->comment_status==='closed'&&$current->ping_status==='closed')continue;
    $result=wp_update_post(wp_slash(['ID'=>$map[$row['id']],'post_title'=>$row['title'],'post_name'=>$row['slug'],'post_content'=>owr_material_body($row,$map),'post_parent'=>$row['parent']===null?0:$map[$row['parent']],'post_status'=>($row['status']??'draft'),'comment_status'=>'closed','ping_status'=>'closed']),true);
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
        if($p->post_title!==$row['title'] || $p->post_name!==$row['slug'] || $p->post_content!==owr_material_body($row,$map) || (int)$p->post_parent!==($row['parent']===null?0:$map[$row['parent']]) || $p->post_status!==(($row['status']??'draft'))){throw new RuntimeException('Content comparison failed for '.$row['id']);}
    }$checks[]=$row['id'];
}
if((int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_type IN ('post','page','attachment') AND post_status<>'auto-draft'")!==count($map)){throw new RuntimeException('Unexpected target objects');}
$state=$source?'verified-source':'verified-reconstruction';$record($state);$wpdb->query('COMMIT');return ['state'=>$state,'verified_ids'=>$checks,'map'=>$map,'restored_statuses'=>array_column(array_filter($site['entries'],fn($row)=>$row['kind']!=='image'),'status','id'),'side_effect_attempts'=>(int)get_option('rbr_side_effect_attempts',0)];

} catch (\Throwable $e) {$wpdb->query('ROLLBACK');wp_cache_flush();throw $e;}

}
