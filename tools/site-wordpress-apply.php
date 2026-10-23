<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'||getenv('OWR_RBR_DISPOSABLE')!=='1'){throw new RuntimeException('Dedicated environment required');}
require '/var/www/html/wp-load.php';
require_once __DIR__.'/../src/SiteMaterialsProjection.php';
$input=json_decode(file_get_contents('/bundle/received.json'),true,64,JSON_THROW_ON_ERROR);
echo json_encode(owr_site_materials_apply($input,getenv('OWR_SITE_INCREMENTAL')==='1'),JSON_THROW_ON_ERROR);
