<?php
// Only the disposable /lab fixture. Creates new synthetic local history.
require '/var/www/html/wp-load.php';
use OzekiResilience\M1\{Plugin,SetupReadiness};
if(!str_contains(home_url(),'127.0.0.1:18784'))throw new RuntimeException('Not isolated browser fixture');
if(is_file('/lab/live'))throw new RuntimeException('This fixture requires local transport');
wp_set_current_user(1);
$c=['bucket'=>'isolated','region'=>'ap-northeast-1','prefix'=>'individual-'.bin2hex(random_bytes(8)).'/','protect'=>false,'setup_role'=>'source','setup_version'=>1,'terms_version'=>SetupReadiness::TERMS,'gfs'=>[],'cleanup_enabled'=>false];
update_option('ozeki_resilience_m1_config',$c,false);$store=(new Plugin())->store();
$expected=[];
foreach(['page'=>'<h2>Individual article</h2><p>24 V</p><script>window.individualUnsafe=1</script>','ozmd_document'=>"# Individual Markdown\n\n```html\n<script>example</script>\n```\n\n[review_attack]\n"] as $type=>$source){
    $seq=count($expected)+1;$asset=wp_generate_uuid4();
    $attrs=['title'=>'Individual '.$type,'slug'=>'individual-'.$type,'status'=>'draft','date'=>'2026-11-24 01:00:00','date_gmt'=>'2026-11-24 01:00:00','post_type'=>$type,'content_format'=>$type==='page'?'wordpress-block-html':'markdown','origin_url'=>'http://isolated-review-source.invalid/?p='.$seq,'origin_id'=>$seq];
    $original=$store->prepare($asset,wp_generate_uuid4(),$source,$attrs);
    $store->commit(['schema'=>'owr-md-history-1','sequence'=>$seq,'original'=>$original,'attributes'=>$attrs,'confirmed_at'=>gmdate('c')]);
    $expected[]=['asset'=>$asset,'source'=>$source,'type'=>$type,'original'=>$original];
}
$c['setup_role']='recovery';update_option('ozeki_resilience_m1_config',$c,false);
file_put_contents('/lab/individual-expected.json',json_encode($expected));
echo json_encode(['sequences'=>[1,2],'local_only'=>true]);
