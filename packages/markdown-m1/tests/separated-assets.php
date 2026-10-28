<?php
// Standalone WordPress API fixture; product includes reject direct access.
if (!defined('ABSPATH')) define('ABSPATH', __DIR__.'/');
require $argv[1].'/src/Store.php';
require $argv[1].'/src/SiteSnapshot.php';
require $argv[1].'/src/CommentHistory.php';
require $argv[1].'/src/Plugin.php';
function get_option($key,$default=false){return $default;}
use OzekiResilience\M1\{AssetFormat,Store,SiteSnapshot};
function check($v,$m){if(!$v)throw new RuntimeException($m);}
function reject($f){try{$f();}catch(RuntimeException $e){return;}throw new RuntimeException('Expected failure');}
class SeparateS3 {
 public array $objects=[];public int $n=0;public ?string $fail=null;
 function putObject($a){if($this->fail&&str_contains($a['Key'],$this->fail))throw new RuntimeException('storage failure');if(isset($this->objects[$a['Key']]))throw new RuntimeException('exists');return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('version');return $r;}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&$k>($a['StartAfter']??''))$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
$s3=new SeparateS3();$store=new Store($s3,['bucket'=>'fixture','prefix'=>'trial/']);$site=new SiteSnapshot($store);
$md="# 原本\n```mermaid\ngraph LR; A-->B\n```\n$$ x^2 $$\n```php\necho 1;\n```\n";
$rows=[
 ['post'=>['ID'=>'1','post_type'=>'tablepress_table','post_content'=>'[["品名","数"],["資料",3]]'],'meta'=>[['meta_key'=>'_tablepress_table_options','meta_value'=>'{"paging":true}']], 'unknown'=>['extension'=>['keep'=>'verbatim']]],
 ['schema'=>'owr-comment-1','deleted'=>false,'comment'=>['comment_ID'=>'9','comment_post_ID'=>'1','comment_content'=>'独立したコメント本文','comment_approved'=>'1']],
 ['post'=>['ID'=>'3','post_type'=>'flamingo_inbound','post_content'=>'問い合わせ本文'],'meta'=>[['meta_key'=>'_fields','meta_value'=>serialize(['your-name'=>'試験者','your-message'=>"質問\n二行目"])],['meta_key'=>'unrecognized','meta_value'=>'unknown preserved']]],
 ['user'=>['user_login'=>'subscriber','user_pass'=>'hash-preserved','display_name'=>'会員氏名'],'meta'=>['active'=>['1']]],
 ['meta_key'=>'_ozmd_source','meta_value'=>$md],
];
foreach($rows as $i=>$row){
 $raw=Store::json($row);$a=['content_format'=>'table-json','title'=>'Fixture'];
 $o=$store->prepare('fixture-'.$i,'save',$raw,$a);check($store->originalSource($o)===$raw,'lossless structured original');
 $layout=json_decode($store->get($o['metadata']),true)['structure'];$direct=[];
 foreach($o['parts'] as $path=>$ref)$direct[$path]=$store->get($ref);
 check(AssetFormat::join($layout,$direct)===$row,'independent files + metadata');
 if($i===0)check(in_array('[["品名","数"],["資料",3]]',$direct,true),'table values directly readable JSON without settings');
 if($i===2){check(in_array(Store::json(['your-name'=>'試験者','your-message'=>"質問\n二行目"]),$direct,true),'inquiry fields readable without PHP unserialize');}
 if($i===4)check(in_array($md,$direct,true),'Markdown exact bytes');
 $saved=$s3->objects;$first=reset($o['parts']);$s3->objects['trial/'.$first['key']]['Body']='corruption';reject(fn()=>$store->originalSource($o));$s3->objects=$saved;
}
$a=['content_format'=>'markdown'];$o=$store->prepare('markdown','save',$md,$a);check($store->get($o['source'])===$md,'raw MD direct');
$html='<p>企業案内</p>';$o=$store->prepare('page','save',$html,['content_format'=>'wordpress-block-html']);check($store->get($o['source'])===$html,'raw HTML direct');
// Legacy objects are read without migration or writing.
$old=['schema'=>'owr-md-original-1','source'=>$store->put('legacy/source.md',$md,'text/markdown')];$before=$s3->objects;check($store->originalSource($old)===$md&&$before===$s3->objects,'legacy read only');
$d=['tables'=>['posts'=>[['ID'=>'1','post_type'=>'page','post_content'=>$html]],'postmeta'=>[['post_id'=>'2','meta_key'=>'_ozmd_source','meta_value'=>$md],['post_id'=>'1','meta_key'=>'unknown','meta_value'=>'keep unknown']], 'comments'=>[$rows[1]['comment']]],'options'=>['theme_mods_trial'=>['colour'=>'red']],'unknown'=>['preserved'=>true]];
$files=['content.json'=>Store::json($d),'markdown/2.md'=>$md,'uploads/photo.png'=>'image bytes','software.zip'=>'software bytes'];
$manifest=['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','through'=>0,'source_url'=>'https://lost.invalid'];
$initial=$site->save($files,$manifest);$rawManifest=json_decode($store->get($initial['manifest']),true);
check(!isset($rawManifest['resources']['content.json'])&&isset($rawManifest['resources']['assets/metadata.json']),'no mixed content.json stored');
$metadata=$store->get($rawManifest['resources']['assets/metadata.json']);check(!str_contains($metadata,$html)&&!str_contains($metadata,'独立したコメント本文'),'metadata excludes body');
$cp=$site->checkpoint($initial['manifest']);
$prefix='trial/'.dirname($cp['manifest']['key']).'/';foreach(array_keys($s3->objects) as $key)if(!str_starts_with($key,$prefix))unset($s3->objects[$key]);
[$m,$loaded]=$site->load($cp['manifest']);ksort($files);check($loaded===$files,'Checkpoint independent, all unknown information retained');
// Tail uses the same representation and the existing typed replay.
$attrs=['post_type'=>'owr_comment','content_format'=>'comment-json','origin_id'=>9,'post_id'=>1,'status'=>'1'];$r=$rows[1];$r['comment']['comment_content']='更新後のコメント';
$o=$store->prepare('comment-9','updated',Store::json($r),$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$o,'attributes'=>$attrs]);
$next=$site->checkpoint($cp['manifest']);[$m,$loaded]=$site->load($next['manifest']);check(json_decode($loaded['content.json'],true)['tables']['comments'][0]['comment_content']==='更新後のコメント','structured tail replay');
$s3->fail='metadata.json';$count=count($store->history());reject(fn()=>$store->prepare('failed','save',Store::json($r),$attrs));check(count($store->history())===$count,'partial write not confirmed');
echo "PASS independent Markdown/HTML/table/inquiry/comment data, lossless unknown fields, separate metadata, legacy read, independent Checkpoint and structured tail, corruption/partial write rejection. Memory S3 only.\n";
