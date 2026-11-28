<?php
// Prepared local WP-CLI worker bridge. Not a public upload/command endpoint.
use OzekiResilience\M1\{ConstructionAdmin,ConstructionJob,Plugin,SetupReadiness,ConstructionAuthors};
if(!class_exists(ConstructionAdmin::class))require_once __DIR__.'/../src/ConstructionAdmin.php';
if(!class_exists(ConstructionJob::class))require_once __DIR__.'/../src/ConstructionJob.php';
if(!defined('WP_CLI')||!WP_CLI)throw new RuntimeException('Local WP-CLI worker only');
ConstructionAdmin::authorize();
$p=new Plugin();$job=new ConstructionJob(ConstructionAdmin::store(),SetupReadiness::identity($p->config()));
$operation=$args[0]??'';
if($operation==='claim')echo wp_json_encode($job->claim());
elseif($operation==='authors'){
    $kit=json_decode(file_get_contents($args[1]),true,512,JSON_THROW_ON_ERROR);
    echo wp_json_encode(ConstructionAuthors::register($kit));
}elseif($operation==='finish'){
    $job->finish(json_decode(file_get_contents($args[1]),true,512,JSON_THROW_ON_ERROR));echo wp_json_encode(ConstructionJob::summary());
}else throw new RuntimeException('Unknown worker command');
