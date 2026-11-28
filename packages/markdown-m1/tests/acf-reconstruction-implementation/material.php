<?php
spl_autoload_register(function($n){$p='OzekiResilience\\M1\\';if(str_starts_with($n,$p)){$f='/tmp/product/src/'.substr($n,strlen($p)).'.php';if(is_file($f))require_once $f;}});
use OzekiResilience\M1\{AcfHistory,AcfReconstruction,Store};
$mode=$args[0];$id=(int)($args[1]??0);$path='/tmp/acf-material.json';
function portable($groups){return array_map(fn($g)=>acf_prepare_internal_post_type_for_export($g,'acf-field-group'),$groups);}
if($mode==='capture'){
 $d=['tables'=>['posts'=>[['ID'=>$id,'post_type'=>'page','post_status'=>'publish']]]];AcfHistory::baseline($d);file_put_contents($path,Store::json($d));echo Store::json($d);return;
}
if($mode==='selected'){
 $raw=file_get_contents($path);$d=json_decode($raw,true);$event=AcfHistory::capture($id);AcfHistory::replay($d,Store::json($event),['origin_id'=>$id]);
 echo Store::json(['acf'=>$d['acf'],'portable'=>portable($d['acf']['acf_definitions']),'baseline_unchanged'=>hash('sha256',$raw)===hash_file('sha256',$path),'through'=>1,'plan'=>AcfReconstruction::plan(['source_url'=>home_url(),'through'=>1],['content.json'=>Store::json($d)])]);return;
}
if($mode==='read'){
 $v=AcfHistory::capture($id);echo Store::json(['capture'=>$v,'portable'=>portable($v['acf_definitions']),'formatted'=>get_fields($id)]);return;
}
if($mode==='negative'){
 $d=json_decode(file_get_contents($path),true);$cases=[];
 $bad=$d;$bad['acf']['acf_definitions'][0]['fields'][0]['type']='repeater';
 $cases['unsupported_type']=AcfReconstruction::plan(['source_url'=>home_url(),'through'=>0],['content.json'=>Store::json($bad)]);
 $bad=$d;unset($bad['acf']['posts'][(string)$id]['acf_values']['trial_text']);
 $cases['missing_value']=AcfReconstruction::plan(['source_url'=>home_url(),'through'=>0],['content.json'=>Store::json($bad)]);
 echo Store::json($cases);return;
}
throw new RuntimeException('Unknown observation mode');
