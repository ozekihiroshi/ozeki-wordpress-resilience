<?php
declare(strict_types=1);
/** Offline planner: explicit hash-addressed object cache only; no SDK/network/WordPress. */
require dirname(__DIR__).'/src/RbrGenerationCoordinator.php';
require dirname(__DIR__).'/src/RbrReconstructionPlanner.php';
require __DIR__.'/rbr-planner-build.php';
$o=getopt('', ['definition:', 'objects:', 'output:']);
try {
    if(!isset($o['definition'],$o['objects'],$o['output'])){throw new InvalidArgumentException('Required: --definition --objects --output');}
    if(!is_file($o['definition'])||is_link($o['definition'])||filesize($o['definition'])>2*1024*1024
        ||!is_dir($o['objects'])||is_link($o['objects'])||file_exists($o['output'])||is_link($o['output'])){
        throw new InvalidArgumentException('Require bounded definition, object directory and new output');
    }
    $cache=realpath($o['objects']);
    $reader=static function(array $ref)use($cache):string{
        $p=$cache.'/'.$ref['sha256'].'.blob';
        if(!is_file($p)||is_link($p)||realpath(dirname($p))!==$cache||filesize($p)>8*1024*1024){throw new RuntimeException('Missing or unsafe pinned object');}
        $raw=file_get_contents($p);if($raw===false){throw new RuntimeException('Pinned object unreadable');}return $raw;
    };
    $planner=new Owr\RbrReconstructionPlanner($reader,hash('sha256',rbrPlannerBuildBytes()));
    $plan=$planner->plan(file_get_contents($o['definition']));
    $bytes=Owr\RbrGenerationCoordinator::encode($plan);
    $fp=fopen($o['output'],'xb');if(!$fp){throw new RuntimeException('Output exists or unavailable');}
    chmod($o['output'],0600);
    try {if(fwrite($fp,$bytes)!==strlen($bytes)||!fflush($fp)){throw new RuntimeException('Plan output failed');}}
    catch(Throwable $e){fclose($fp);unlink($o['output']);throw $e;}
    fclose($fp);
    echo json_encode(['state'=>'planned','plan_sha256'=>hash('sha256',$bytes),'steps'=>count($plan['steps']),
        'execution_authorized'=>false,'environment_mode'=>$plan['environment_mode']],JSON_THROW_ON_ERROR)."\n";
} catch(Throwable $e){
    fwrite(STDERR,json_encode(['state'=>'rejected','reason'=>$e->getMessage(),'wp_invoked'=>false,'network_requested'=>false],JSON_THROW_ON_ERROR)."\n");exit(1);
}
