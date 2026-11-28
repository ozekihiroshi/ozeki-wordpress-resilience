<?php
define('ABSPATH',__DIR__.'/');
// No fixture autoloader: the management entry must load its runtime dependencies.
require __DIR__.'/../src/ConstructionAdmin.php';
foreach(['ConstructionAdmin','ConstructionJournal','ConstructionPreservation','ConstructionJob','ConstructionFollow','FlamingoReconstruction','ConstructionAuthors','ConstructionTransfer','ConstructionBundle','ConstructionReadiness','ConstructionSafety'] as $name){
    if(!class_exists('OzekiResilience\\M1\\'.$name,false))throw new RuntimeException('Fixture-only autoload dependency: '.$name);
}
if(OzekiResilience\M1\ConstructionAdmin::enabled())throw new RuntimeException('Development entry enabled without explicit flags');
echo "PASS management runtime dependencies without fixture autoload; inactive by default\n";
