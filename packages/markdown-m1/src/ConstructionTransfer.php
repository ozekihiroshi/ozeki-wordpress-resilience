<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionOperations.php';

/** Separate experimental stream: old originals/history are never changed or reinterpreted. */
final class ConstructionTransfer {
    public function __construct(private Store $store){}
    public function flush(array $packet,array $journal): array {
        ConstructionOperations::afterInitialSave($packet['construction_anchor'],$packet['manifest'],$packet['files'],$journal);
        $base='construction-experiment/'.hash('sha256',Store::json($packet['construction_anchor'])).'/';
        $files=[];
        foreach($packet['files'] as $name=>$body){
            SiteSnapshot::safePath($name);
            $files[$name]=$this->store->put($base.'initial/files/'.hash('sha256',$name),$body,'application/octet-stream');
            if($this->store->get($files[$name])!==$body)throw new \RuntimeException('Initial material read-back differs');
        }
        $initial=['schema'=>'owr-construction-initial-experiment-1','manifest'=>$packet['manifest'],'files'=>$files,'anchor'=>$packet['construction_anchor']];
        $initialRef=$this->store->put($base.'initial.json',Store::json($initial),'application/json');
        $this->store->get($initialRef);$refs=[];
        foreach($journal['entries'] as $e){
            if(!in_array($e['state'],['registered','rejected'],true))throw new \RuntimeException('Unconfirmed operation');
            $original=$this->store->put($base.sprintf('inputs/%020d.json',$e['sequence']),Store::json($e),'application/json');
            $this->store->get($original);
            $row=['schema'=>'owr-construction-history-experiment-1','sequence'=>$e['sequence'],'source'=>$journal['source'],'original'=>$original];
            $refs[]=$this->store->put($base.sprintf('history/%020d.json',$e['sequence']),Store::json($row),'application/json');
            $this->store->get(end($refs));
        }
        // Only a final, versioned commit makes the exact selected range readable.
        $commit=['schema'=>'owr-construction-commit-experiment-1','initial'=>$initialRef,'operations'=>$refs,'source'=>$journal['source']];
        $ref=$this->store->put($base.'commits/'.hash('sha256',Store::json($commit)).'.json',Store::json($commit),'application/json');
        $this->load($ref);return $ref;
    }
    public function load(array $ref): array {
        $c=json_decode($this->store->get($ref),true,512,JSON_THROW_ON_ERROR);
        if(($c['schema']??'')!=='owr-construction-commit-experiment-1')throw new \RuntimeException('Unknown construction commit');
        $i=json_decode($this->store->get($c['initial']),true,512,JSON_THROW_ON_ERROR);
        if(($i['schema']??'')!=='owr-construction-initial-experiment-1')throw new \RuntimeException('Unknown initial material');
        $files=[];foreach($i['files'] as $name=>$file){SiteSnapshot::safePath($name);$files[$name]=$this->store->get($file);}
        $j=['schema'=>ConstructionOperations::SCHEMA,'source'=>$c['source'],'entries'=>[]];
        foreach($c['operations'] as $index=>$op){
            $row=json_decode($this->store->get($op),true,512,JSON_THROW_ON_ERROR);
            if(($row['schema']??'')!=='owr-construction-history-experiment-1'||$row['sequence']!==$index+1||$row['source']!==$c['source'])throw new \RuntimeException('Operation history gap');
            $e=json_decode($this->store->get($row['original']),true,512,JSON_THROW_ON_ERROR);
            if($e['sequence']!==$row['sequence'])throw new \RuntimeException('Operation identity mismatch');$j['entries'][]=$e;
        }
        $tail=ConstructionOperations::afterInitialSave($i['anchor'],$i['manifest'],$files,$j);
        return ['manifest'=>$i['manifest'],'files'=>$files,'anchor'=>$i['anchor'],'journal'=>$j,'tail'=>$tail];
    }
}
