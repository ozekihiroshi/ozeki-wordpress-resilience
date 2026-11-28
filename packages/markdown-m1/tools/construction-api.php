<?php
use OzekiResilience\M1\{ConstructionTransfer,ConstructionAuthors,ConstructionBundle,FlamingoReconstruction,ConstructionFollow};
// Isolated CLI bridge for normal APIs not exposed by WordPress REST.
if(!defined('OWR_CONSTRUCTION_ISOLATED')||!OWR_CONSTRUCTION_ISOLATED||!defined('WP_CLI')||!WP_CLI)throw new RuntimeException('Isolated CLI only');
if(!current_user_can('manage_options'))throw new RuntimeException('Select a prepared destination administrator with WP-CLI --user');
$input=json_decode(file_get_contents($args[0]),true,512,JSON_THROW_ON_ERROR);
switch($input['operation']){
case 'prepare-initial-content':
    $out=ConstructionFollow::initial($input['material'],$input['identities']);break;
case 'accept-operation':
    $out=ConstructionFollow::accept($input['entry'],$input['returned'],$input['identities']);break;
case 'prepare-operation':
    $out=ConstructionFollow::prepare($input['entry'],$input['through'],$input['identities'],get_current_user_id());break;
case 'follow':
    $out=ConstructionFollow::run($input['entries'],$input['through'],$input['identities'],function($endpoint,$id,$body){
        $r=new WP_REST_Request('POST',$endpoint.($id===null?'':'/'.$id));$r->set_header('Content-Type','application/json');$r->set_body(wp_json_encode($body));
        $response=rest_do_request($r);if($response->get_status()>=400)throw new RuntimeException(wp_json_encode($response->get_data()));
        return (int)($response->get_data()['id']??0);
    });break;
case 'menu':
    $id=wp_create_nav_menu($input['name']);if(is_wp_error($id))throw new RuntimeException($id->get_error_message());$out=['id'=>$id];break;
case 'menu-item':
    $id=wp_update_nav_menu_item($input['menu'],0,$input['item']);if(is_wp_error($id))throw new RuntimeException($id->get_error_message());$out=['id'=>$id];break;
case 'receipt':
    $out=FlamingoReconstruction::recorded($input['entry'],$input['source'],$input['form'],$input['journal'],true);break;
default:throw new RuntimeException('Unsupported normal API operation');
}
echo wp_json_encode($out);
