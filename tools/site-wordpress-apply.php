<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'){throw new RuntimeException('CLI required');}
$args=getopt('', ['wordpress:','input:','target-url:','user:','allow-target']);
$legacy=getenv('OWR_RBR_DISPOSABLE')==='1' && !isset($args['wordpress']);
if($legacy){
    $wordpress='/var/www/html';$inputFile='/bundle/received.json';
}else{
    foreach(['wordpress','input','target-url','user','allow-target'] as $key){
        if(!array_key_exists($key,$args)){throw new RuntimeException('Explicit WordPress path, input, target URL, administrator and --allow-target required');}
    }
    $wordpress=realpath($args['wordpress']);$inputFile=realpath($args['input']);
    if(!$wordpress||!is_file($wordpress.'/wp-load.php')||!$inputFile||!is_file($inputFile)){
        throw new RuntimeException('Target or input missing');
    }
}
require $wordpress.'/wp-load.php';
if(!$legacy){
    if(rtrim((string)get_option('siteurl'),'/')!==rtrim($args['target-url'],'/')){throw new RuntimeException('Target URL mismatch');}
    wp_set_current_user((int)$args['user']);
    if(!current_user_can('manage_options')){throw new RuntimeException('Target administrator required');}
}
require_once __DIR__.'/../src/SiteMaterialsProjection.php';
$input=json_decode(file_get_contents($inputFile),true,64,JSON_THROW_ON_ERROR);
$result=owr_site_materials_apply($input,$legacy&&getenv('OWR_SITE_INCREMENTAL')==='1');
$canonical=function($v)use(&$canonical){
    if(!is_array($v))return $v;
    if(!array_is_list($v))ksort($v,SORT_STRING);
    return array_map($canonical,$v);
};
$result['logical_sha256']=hash('sha256',json_encode($canonical($input['expected']),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_LINE_TERMINATORS|JSON_THROW_ON_ERROR)."\n");
echo json_encode($result,JSON_THROW_ON_ERROR);
