<?php
/** WP-CLI eval-file only; never install a web-accessible endpoint. */
if(!defined('WP_CLI')||!WP_CLI)throw new RuntimeException('WP-CLI required');
if(count($args)!==4||$args[3]!=='isolated')throw new RuntimeException('Expected plan, CF7 mapping, new journal, isolated');
require_once __DIR__.'/../src/FlamingoReconstruction.php';
$plan=json_decode(file_get_contents($args[0]),true,512,JSON_THROW_ON_ERROR);
$map=json_decode(file_get_contents($args[1]),true,512,JSON_THROW_ON_ERROR);
echo wp_json_encode(\OzekiResilience\M1\FlamingoReconstruction::run($plan,$map,$args[2],true));
