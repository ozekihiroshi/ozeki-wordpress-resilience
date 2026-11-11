<?php
declare(strict_types=1);
// Dedicated isolated site only. Expected input may contain secrets; never print it.
require __DIR__.'/AcfApplicationContract.php';
if(PHP_SAPI!=='cli'||$argc!==3)exit(2);
try{
    $input=json_decode(file_get_contents($argv[2]),true,512,JSON_THROW_ON_ERROR);
    $expected=AcfApplicationContract::expected($input['raw']);
    require $argv[1];
    $actual=AcfApplicationContract::observe($expected);
    $errors=AcfApplicationContract::differences($expected,$actual);
    $paths=[];
    $walk=function(array $data,array $path=[])use(&$walk,&$paths){foreach($data as $k=>$v){$p=[...$path,$k];if(is_array($v)&&$v)$walk($v,$p);else $paths[]=$p;}};
    $walk($expected);$detected=0;
    foreach($paths as $path){$broken=$expected;$ref=&$broken;foreach(array_slice($path,0,-1) as $k)$ref=&$ref[$k];unset($ref[end($path)]);unset($ref);if(AcfApplicationContract::differences($expected,$broken))$detected++;}
    echo json_encode(['pass'=>!$errors,'errors'=>$errors,'missing_leaf_cases'=>count($paths),'detected'=>$detected],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n";
    exit($errors||$detected!==count($paths)?1:0);
}catch(Throwable $e){echo "{\"pass\":false,\"error\":\"input-or-runtime\"}\n";exit(1);}
