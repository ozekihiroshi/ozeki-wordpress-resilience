<?php
if(!current_user_can('manage_options')){status_header(403);exit('Private reconstruction preview');}
$map=get_option('rbr_map');$id=isset($_GET['page_id'])?(int)$_GET['page_id']:($map[get_option('rbr_landing')]??0);
$post=get_post($id);if(!$post||$post->post_type!=='page'||$post->post_status!=='draft'){status_header(404);exit('Missing');}
header('Content-Type: text/html; charset=utf-8');
echo '<!doctype html><html><head><style>p {white-space:pre-wrap;}</style></head><body><nav id="global">';
foreach(get_option('rbr_navigation',[])as $n)echo '<a href="'.esc_url(home_url('/?page_id='.$map[$n['target_asset_id']])).'">'.esc_html($n['label']).'</a>';
echo '</nav><h1>'.esc_html($post->post_title).'</h1><main>'.$post->post_content.'</main></body></html>';
