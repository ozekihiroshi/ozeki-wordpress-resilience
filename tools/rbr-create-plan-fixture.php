<?php
declare(strict_types=1);
/** Development-kit synthetic planning bundle; never constructs a runnable WordPress. */
require __DIR__.'/aws-autoload.php';
require dirname(__DIR__).'/src/VersionedAssetStore.php';
require dirname(__DIR__).'/src/RbrObjectStore.php';
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
require dirname(__DIR__).'/src/RbrReconstructionPlanner.php';
require __DIR__.'/rbr-planner-build.php';
require dirname(__DIR__).'/tests/support/RbrS3Double.php';
require dirname(__DIR__).'/tests/support/RbrPlannerFixture.php';
$o=getopt('', ['output:']);
if(!isset($o['output'])||file_exists($o['output'])||is_link($o['output'])){fwrite(STDERR,"Supply a new --output directory\n");exit(1);}
mkdir($o['output'],0700,true);$root=realpath($o['output']);
$f=new RbrPlannerFixture($root);mkdir($root.'/cache',0700);
foreach($f->cache as $sha=>$raw){file_put_contents($root.'/cache/'.$sha.'.blob',$raw);chmod($root.'/cache/'.$sha.'.blob',0600);}
file_put_contents($root.'/definition.json',Owr\RbrGenerationCoordinator::encode($f->definition));chmod($root.'/definition.json',0600);
file_put_contents($root.'/SYNTHETIC-ONLY.txt',"No executable WordPress/runtime/comparator packages. Planning fixtures only. No network requests.\n");
echo $root."/definition.json\n";
