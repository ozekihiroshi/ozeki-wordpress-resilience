<?php
define('ABSPATH', __DIR__ . '/');
require __DIR__.'/../src/SiteMaterialsProjection.php';
function wp_kses_post($html){return $html;}
function esc_url($s){return htmlspecialchars($s,ENT_QUOTES);}
function esc_attr($s){return htmlspecialchars($s,ENT_QUOTES);}
function get_post_type($id){return $id===2?'attachment':'page';}
function wp_get_attachment_url($id){return 'https://new.invalid/image-'.$id.'.png';}
function home_url($s){return 'https://new.invalid'.$s;}
function get_comment_delimited_block_content($name,$attrs,$html){return json_encode($attrs).$html;}
$body=owr_material_block(['name'=>'core/paragraph','html'=>'<p>literal asset:unknown <a href="asset:page">page</a></p>'],['page'=>1]);
if(!str_contains($body,'literal asset:unknown')||!str_contains($body,'href="https://new.invalid/?p=1"'))throw new RuntimeException('Only URL references must be replaced');
$body=owr_material_block(['name'=>'core/image','html'=>'<figure><img alt="asset:not-a-reference" src="asset:picture"></figure>'],['picture'=>2]);
if(!str_contains($body,'asset:not-a-reference')||!str_contains($body,'wp-image-2'))throw new RuntimeException('Image must use src reference');
echo "Native block rendering: 2 checks PASS\n";
