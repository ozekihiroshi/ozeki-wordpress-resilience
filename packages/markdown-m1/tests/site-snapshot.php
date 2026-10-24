<?php
require '/var/www/html/wp-load.php';
require_once $argv[1].'/src/SiteSnapshot.php';
use Owr\M1\SiteSnapshot;
use Owr\M1\Store;
function must($v,$m){if(!$v)throw new RuntimeException($m);}
function no($f){try{$f();}catch(Throwable $e){return;}throw new RuntimeException('Expected rejection');}
foreach(['../a','a/../b','/root','C:/x','a\\b'] as $p)no(fn()=>SiteSnapshot::safePath($p));
must(SiteSnapshot::relocate(['x'=>'https://source.invalid/a','other'=>'https://source.invalid.evil/a'],'https://source.invalid','https://target.invalid')===['x'=>'https://target.invalid/a','other'=>'https://source.invalid.evil/a'],'URL boundary');
class SiteMemoryS3 {
 public array $objects=[];public int $n=0;public bool $fail=false;
 function putObject($a){if($this->fail&&str_ends_with($a['Key'],'manifest.json'))throw new RuntimeException('manifest failure');if(isset($this->objects[$a['Key']]))throw new RuntimeException('exists');return $this->objects[$a['Key']]=['Body'=>$a['Body'],'VersionId'=>'v'.++$this->n];}
 function getObject($a){$r=$this->objects[$a['Key']]??throw new RuntimeException('missing',404);if(isset($a['VersionId'])&&$a['VersionId']!==$r['VersionId'])throw new RuntimeException('wrong version');return $r;}
 function listObjectsV2($a){$out=[];foreach($this->objects as $k=>$v)if(str_starts_with($k,$a['Prefix'])&&(!isset($a['StartAfter'])||strcmp($k,$a['StartAfter'])>0))$out[]=['Key'=>$k];return ['Contents'=>$out];}
}
$s3=new SiteMemoryS3();$store=new Store($s3,['bucket'=>'test','prefix'=>'site/','retention_days'=>36]);$site=new SiteSnapshot($store);
$m=['schema'=>'owr-site-snapshot-1','source_url'=>'https://lost.invalid','through'=>0,'origin'=>'administrator_initial','wordpress'=>'7.1.2'];
$f=['content.json'=>Store::json(['tables'=>['posts'=>[],'postmeta'=>[]]]),'markdown/1.md'=>"# 完全原文\n```mermaid\ngraph LR; A-->B\n```",'uploads/p.pdf'=>'pdf-bytes','software.zip'=>'bundle'];
$s3->fail=true;no(fn()=>$site->save($f,$m));must(!array_filter(array_keys($s3->objects),fn($k)=>str_ends_with($k,'manifest.json')),'partial invisible');
$s3->fail=false;$initial=$site->save($f,$m);$cp=$site->checkpoint($initial['manifest']);
$base='site/'.dirname($cp['manifest']['key']).'/';foreach(array_keys($s3->objects) as $k)if(!str_starts_with($k,$base))unset($s3->objects[$k]);
[$loaded,$files]=$site->load($cp['manifest']);ksort($f);must($files===$f,'complete snapshot independent after ancestor removal');
$attrs=['title'=>'new document','slug'=>'new-document','status'=>'publish','date'=>'2026-10-24 05:00:00','date_gmt'=>'2026-10-24 05:00:00','origin_id'=>42,'origin_url'=>'https://lost.invalid/new-document/'];
$original=$store->prepare('new-doc','new-operation',"# New document\n",$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>1,'original'=>$original,'attributes'=>$attrs]);
$tail=$site->checkpoint($cp['manifest']);[$tailManifest,$tailFiles]=$site->load($tail['manifest']);must($tailManifest['through']===1&&$tailFiles['markdown/42.md']==="# New document\n",'new confirmed document included');
$tailData=json_decode($tailFiles['content.json'],true);must($tailData['tables']['posts'][0]['post_status']==='publish','new document publication state');
$attrs['origin_id']=43;$attrs['post_type']='page';$attrs['content_format']='wordpress-block-html';$attrs['title']='Full page';$attrs['slug']='full-page';
$html='<!-- wp:paragraph --><p>Complete page content</p><!-- /wp:paragraph -->';
$original=$store->prepare('page-43','publish-page',$html,$attrs);must(str_ends_with($original['source']['key'],'.html'),'native original is HTML');
$store->commit(['schema'=>'owr-md-history-1','sequence'=>2,'original'=>$original,'attributes'=>$attrs]);
$attrs['status']='trash';$original=$store->prepare('page-43','trash-page',$html,$attrs);
$store->commit(['schema'=>'owr-md-history-1','sequence'=>3,'original'=>$original,'attributes'=>$attrs]);
$native=$site->checkpoint($tail['manifest']);[$nm,$nf]=$site->load($native['manifest']);$nd=json_decode($nf['content.json'],true);
$page=array_values(array_filter($nd['tables']['posts'],fn($p)=>(int)$p['ID']===43))[0];
must($nm['through']===3&&$page['post_type']==='page'&&$page['post_status']==='trash'&&$page['post_content']===$html,'native page and deletion replay');
must($nf['posts/43.html']===$html,'independent complete native original');
$imageRef=$store->put('originals/page-43/image-op/media/test.png','image-v1','image/png');
$attrs['status']='publish';$attrs['media']=[['post'=>['ID'=>'44','post_type'=>'attachment','post_mime_type'=>'image/png'],'meta'=>['_wp_attached_file'=>'2026/10/test.png','_wp_attachment_metadata'=>['file'=>'2026/10/test.png','width'=>800,'height'=>400],'_wp_attachment_image_alt'=>'Trial image'],'files'=>['uploads/2026/10/test.png'=>$imageRef]]];
$original=$store->prepare('page-43','image-op',$html,$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>4,'original'=>$original,'attributes'=>$attrs]);
$images=$site->checkpoint($native['manifest']);[$im,$if]=$site->load($images['manifest']);
must($im['through']===4&&$if['uploads/2026/10/test.png']==='image-v1','new image replay');
$imageRef2=$store->put('originals/page-43/replace-op/media/test2.png','image-v2','image/png');
$attrs['media'][0]['post']['ID']='45';$attrs['media'][0]['files']=['uploads/2026/10/test2.png'=>$imageRef2];$attrs['media'][0]['meta']['_wp_attached_file']='2026/10/test2.png';$attrs['media'][0]['meta']['_wp_attachment_metadata']['file']='2026/10/test2.png';
$html2='<p><img class="wp-image-45" src="https://lost.invalid/wp-content/uploads/2026/10/test2.png" /></p>';
$original=$store->prepare('page-43','replace-op',$html2,$attrs);$store->commit(['schema'=>'owr-md-history-1','sequence'=>5,'original'=>$original,'attributes'=>$attrs]);
$replaced=$site->checkpoint($images['manifest']);
$independentPrefix='site/'.dirname($replaced['manifest']['key']).'/';
$savedObjects=$s3->objects;foreach(array_keys($s3->objects) as $key)if(!str_starts_with($key,$independentPrefix))unset($s3->objects[$key]);
[$rm,$rf]=$site->load($replaced['manifest']);must($rf['uploads/2026/10/test2.png']==='image-v2'&&$rf['posts/43.html']===$html2,'replacement and independent media checkpoint');
$s3->objects=$savedObjects;$s3->objects['site/'.$imageRef2['key']]['Body']='damaged';no(fn()=>$site->checkpoint($images['manifest']));
$s3->objects=$savedObjects;
$resource=$loaded['resources']['uploads/p.pdf'];$s3->objects['site/'.$resource['key']]['Body']='corrupt';no(fn()=>$site->load($cp['manifest']));
echo "PASS path rejection, serialized-value URL boundary, failed manifest/retry, independent full-file checkpoint after removing ancestors, corruption rejection. In-memory storage only.\n";
