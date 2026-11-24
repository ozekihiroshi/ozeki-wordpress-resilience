<?php
$_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,SetupReadiness};
if(is_file('/lab/live')||!is_dir('/lab/objects'))throw new RuntimeException('Isolated local fixture required');
wp_set_current_user(1);$run=bin2hex(random_bytes(6));
$c=['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>'editor-'.$run.'/','protect'=>false,'setup_role'=>'source','setup_version'=>1,'terms_version'=>SetupReadiness::TERMS,'gfs'=>[],'cleanup_enabled'=>false];
update_option('ozeki_resilience_m1_config',$c,false);
update_option('home','http://isolated-editor-'.$run.'.invalid');update_option('siteurl','http://isolated-editor-'.$run.'.invalid');
$html='<!-- wp:heading --><h2 class="wp-block-heading">Editable recovery</h2><!-- /wp:heading -->' . "\n" .
'<!-- wp:paragraph --><p>Visible [review_probe] example.</p><!-- /wp:paragraph -->' . "\n" .
'<!-- wp:code --><pre class="wp-block-code"><code>[review_probe] code example.</code></pre><!-- /wp:code -->';
$id=wp_insert_post(['post_type'=>'page','post_status'=>'publish','post_title'=>'Editor recovery check','post_content'=>'seed']);
global $wpdb;$wpdb->update($wpdb->posts,['post_content'=>$html],['ID'=>$id]);clean_post_cache($id);
$ref=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);
$c['setup_role']='recovery';update_option('ozeki_resilience_m1_config',$c,false);
update_option('home','http://127.0.0.1:18784');update_option('siteurl','http://127.0.0.1:18784');
require_once ABSPATH.'wp-admin/includes/user.php';foreach(get_users() as $u)if(!user_can($u,'manage_options'))wp_delete_user($u->ID,1);
$r=(new SiteSnapshot((new Plugin())->store()))->restore($ref['manifest'],true,'/lab/work');
$out=['id'=>$id,'source'=>$html,'manifest'=>$ref['manifest'],'source_sha256'=>hash('sha256',$html),'applied'=>get_post($id)->post_content];
file_put_contents('/lab/editor-fixture.json',json_encode($out,JSON_PRETTY_PRINT));echo json_encode($out);
