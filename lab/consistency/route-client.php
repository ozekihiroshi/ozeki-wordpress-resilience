<?php
// Run via php -r as the lab's external HTTP client (not a WordPress writer).
$action=getenv('OWR_ROUTE_ACTION');
$jar='/tmp/owr-route-cookies';
function request($path,$data=null,$headers=[]) {
    global $jar;
    $c=curl_init('http://127.0.0.1'.$path);
    curl_setopt_array($c,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_COOKIEFILE=>$jar,CURLOPT_COOKIEJAR=>$jar,
        CURLOPT_TIMEOUT=>20,CURLOPT_HTTPHEADER=>$headers]);
    if ($data!==null) { curl_setopt($c,CURLOPT_POST,true); curl_setopt($c,CURLOPT_POSTFIELDS,is_array($data)?http_build_query($data):$data); }
    $body=curl_exec($c); $status=curl_getinfo($c,CURLINFO_HTTP_CODE);
    if ($body===false) { throw new RuntimeException(curl_error($c)); }
    curl_close($c);
    return ['status'=>$status,'body'=>$body];
}
if ($action==='setup') {
    touch($jar); chmod($jar,0600);
    request('/wp-login.php');
    request('/wp-login.php',['log'=>'labadmin','pwd'=>getenv('LAB_ADMIN_PASSWORD'),'wp-submit'=>'Log In','testcookie'=>1]);
    $r=request('/route-nonce.php'); $nonces=json_decode($r['body'],true);
    if ($r['status']!==200 || !isset($nonces['rest'])) { throw new RuntimeException('login failed'); }
    $r=request('/wp-admin/post-new.php');
    $form=[]; $dom=new DOMDocument();
    $previous=libxml_use_internal_errors(true); $dom->loadHTML($r['body']);
    libxml_clear_errors(); libxml_use_internal_errors($previous);
    foreach ($dom->getElementsByTagName('input') as $input) { $form[$input->getAttribute('name')]=$input->getAttribute('value'); }
    if (!isset($form['_wpnonce'],$form['post_ID'])) { throw new RuntimeException('admin form missing, status '.$r['status']); }
    $nonces['admin_nonce']=$form['_wpnonce']; $nonces['post_id']=$form['post_ID'];
    file_put_contents('/tmp/owr-route-client.json',json_encode($nonces)); chmod('/tmp/owr-route-client.json',0600);
    echo json_encode(['status'=>200,'prepend'=>$nonces['prepend']]); return;
}
$n=json_decode(file_get_contents('/tmp/owr-route-client.json'),true);
switch ($action) {
case 'admin': $r=request('/wp-admin/post.php',['action'=>'editpost','post_ID'=>$n['post_id'],'_wpnonce'=>$n['admin_nonce'],
 'post_type'=>'post','post_title'=>'Admin route','content'=>'Actual admin form write','post_status'=>'publish','publish'=>'Publish']); break;
case 'rest': $r=request('/?rest_route=/wp/v2/posts',json_encode(['title'=>'REST route','status'=>'publish']),['Content-Type: application/json','X-WP-Nonce: '.$n['rest']]); break;
case 'media': $r=request('/?rest_route=/wp/v2/media','isolated route media',['Content-Type: text/plain','Content-Disposition: attachment; filename="route-media.txt"','X-WP-Nonce: '.$n['rest']]); break;
case 'ajax': $r=request('/wp-admin/admin-ajax.php',['action'=>'add-tag','taxonomy'=>'category','tag-name'=>'Route '.bin2hex(random_bytes(4)),'_wpnonce_add-tag'=>$n['tag']]); break;
case 'shutdown': $r=request('/wp-admin/admin-ajax.php',['action'=>'owr_shutdown_probe','_ajax_nonce'=>$n['shutdown']]); break;
case 'cron': $r=request('/wp-cron.php'); break;
case 'public': $r=request('/'); break;
case 'xmlrpc': $r=request('/xmlrpc.php','<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName><params/></methodCall>',['Content-Type: text/xml']); break;
case 'comments': $r=request('/wp-comments-post.php',['comment_post_ID'=>$n['post_id'],'comment'=>'blocked probe']); break;
case 'admin-post': $r=request('/wp-admin/admin-post.php',['action'=>'blocked_probe']); break;
case 'async-upload': $r=request('/wp-admin/async-upload.php',['action'=>'upload-attachment']); break;
case 'login': $r=request('/wp-login.php',['log'=>'labadmin','pwd'=>'blocked probe']); break;
case 'update': $r=request('/wp-admin/update.php',['action'=>'upgrade-plugin','plugin'=>'blocked_probe']); break;
default: throw new RuntimeException('unknown action');
}
// Do not print cookies, nonces, post bodies or credentials into the evidence.
echo json_encode(['status'=>$r['status'],'fenced'=>str_contains($r['body'],'"state":"fenced"')]);
