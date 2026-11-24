<?php
// Run with wp eval-file in the disposable WordPress candidate.
require_once WP_PLUGIN_DIR.'/ozeki-resilience/src/RecoveryContent.php';
use OzekiResilience\M1\RecoveryContent;
function editor_check($v,$message){if(!$v)throw new RuntimeException($message);}
$raw='<!-- wp:heading --><h2 class="wp-block-heading">Heading</h2><!-- /wp:heading -->' . "\n" . '<!-- wp:paragraph --><p>[review_probe]</p><!-- /wp:paragraph -->';
$notes=[];$safe=RecoveryContent::html($raw,'editor',$notes);
editor_check(array_values(array_filter(array_column(parse_blocks($safe),'blockName')))===['core/heading','core/paragraph'],'Static block editing structure lost');
// Match an editor converting character references back to visible characters.
$edited=html_entity_decode($safe,ENT_QUOTES|ENT_HTML5,'UTF-8');
$id=wp_insert_post(['post_type'=>'page','post_status'=>'draft','post_title'=>'Editor contract','post_content'=>$edited]);
update_post_meta($id,'_ozeki_resilience_m1_origin_url','https://source.invalid/?p=1');
add_shortcode('review_probe',fn()=>'<strong>PROBE_EXECUTED</strong>');
global $post;$savedPost=$post;$post=get_post($id);setup_postdata($post);
$rendered=apply_filters('the_content',$post->post_content);
editor_check(!str_contains($rendered,'PROBE_EXECUTED')&&str_contains($rendered,'review_probe'),'Recovered shortcode reactivated after editing');
delete_post_meta($id,'_ozeki_resilience_m1_origin_url');
editor_check(str_contains(apply_filters('the_content',$post->post_content),'PROBE_EXECUTED'),'Unrelated new article was restricted');
$post=$savedPost;wp_reset_postdata();wp_delete_post($id,true);
echo "Recovered editor normalization guarded; unrelated content unchanged; static blocks retained PASS\n";
