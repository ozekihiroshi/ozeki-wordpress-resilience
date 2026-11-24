<?php
require __DIR__.'/separated-assets.php';
use OzekiResilience\M1\{Store,SiteSnapshot,UpdateContract};
$s3->fail=null;
$store=new Store($s3,['bucket'=>'fixture','prefix'=>'identity/']);$site=new SiteSnapshot($store);
$d=['update_contract'=>UpdateContract::SCHEMA,'authors'=>[],'options'=>[],'media_access'=>[],'tables'=>['posts'=>[['ID'=>'10','post_type'=>'post','post_status'=>'publish','post_content'=>'Before']],'postmeta'=>[]]];
$initial=$site->save(['content.json'=>Store::json($d)],['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','through'=>0,'source_url'=>'https://lost.invalid']);
$a=['update_contract'=>UpdateContract::SCHEMA,'post_type'=>'post','content_format'=>'wordpress-block-html','post_excerpt'=>'','post_parent'=>'0','menu_order'=>'0','comment_status'=>'closed','ping_status'=>'closed','post_password'=>'','post_author'=>'0','author'=>null,'title'=>'Protected draft','status'=>'draft','slug'=>'protected','date'=>'2026-11-24 00:00:00','date_gmt'=>'2026-11-24 00:00:00','origin_id'=>10];
$o=$store->prepare('protected-article','first','Draft body',$a);$store->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$a]);
$cp=$site->checkpoint($initial['manifest']);[$m,$files]=$site->load($cp['manifest']);$after=json_decode($files['content.json'],true);
$markers=array_values(array_filter($after['tables']['postmeta'],fn($r)=>$r['meta_key']==='_ozeki_resilience_m1_asset'));
check(count($markers)===1&&$markers[0]['meta_value']==='protected-article'&&(int)$markers[0]['post_id']===10,'Existing Baseline article inherits daily protection identity');
check($after['tables']['posts'][0]['post_status']==='draft','Protection identity does not publish draft');
echo "PASS protected identity on existing Baseline article\n";
