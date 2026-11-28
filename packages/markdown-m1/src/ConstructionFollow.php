<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Strict sequence follower. Initial identities come from actual baseline registration. */
final class ConstructionFollow {
    public static function prepare(array $e,int $through,array $map,int $actor=0): array {
        $c=$e['contract']??[];
        if(($e['sequence']??null)!==$through+1||($e['previous']??null)!==$through)throw new \RuntimeException('Operation sequence gap; do not reorder');
        if(!in_array($e['state']??'', ['registered','rejected'],true))throw new \RuntimeException('Unconfirmed ordinary operation');
        if(ConstructionContract::hash([$e['state'],$e['result'],$e['outputs']])!==($e['completion_sha256']??''))throw new \RuntimeException('Changed operation completion');
        if(($c['schema']??'')!==ConstructionContract::SCHEMA||ConstructionContract::hash($c)!==($e['contract_sha256']??'')||ConstructionContract::hash($e['input'])!==$e['input_sha256'])throw new \RuntimeException('Missing or changed operation contract');
        if($e['state']==='rejected')return ['skip'=>true];
        if($c['coverage']!=='complete'||count($e['outputs'])!==($c['output_type']===null?0:1))throw new \RuntimeException('Capture incomplete; do not compensate at reconstruction');
        if(($c['completion']??'')==='media-delete'&&(empty($e['result']['response']['deleted'])||(int)($e['result']['response']['previous']['id']??0)!==(int)$c['target']['id']))throw new \RuntimeException('Deletion result does not match the recorded target');
        if(($c['completion']??'')==='option'&&!array_filter($e['result']['effects']??[],fn($x)=>$x['type']==='option'))throw new \RuntimeException('Settings completion absent');
        if(($c['completion']??'')==='acf-import'){
            $actual=[];foreach($e['result']['effects']??[] as $x)if($x['type']==='acf-import')$actual[]=$x['key'];
            $expected=$c['expected_keys'];sort($expected);sort($actual);if($expected!==$actual)throw new \RuntimeException('Definition completion absent');
        }
        return self::arguments($c,$map,$actor)+['outputs'=>$e['outputs']];
    }
    public static function initial(array $material,array $map): array {
        $c=$material['contract']??[];
        if(($c['schema']??'')!==ConstructionContract::SCHEMA||($c['coverage']??'')!=='complete'||ConstructionContract::hash($c)!==($material['contract_sha256']??'')||ConstructionContract::hash($material['input'])!==($material['input_sha256']??''))throw new \RuntimeException('Missing or changed initial content contract');
        return self::arguments($c,$map,0);
    }
    private static function arguments(array $c,array $map,int $actor): array {
        $args=$c['arguments'];
        $resolve=static function($r)use($map){
            $key=$r['type'].':'.$r['id'];if(!isset($map[$key]))throw new \RuntimeException('Missing prior registration result: '.$key);
            if($r['type']==='post'||str_starts_with($r['type'],'image-url:')){
                $deleted=!empty($map['deleted:'.$r['id']]);$sourceDeleted=($r['source_state']??'live')==='deleted';
                if($deleted!==$sourceDeleted)throw new \RuntimeException('Recorded reference lifecycle differs: '.$key);
            }
            return $map[$key];
        };
        $target=$c['target']?$resolve($c['target']):null;
        foreach($c['references'] as $r){$v=&$args;foreach($r['path'] as $key){if(!is_array($v)||!array_key_exists($key,$v))throw new \RuntimeException('Missing recorded reference path');$v=&$v[$key];}$v=$resolve($r);unset($v);}
        $spans=$c['spans']??[];foreach($c['json_spans']??[] as $r)$spans[]=$r+['json'=>true];usort($spans,fn($a,$b)=>$b['offset']<=>$a['offset']);
        foreach($spans as $r){
            $v=&$args;foreach($r['path'] as $key)$v=&$v[$key];if(!is_string($v)||substr($v,$r['offset'],$r['length'])!==$r['literal'])throw new \RuntimeException('Changed recorded embed span');
            if(!empty($r['json'])){
                $attrs=$r['value'];foreach($r['references'] as $ref){$a=&$attrs;foreach($ref['path'] as $k)$a=&$a[$k];$a=$resolve($ref);unset($a);}
                $replacement=serialize_block_attributes($attrs);
            }else $replacement=(string)$resolve($r);
            $v=substr_replace($v,$replacement,$r['offset'],$r['length']);unset($v);
        }
        if(isset($c['text_upload'])){
            $text=$args;foreach($c['text_upload']['text_path'] as $key)$text=$text[$key];
            $v=&$args;foreach($c['text_upload']['path'] as $key)$v=&$v[$key];$v=base64_encode($text);unset($v);
        }
        foreach($c['destination_actor_paths']??[] as $path){if(!$actor)throw new \RuntimeException('Prepared destination actor required');$v=&$args;foreach($path as $key)$v=&$v[$key];$v=$actor;unset($v);}
        return ['endpoint'=>$c['endpoint'],'target'=>$target,'arguments'=>$args];
    }
    /** Bind only references supplied by this ordinary registration's result. */
    public static function accept(array $entry,mixed $returned,array $map): array {
        if(($entry['contract']['endpoint']??'')==='wordpress.media-delete'){
            if($returned!==true||empty($entry['result']['response']['deleted']))throw new \RuntimeException('Deletion outcome is unconfirmed');
            $id=(string)$entry['contract']['target']['id'];$map['deleted:'.$id]=true;
            return $map;
        }
        $id=is_array($returned)?($returned['id']??null):$returned;
        foreach($entry['outputs'] as $out){
            if($out['type']==='table'?(!is_string($id)||!preg_match('/^[A-Za-z0-9_-]+$/D',$id)):(!is_int($id)||$id<1))throw new \RuntimeException('Normal result identity missing');
            $key=$out['type'].':'.$out['id'];if(isset($map[$key])&&$map[$key]!==$id)throw new \RuntimeException('Normal update changed identity');$map[$key]=$id;
            foreach($entry['result']['reference_values']??[] as $type=>$sourceValue){
                $value=is_array($returned)?($returned['reference_values'][$type]??null):null;
                if(!is_string($value)||$value==='')throw new \RuntimeException('Normal result lacks recorded reference kind: '.$type);
                $map[$type.':'.$out['id']]=$value;
            }
        }
        return $map;
    }
    public static function run(array $entries,int $through,array $identities,callable $normal): array {
        $map=$identities;$done=[];
        // Reject incomplete contracts before making any normal call.
        foreach($entries as $i=>$e){
            $c=$e['contract']??[];
            if(($e['sequence']??null)!==$through+$i+1||($e['previous']??null)!==$through+$i)throw new \RuntimeException('Operation sequence gap; do not reorder');
            if(!in_array($e['state']??'', ['registered','rejected'],true))throw new \RuntimeException('Unconfirmed ordinary operation');
            if(ConstructionContract::hash([$e['state'],$e['result'],$e['outputs']])!==($e['completion_sha256']??''))throw new \RuntimeException('Changed operation completion');
            if(($c['schema']??'')!==ConstructionContract::SCHEMA||ConstructionContract::hash($c)!==($e['contract_sha256']??'')||ConstructionContract::hash($e['input'])!==$e['input_sha256'])throw new \RuntimeException('Missing or changed operation contract');
            if($e['state']==='registered'&&($c['coverage']!=='complete'||count($e['outputs']??[])!==($c['output_type']===null?0:1)))throw new \RuntimeException('Capture incomplete; do not compensate at reconstruction');
        }
        foreach($entries as $e){
            if($e['state']==='rejected')continue;
            $c=$e['contract'];$prepared=self::prepare($e,$e['sequence']-1,$map,get_current_user_id());$args=$prepared['arguments'];$target=$prepared['target'];
            // Callback is a normal registration call, not an internal-state repair.
            $result=$normal($c['endpoint'],$target,$args);
            if($c['output_type']===null){if($result!==true)throw new \RuntimeException('Ordinary save not confirmed');$map=self::accept($e,$result,$map);$done[]=$e['sequence'];continue;}
            $map=self::accept($e,$result,$map);$done[]=$e['sequence'];
        }
        return ['identities'=>$map,'completed'=>$done];
    }
}
