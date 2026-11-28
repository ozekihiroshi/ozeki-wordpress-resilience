<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/ConstructionContract.php';

/** Development-only local journal. Not enabled by Plugin::boot or an S3 format. */
final class ConstructionOperations {
    public const KEY='ozeki_resilience_construction_experiment_v5';
    public const SCHEMA='owr-observed-construction-experiment-5';
    private static function write(array $s): void {
        $raw=wp_json_encode($s,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
        if($raw===false || strlen($raw)>8*1024*1024)throw new \RuntimeException('Construction journal limit; operation not confirmed');
        if(get_option(self::KEY,null)!==$s&&!update_option(self::KEY,$s,false))throw new \RuntimeException('Construction journal write failed');
    }
    public static function read(): array {
        return get_option(self::KEY,['schema'=>self::SCHEMA,'source'=>home_url(),'entries'=>[]]);
    }
    private static function locked(callable $fn): mixed {
        if(!add_option(self::KEY.'_lock',wp_generate_uuid4(),'',false))throw new \RuntimeException('Construction journal busy; no inferred retry');
        try{return $fn();}finally{delete_option(self::KEY.'_lock');}
    }
    public static function begin(string $operation,array $input): int {
        return self::locked(function()use($operation,$input){
            $s=self::read();
            foreach($s['entries'] as $e)if($e['state']==='attempting')throw new \RuntimeException('An earlier construction outcome is unconfirmed');
            $n=count($s['entries'])+1;
            $contract=ConstructionContract::describe($operation,$input);
            $s['entries'][]=['sequence'=>$n,'previous'=>$n-1,'operation'=>$operation,'input'=>$input,'input_sha256'=>hash('sha256',wp_json_encode($input)),'contract'=>$contract,'contract_sha256'=>ConstructionContract::hash($contract),'state'=>'attempting'];
            self::write($s);return $n;
        });
    }
    public static function finish(int $n,array $result,bool $accepted=true): void {
        self::locked(function()use($n,$result,$accepted){
            $s=self::read();$e=$s['entries'][$n-1]??null;
            if(!$e || $e['state']!=='attempting')throw new \RuntimeException('Unexpected construction completion');
            $row=&$s['entries'][$n-1];$row['result']=$result;$row['outputs']=ConstructionContract::outputs($e['contract'],$result,$accepted);$row['state']=$accepted?'registered':'rejected';$row['completion_sha256']=ConstructionContract::hash([$row['state'],$row['result'],$row['outputs']]);unset($row);self::write($s);
        });
    }
    public static function stable(): array {
        $s=self::read();foreach($s['entries'] as $e)if($e['state']==='attempting')throw new \RuntimeException('Pending construction cannot seed an initial save');return $s;
    }
    /** A new sidecar; never alters the existing manifest/files or fabricates old operations. */
    public static function initialSaveWithAuthors(callable $capture): array {
        return self::initialSave(function()use($capture){
            [$manifest,$files]=$capture();
            return [$manifest,ConstructionInitialReferences::capture(ConstructionAuthors::capture($files))];
        });
    }
    public static function initialSave(callable $capture): array {
        $before=self::stable();[$manifest,$files]=$capture();$after=self::stable();
        if($before!==$after)throw new \RuntimeException('Construction changed during initial save; no anchor assigned');
        $hashes=[];foreach($files as $name=>$bytes)$hashes[$name]=hash('sha256',$bytes);ksort($hashes);
        return ['manifest'=>$manifest,'files'=>$files,'construction_anchor'=>[
            'schema'=>'owr-construction-anchor-experiment-5','manifest_sha256'=>hash('sha256',wp_json_encode($manifest)),
            'files_sha256'=>$hashes,'through'=>count($after['entries']),'prefix_sha256'=>hash('sha256',wp_json_encode($after)),'source'=>$after['source']]];
    }
    public static function afterInitialSave(array $anchor,array $manifest,array $files,array $journal): array {
        if(($anchor['schema']??'')!=='owr-construction-anchor-experiment-5'||($journal['schema']??'')!==self::SCHEMA)throw new \RuntimeException('Old initial save has no current operation contract; do not infer one');
        $hashes=[];foreach($files as $name=>$bytes)$hashes[$name]=hash('sha256',$bytes);ksort($hashes);
        if(hash('sha256',wp_json_encode($manifest))!==$anchor['manifest_sha256'] || $hashes!==$anchor['files_sha256'] || $journal['source']!==$anchor['source'])throw new \RuntimeException('Initial save identity changed');
        $prefix=$journal;$prefix['entries']=array_slice($journal['entries'],0,$anchor['through']);
        if(hash('sha256',wp_json_encode($prefix))!==$anchor['prefix_sha256'])throw new \RuntimeException('Initial save operation prefix changed');
        foreach($journal['entries'] as $i=>$e)if($e['sequence']!==$i+1 || $e['state']==='attempting' || hash('sha256',wp_json_encode($e['input']))!==$e['input_sha256'])throw new \RuntimeException('Unconfirmed or inconsistent operation chain');
        return array_slice($journal['entries'],$anchor['through']);
    }
}
