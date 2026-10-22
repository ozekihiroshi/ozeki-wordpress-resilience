<?php
declare(strict_types=1);
/** Identify loaded planning implementation outside the pure planning call. No credentials/network. */
function rbrPlannerBuildBytes(): string {
    $root=dirname(__DIR__);$files=[];
    foreach(['src/RbrReconstructionPlanner.php','src/RbrGenerationCoordinator.php','tools/rbr-wordpress-apply.php','tools/rbr-wordpress-observe.php','tools/rbr-reconstruct-lab.py','tools/rbr-compare.py'] as $name){
        $raw=file_get_contents($root.'/'.$name);if($raw===false){throw new RuntimeException('Planner source unavailable');}
        $files[$name]=base64_encode($raw);
    }
    return json_encode(['kind'=>'owr-planner-source-bundle-v1','files'=>$files],JSON_THROW_ON_ERROR|JSON_UNESCAPED_SLASHES)."\n";
}
