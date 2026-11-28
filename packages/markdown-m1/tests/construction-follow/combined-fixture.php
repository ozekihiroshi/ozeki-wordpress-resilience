<?php
define('OWR_CONSTRUCTION_ISOLATED',true);
spl_autoload_register(function($name){$prefix='OzekiResilience\\M1\\';if(str_starts_with($name,$prefix)){
    $file='/tmp/product/src/'.substr($name,strlen($prefix)).'.php';if(is_file($file))require_once $file;
}});
add_action('plugins_loaded',function(){(new OzekiResilience\M1\ConstructionCapture())->boot();});
add_action('wpcf7_before_send_mail',function(){update_option('fixture_submission_count',(int)get_option('fixture_submission_count',0)+1,false);});
add_filter('pre_wp_mail',function($result,$mail){$p='/tmp/member-mail.json';$rows=is_file($p)?json_decode(file_get_contents($p),true):[];$rows[]=$mail;file_put_contents($p,wp_json_encode($rows));return true;},10,2);
