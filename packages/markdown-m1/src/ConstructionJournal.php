<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Local persistence only. The existing exported experiment schema is unchanged. */
final class ConstructionJournal {
    public const KEY='ozeki_resilience_construction_local_v1';
    public static function enabled(): bool {return defined('OWR_CONSTRUCTION_PERSISTENT')&&OWR_CONSTRUCTION_PERSISTENT===true;}
    private static function immutable(string $key,array $value): void {
        $raw=wp_json_encode($value);
        if($raw===false||strlen($raw)>8*1024*1024)throw new \RuntimeException('Construction record exceeds current local limit');
        $old=get_option($key,null);
        if($old!==null){if($old!==$value)throw new \RuntimeException('Construction record already differs');return;}
        if(!add_option($key,$value,'',false)||get_option($key,null)!==$value)throw new \RuntimeException('Construction durable write failed');
    }
    public static function gap(string $reason,array $identity=[]): void {
        // First cause survives subsequent requests, retries and plugin reactivation.
        $key=self::KEY.'_gap';
        if(get_option($key,null)!==null)return;
        $value=['reason'=>$reason,'identity'=>$identity,'at'=>gmdate('c')];
        if(!add_option($key,$value,'',false)&&get_option($key,null)===null)throw new \RuntimeException('Cannot persist construction interruption');
    }
    public static function assertContinuous(): void {
        if(get_option(self::KEY.'_gap',null)!==null)throw new \RuntimeException('Construction preservation gap; explicit resolution required');
    }
    public static function read(): array {
        if(get_option(ConstructionOperations::KEY,[])!==[])throw new \RuntimeException('Existing experimental journal requires a separate fresh environment; no automatic conversion');
        $head=get_option(self::KEY,null);
        if($head===null)$head=['schema'=>ConstructionOperations::SCHEMA,'source'=>home_url(),'count'=>0];
        if(($head['schema']??'')!==ConstructionOperations::SCHEMA||!is_int($head['count']??null)||$head['count']<0||!is_string($head['source']??null))throw new \RuntimeException('Invalid construction head');
        $out=['schema'=>$head['schema'],'source'=>$head['source'],'entries'=>[]];
        for($n=1;$n<=$head['count'];$n++){
            $e=get_option(self::KEY.'_input_'.$n,null);
            if(!is_array($e)||($e['sequence']??0)!==$n||($e['previous']??-1)!==$n-1||($e['state']??'')!=='attempting'||ConstructionContract::hash($e['contract']??[])!==($e['contract_sha256']??'')||hash('sha256',wp_json_encode($e['input']??null))!==($e['input_sha256']??''))throw new \RuntimeException('Missing or changed construction input');
            $r=get_option(self::KEY.'_result_'.$n,null);
            if($r!==null){
                if(!is_array($r)||array_diff(array_keys($r),['state','result','outputs','completion_sha256'])||!in_array($r['state']??'',['registered','rejected'],true)||ConstructionContract::hash([$r['state'],$r['result']??null,$r['outputs']??null])!==($r['completion_sha256']??''))throw new \RuntimeException('Changed construction completion');
                $e=array_replace($e,$r);
            }
            $out['entries'][]=$e;
        }
        if(get_option(self::KEY.'_input_'.($head['count']+1),null)!==null)throw new \RuntimeException('Construction head update interrupted; no inferred retry');
        return $out;
    }
    public static function write(array $next): void {
        $old=self::read();$count=count($old['entries']);$newCount=count($next['entries']);
        if($next['source']!==$old['source']||$next['schema']!==$old['schema']||$newCount<$count||$newCount>$count+1)throw new \RuntimeException('Construction sequence changed');
        for($i=0;$i<$count;$i++){
            $before=$old['entries'][$i];$after=$next['entries'][$i];if($before===$after)continue;
            $base=$after;foreach(['result','outputs','completion_sha256'] as $k)unset($base[$k]);$base['state']='attempting';
            if($before['state']!=='attempting'||$base!==$before||!in_array($after['state'],['registered','rejected'],true))throw new \RuntimeException('Construction input/result overwrite refused');
            self::immutable(self::KEY.'_result_'.($i+1),array_intersect_key($after,array_flip(['state','result','outputs','completion_sha256'])));
        }
        if($newCount>$count){
            $raw=wp_json_encode($next['entries'][$count]);
            if($raw===false||strlen($raw)>8*1024*1024)throw new \RuntimeException('Construction single operation exceeds current limit');
            self::immutable(self::KEY.'_input_'.$newCount,$next['entries'][$count]);
            $head=['schema'=>$next['schema'],'source'=>$next['source'],'count'=>$newCount];
            if(!update_option(self::KEY,$head,false)||get_option(self::KEY,null)!==$head)throw new \RuntimeException('Construction head write failed');
        }
    }
    public static function status(): array {
        $gap=get_option(self::KEY.'_gap',null);
        try{$j=self::read();}catch(\Throwable $e){return ['state'=>'record_error','count'=>null,'gap'=>$gap];}
        $pending=0;$unsupported=0;
        foreach($j['entries'] as $e){$pending+=(int)($e['state']==='attempting');$unsupported+=(int)($e['state']!=='rejected'&&($e['contract']['coverage']??'')!=='complete');}
        $locked=get_option(ConstructionOperations::KEY.'_lock',null)!==null;
        return ['state'=>$gap?'gap':($locked?'writer_busy_or_interrupted':($pending?'outcome_unknown':($unsupported?'unsupported':(count($j['entries'])?'transfer_pending':'not_started')))),'count'=>count($j['entries']),'pending'=>$pending,'unsupported'=>$unsupported,'gap'=>$gap];
    }
}
