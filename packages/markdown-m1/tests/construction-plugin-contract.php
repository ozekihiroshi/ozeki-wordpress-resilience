<?php
require __DIR__.'/construction-follow.php';
use OzekiResilience\M1\{ConstructionOperations as O,ConstructionFollow as F,ConstructionContract as C};
$start=microtime(true);$checks=0;
foreach([1,7,42,10001] as $id){
 $options=[];
 $n=O::begin('rest',['actor'=>7,'route'=>'/wp/v2/pages','body'=>['content'=>'日本語 [table id="'.$id.'" /] [ozeki_markdown_document id="'.$id.'"] [contact-form-7 id="'.$id.'"]']]);O::finish($n,['response'=>['id'=>$id+1]]);
 $e=O::stable()['entries'][0];$raw=$e['input'];$q=F::prepare($e,0,['user:7'=>9,'table:'.$id=>'t-new-'.$id,'post:'.$id=>900+$id]);
 check($q['arguments']['content']==='日本語 [table id="t-new-'.$id.'" /] [ozeki_markdown_document id="'.(900+$id).'"] [contact-form-7 id="'.(900+$id).'"]','Typed embed substitution differs');
 check($raw===$e['input'],'Source input mutated');
 check(rejects(fn()=>F::prepare($e,0,['user:7'=>9,'post:'.$id=>900+$id])),'Missing table identity guessed');$checks+=3;
}
$options=[];
$body=['action'=>'editpost','post_ID'=>'42','post_type'=>'page','acf'=>['field_plain'=>'42','field_image'=>'42'],'user_ID'=>7];
$input=['path'=>'post.php','nonce_fields'=>['_wpnonce','_acf_nonce'],'body'=>$body,'field_contracts'=>['field_plain'=>['type'=>'text'],'field_image'=>['type'=>'image']]];
$n=O::begin('admin',$input);O::finish($n,['effects'=>[['type'=>'post','id'=>42,'post_type'=>'page']]]);
$e=O::stable()['entries'][0];$q=F::prepare($e,0,['post:42'=>99],8);
check($q['arguments']['body']['acf']===['field_plain'=>'42','field_image'=>99],'Structured value interpreted by its shape');
check($q['arguments']['body']['user_ID']===8,'Transport actor was not distinguished from content identity');$checks+=2;
unset($input['field_contracts']);check(C::describe('admin',$input)['coverage']==='incomplete','Missing source field type guessed');$checks++;
$c=C::describe('admin',['path'=>'admin-post.php','nonce_fields'=>['_wpnonce'],'body'=>['action'=>'tablepress_import','import'=>['source'=>'form-field','type'=>'add','form-field'=>'{"name":"42","data":[["42"]]}']]]);
check(C::outputs($c,['redirect'=>'https://source.invalid/wp-admin/admin.php?message=success_import&table_id=42'],true)===[['type'=>'table','id'=>'42']],'Table ID did not come from normal completion');
check(C::outputs($c,['effects'=>[['type'=>'post','id'=>42]]],true)===[],'Table result invented from unrelated post write');$checks+=2;
echo json_encode(['plugin_contract_checks'=>$checks,'seconds'=>round(microtime(true)-$start,4),'scope'=>'pure contract checks; not a substitute for normal plugin operations'])."\n";
