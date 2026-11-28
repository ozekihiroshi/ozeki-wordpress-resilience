<?php
use OzekiResilience\M1\{ConstructionOperations as O,ConstructionAuthors as A,ConstructionFollow as F};
$start=microtime(true);
$login=$args[0]==='source'?'source-operator':'destination-admin';wp_set_current_user(get_user_by('login',$login)->ID);
function ordinary($endpoint,$id,$body){
    $r=new WP_REST_Request('POST',$endpoint.($id===null?'':'/'.$id));$r->set_header('Content-Type','application/json');$r->set_body(wp_json_encode($body));
    $response=rest_do_request($r);if($response->get_status()>=400)throw new RuntimeException(wp_json_encode($response->get_data()));return $response->get_data();
}
if($args[0]==='source'){
    // Focused baseline: a real existing author, not a supplied destination ID.
    // Full SiteSnapshot storage is covered separately, not claimed by this test.
    $p=get_posts(['post_type'=>'post','post_status'=>'publish','numberposts'=>1])[0];
    $kit=O::initialSaveWithAuthors(fn()=>[['source_url'=>home_url()],['content.json'=>wp_json_encode(['tables'=>['posts'=>[(array)$p]]])]]);
    $parent=ordinary('/wp/v2/pages',null,['title'=>'Parent','status'=>'publish']);
    $child=ordinary('/wp/v2/pages',null,['title'=>'Child','status'=>'publish','parent'=>$parent['id']]);
    ordinary('/wp/v2/pages',$child['id'],['title'=>'Edited']);
    ordinary('/wp/v2/pages',$child['id'],['parent'=>0]);
    $kit['journal']=O::stable();file_put_contents('/tmp/follow-kit.json',wp_json_encode($kit));
    echo wp_json_encode(['seconds'=>microtime(true)-$start,'recorded'=>count($kit['journal']['entries'])]);
}else{
    // Make destination allocations differ through ordinary preparation.
    foreach(range(1,3) as $i)wp_insert_post(['post_type'=>'page','post_title'=>'Prepared '.$i,'post_status'=>'draft']);
    $kit=json_decode(file_get_contents('/tmp/follow-kit.json'),true);$before=hash('sha256',wp_json_encode($kit));
    $authors=A::register(['files'=>$kit['files'],'anchor'=>$kit['construction_anchor']]);$identities=[];foreach($authors as $old=>$new)$identities['user:'.$old]=$new;
    $entries=O::afterInitialSave($kit['construction_anchor'],$kit['manifest'],$kit['files'],$kit['journal']);$observed=[];
    $result=F::run($entries,$kit['construction_anchor']['through'],$identities,function($endpoint,$target,$body)use(&$observed){
        $r=ordinary($endpoint,$target,$body);$observed[]=['id'=>$r['id'],'parent'=>$r['parent'],'title'=>$r['title']['raw'],'author'=>$r['author']];return (int)$r['id'];
    });
    $passed=count($observed)===4&&$observed[1]['parent']===$observed[0]['id']&&$observed[2]['id']===$observed[1]['id']&&$observed[2]['title']==='Edited'&&$observed[3]['parent']===0;
    $different=true;foreach($entries as $i=>$entry)$different=$different&&$entry['outputs'][0]['id']!==$observed[$i]['id'];
    if(!$passed||!$different||$before!==hash('sha256',wp_json_encode($kit)))throw new RuntimeException('Following ordinary operations differs');
    echo wp_json_encode(['seconds'=>microtime(true)-$start,'sequence'=>$result['completed'],'new_ids'=>$different,'parent_then_update_then_unlink'=>$passed,'input_unchanged'=>true]);
}
