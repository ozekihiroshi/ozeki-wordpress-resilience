<?php
require __DIR__.'/construction-plugin-contract.php';
use OzekiResilience\M1\{ConstructionOperations as O,ConstructionContract as C,ConstructionFollow as F};
function wpcf7_get_contact_form_by_hash($hash){if(!in_array($hash,['abc1234','1234567'],true))return null;return new class($hash){public function __construct(private string $h){}public function hash($n=7){return substr($this->h,0,$n);}public function id(){return 51;}};}
$options=[];$start=microtime(true);$checks=0;
$n=O::begin('rest',['route'=>'/wp/v2/media','body'=>[],'upload'=>['base64'=>base64_encode('synthetic'),'content_type'=>'image/png','content_disposition'=>'attachment; filename="diagram.png"']]);
O::finish($n,['response'=>['id'=>12],'reference_values'=>['image-url:full'=>'https://fixture.invalid/uploads/diagram.png','image-url:thumbnail'=>'https://fixture.invalid/uploads/diagram-150.png']]);
$map=['user:7'=>9,'post:51'=>91,'cf7-hash:51'=>'def9876','image-url:full:12'=>'https://target.invalid/other.png','image-url:thumbnail:12'=>'https://target.invalid/other-small.png'];
foreach(['abc1234','1234567'] as $hash){
 $text='<img src="https://fixture.invalid/uploads/diagram-150.png"/> [contact-form-7 id="'.$hash.'"] <img src="https://fixture.invalid.evil.invalid/uploads/diagram.png"/>';
 $n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>$text]]);O::finish($n,['response'=>['id'=>70+$n]]);$e=O::stable()['entries'][$n-1];
 $q=F::prepare($e,$n-1,$map);
 check($q['arguments']['content']==='<img src="https://target.invalid/other-small.png"/> [contact-form-7 id="def9876"] <img src="https://fixture.invalid.evil.invalid/uploads/diagram.png"/>','Wrong image/hash/external interpretation');
 check($e['input']['body']['content']===$text,'Raw source input changed');$checks+=2;
}
foreach(['https://fixture.invalid/uploads/diagram.png.extra','https://fixture.invalid/other/diagram.png','https://fixture.invalid/uploads/diagram.png?other=1'] as $url){
 $c=C::describe('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'<img src="'.$url.'"/>']]);check($c['coverage']==='incomplete','Unresolved similar URL guessed');$checks++;
}
$raw='日本語 ![x](https://fixture.invalid/uploads/diagram.png)';
$i=['path'=>'admin-post.php','nonce_fields'=>['_wpnonce'],'body'=>['action'=>'ozmd_import_document'],'files'=>['ozmd_file'=>['name'=>'a.md','base64'=>base64_encode($raw)]]];
$n=O::begin('admin',$i);O::finish($n,['effects'=>[['type'=>'post','post_type'=>'ozmd_document','id'=>80]]]);$e=O::stable()['entries'][$n-1];$q=F::prepare($e,$n-1,$map);
check(base64_decode($q['arguments']['files']['ozmd_file']['base64'])==='日本語 ![x](https://target.invalid/other.png)','Upload span not applied to ordinary import');
check($e['input']===$i,'Upload original altered');$checks+=2;
$c=C::describe('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'[contact-form-7 id="unknown"]']]);check($c['coverage']==='incomplete','Unknown hash guessed');$checks++;
$media=O::stable()['entries'][0];check(rejects(fn()=>F::accept($media,['id'=>90,'reference_values'=>['image-url:full'=>'https://target.invalid/a.png']],[])),'Missing destination size invented');$checks++;
$n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'<img class="wp-image-12" title="wp-image-12" src="/uploads/diagram.png"/>']]);O::finish($n,['response'=>['id'=>89]]);$e=O::stable()['entries'][$n-1];
$q=F::prepare($e,$n-1,$map+['post:12'=>92]);check($q['arguments']['content']==='<img class="wp-image-92" title="wp-image-12" src="https://target.invalid/other.png"/>','Class identity/ordinary title distinction lost');$checks++;
foreach(['<img src="diagram.png"/>','<img class="wp-image-99" src="https://fixture.invalid/uploads/diagram.png"/>'] as $text){check(C::describe('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>$text]])['coverage']==='incomplete','Unresolved image context silently followed');$checks++;}
echo json_encode(['source_reference_checks'=>$checks,'seconds'=>round(microtime(true)-$start,5)])."\n";
