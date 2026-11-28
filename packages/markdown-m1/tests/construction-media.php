<?php
function serialize_block_attributes($a){return json_encode($a,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);}
require __DIR__.'/construction-references.php';
use OzekiResilience\M1\{ConstructionOperations as O,ConstructionContract as C,ConstructionFollow as F};
$options=[];$checks=0;
$n=O::begin('rest',['route'=>'/wp/v2/media','body'=>[],'upload'=>['base64'=>base64_encode('synthetic'),'content_type'=>'image/png','content_disposition'=>'attachment; filename="x.png"']]);O::finish($n,['response'=>['id'=>12],'reference_values'=>['image-url:full'=>'https://fixture.invalid/x.png']]);
$content='<!-- wp:gallery {"ids":[12],"columns":12} --><!-- wp:image {"id":12,"width":12,"url":"https://fixture.invalid/x.png"} --><figure><img class="wp-image-12" src="https://fixture.invalid/x.png"/></figure><!-- /wp:image --><!-- /wp:gallery -->';
$n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>$content]]);O::finish($n,['response'=>['id'=>22]]);$e=O::stable()['entries'][$n-1];
$q=F::prepare($e,$n-1,['user:7'=>9,'post:12'=>99,'image-url:full:12'=>'https://target.invalid/new.png']);
check(str_contains($q['arguments']['content'],'"ids":[99],"columns":12')&&str_contains($q['arguments']['content'],'"id":99,"width":12'),'Block display numbers treated as identity');
check(substr_count($q['arguments']['content'],'https://target.invalid/new.png')===2,'Block URL/HTML URL disagreement');$checks+=2;
foreach(['<!-- wp:unknown {"id":12} /-->','<!-- wp:image {"id":12,"metadata":{"bindings":{}}} /-->'] as $unknown){check(C::describe('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>$unknown]])['coverage']==='incomplete','Unknown block semantics guessed');$checks++;}
$n=O::begin('rest',['method'=>'POST','route'=>'/wp/v2/media/12/edit','body'=>['src'=>'https://fixture.invalid/x.png','modifiers'=>[['type'=>'rotate','args'=>['angle'=>90]]]]]);O::finish($n,['response'=>['id'=>31],'reference_values'=>['image-url:full'=>'https://fixture.invalid/edited.png']]);
$e=O::stable()['entries'][$n-1];check($e['outputs']===[['type'=>'post','id'=>31]],'Normal image edit new identity was forced to old identity');$checks++;
$map=['user:7'=>9,'post:12'=>99,'image-url:full:12'=>'https://target.invalid/new.png'];
$n=O::begin('rest',['method'=>'DELETE','route'=>'/wp/v2/media/12','body'=>[],'query'=>['force'=>'true']]);O::finish($n,['response'=>['deleted'=>true,'previous'=>['id'=>12]]]);$e=O::stable()['entries'][$n-1];
$prepared=F::prepare($e,$n-1,$map);check($prepared['target']===99,'Deletion target guessed');$map=F::accept($e,true,$map);check($map['deleted:12']===true,'Deletion not remembered');$checks+=2;
$n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>$content]]);O::finish($n,['response'=>['id'=>40]]);$e=O::stable()['entries'][$n-1];
check($e['contract']['spans'][0]['source_state']==='deleted','Dangling original reference not captured');F::prepare($e,$n-1,$map);$checks++;
unset($map['deleted:12']);check(rejects(fn()=>F::prepare($e,$n-1,$map)),'Live/deleted state difference ignored');$checks++;
echo json_encode(['block_and_media_checks'=>$checks])."\n";
