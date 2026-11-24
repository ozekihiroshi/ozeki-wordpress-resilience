<?php
// Disposable WordPress. Local transport by default; /lab/live enables a scoped
// host broker. Credentials never enter WordPress. Never run on a production DB.
$_SERVER['REMOTE_ADDR']='127.0.0.1';require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SiteSnapshot,SetupReadiness,RecoveryContent};
if(!str_contains(home_url(),'isolated-review'))throw new RuntimeException('Not an isolated review site');
wp_set_current_user(1);
function review_config($prefix,$role){
    $scope=is_file('/lab/live')?json_decode(file_get_contents('/lab/aws.json'),true):['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>''];
    update_option('ozeki_resilience_m1_config',['bucket'=>$scope['bucket'],'region'=>$scope['region'],'owner'=>$scope['owner']??'','prefix'=>$scope['prefix'].$prefix.'/','protect'=>false,'setup_role'=>$role,'setup_version'=>1,'terms_version'=>SetupReadiness::TERMS,'gfs'=>[],'cleanup_enabled'=>false],false);
}
function review_assert($v,$why){if(!$v)throw new RuntimeException($why);}
function review_clean_destination_users(){require_once ABSPATH.'wp-admin/includes/user.php';foreach(get_users() as $u)if(!user_can($u,'manage_options'))wp_delete_user($u->ID,1);}
function review_fp(){
    if(is_file('/lab/live')){
        $id=bin2hex(random_bytes(12));$base='/lab/ipc/'.$id;
        file_put_contents($base.'.tmp',json_encode(['operation'=>'FixtureFingerprint','args'=>[]]));rename($base.'.tmp',$base.'.request');
        $end=microtime(true)+180;while(!is_file($base.'.response')&&microtime(true)<$end)usleep(100000);
        $r=json_decode(file_get_contents($base.'.response'),true);if(empty($r['success']))throw new RuntimeException('Fixture fingerprint failed');return $r['result'];
    }
    $a=[];if(is_dir('/lab/objects'))foreach(new RecursiveIteratorIterator(new RecursiveDirectoryIterator('/lab/objects',FilesystemIterator::SKIP_DOTS)) as $f)$a[$f->getPathname()]=hash_file('sha256',$f->getPathname());ksort($a);return $a;
}
$run=bin2hex(random_bytes(6));review_config('first-'.$run,'source');
update_option('home','http://isolated-review-source-'.$run.'.invalid');update_option('siteurl','http://isolated-review-source-'.$run.'.invalid');
review_clean_destination_users();
require '/lab/tests/review-integrations.php';$integrations=review_integrations_seed();
$body='<h2>技術資料</h2><p>24 V</p><table><tr><td>PLC</td></tr></table><pre><code>&lt;script&gt;example&lt;/script&gt;</code></pre><img src="https://example.invalid/x" onerror="alert(1)"><script>window.reviewExecuted=1</script>';
$body.='<!-- wp:paragraph --><p>[review_probe] editable example</p><!-- /wp:paragraph -->';
$id=wp_insert_post(['post_type'=>'page','post_title'=>'Roundtrip','post_name'=>'review-roundtrip','post_status'=>'publish','post_content'=>'seed']);
global $wpdb;$wpdb->update($wpdb->posts,['post_content'=>$body],['ID'=>$id]);clean_post_cache($id);
$md="# 技術資料\n\n```html\n<script>alert(1)</script>\n```\n\n<script>alert(2)</script>\n\n[bad](javascript:alert(3))\n\n[review_attack]\n";
$doc=wp_insert_post(['post_type'=>'ozmd_document','post_title'=>'Markdown','post_status'=>'publish']);(new OzekiMarkdownDocuments\Content\MarkdownSource())->store($doc,$md);
$s=new SiteSnapshot((new Plugin())->store());$ref=$s->capture(true,[]);$before=review_fp();
update_option('home','http://isolated-review-target.invalid');update_option('siteurl','http://isolated-review-target.invalid');review_config('first-'.$run,'recovery');
update_option('upload_path','wp-content/uploads-target-'.$run);wp_upload_dir(null,true,true);
if(!is_dir('/lab/work'))mkdir('/lab/work',0700);
review_clean_destination_users();
$r=(new SiteSnapshot((new Plugin())->store()))->restore($ref['manifest'],true,'/lab/work');
file_put_contents('/lab/review-application-report.json',json_encode($r['application_report'],JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
review_integrations_check($integrations);
review_assert($before===review_fp(),'Recovery changed archived originals');
$restored=get_post($id)->post_content;review_assert(!str_contains($restored,'<script')&&!str_contains($restored,'onerror')&&str_contains($restored,'PLC'),'Unsafe or missing useful article');
review_assert(get_post_meta($doc,'_ozmd_source',true)===$md,'Markdown original changed');
$html=(new OzekiMarkdownDocuments\Rendering\MarkdownRenderer())->render($md);$notes=[];$html=RecoveryContent::html($html,'markdown',$notes);add_shortcode('review_attack',fn()=>'<script>window.reviewExecuted=9</script>');review_assert(!str_contains(do_shortcode($html),'<script>'),'Rendered Markdown executes');
review_assert(glob('/lab/work/owr-recovery-*')===[],'Successful recovery left private files');
// Normal use/edit, a new independent preservation, then a second recovery.
$edited=html_entity_decode($restored,ENT_QUOTES|ENT_HTML5,'UTF-8').'<p>追記</p>';
wp_update_post(['ID'=>$id,'post_content'=>$edited]);
function review_editor_render($id){
    global $post;$saved=$post;$post=get_post($id);setup_postdata($post);
    add_shortcode('review_probe',fn()=>'<strong>PROBE_EXECUTED</strong>');
    $html=apply_filters('the_content',$post->post_content);
    review_assert(!str_contains($html,'PROBE_EXECUTED')&&str_contains($html,'review_probe'),'Editor-normalized shortcode executed');
    review_assert((bool)get_post_meta($id,'_ozeki_resilience_m1_origin_url',true),'Recovered article marker missing');
    review_assert(in_array('core/paragraph',array_column(parse_blocks($post->post_content),'blockName'),true),'Static editor structure missing');
    $post=$saved;wp_reset_postdata();
}
review_editor_render($id);
review_config('second-'.$run,'source');$ref2=(new SiteSnapshot((new Plugin())->store()))->capture(true,[]);$before2=review_fp();
update_option('home','http://isolated-review-third.invalid');update_option('siteurl','http://isolated-review-third.invalid');review_config('second-'.$run,'recovery');
update_option('upload_path','wp-content/uploads-third-'.$run);wp_upload_dir(null,true,true);
review_clean_destination_users();
(new SiteSnapshot((new Plugin())->store()))->restore($ref2['manifest'],true,'/lab/work');
review_integrations_check($integrations);
review_assert($before2===review_fp(),'Second recovery changed originals');
$expectedNotes=[];$expected=RecoveryContent::html($edited,'expected',$expectedNotes);
review_assert(get_post($id)->post_content===$expected,'Useful text changed in second recovery');
review_editor_render($id);
review_assert(get_post_meta($doc,'_ozmd_source',true)===$md,'Unedited Markdown changed in second recovery');
review_assert(glob('/lab/work/owr-recovery-*')===[],'Second recovery left private files');
file_put_contents('/lab/review-fixture-ids.json',json_encode(['article'=>$id,'markdown'=>$doc,'integrations'=>$integrations,'manifest'=>$ref2['manifest']]));
echo json_encode(['safe_article'=>true,'markdown_original_unchanged'=>true,'use_edit_recapture_recover'=>true,'source_objects_unchanged'=>true,'workspace_empty'=>true,'not_applied'=>count($r['application_report']['not_applied']),'storage'=>is_file('/lab/live')?'real S3 scoped host broker':'network-isolated local SDK transport'],JSON_PRETTY_PRINT).PHP_EOL;
