<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionEmbeds.php';
require_once __DIR__.'/ConstructionPluginContract.php';

/** Recorded BEFORE the ordinary handler. Replay never infers the meaning of numbers. */
final class ConstructionContract {
    public const SCHEMA='owr-construction-contract-5';
    public static function describe(string $operation,array $input): array {
        $c=['schema'=>self::SCHEMA,'coverage'=>'incomplete','reasons'=>[],'endpoint'=>null,'target'=>null,'arguments'=>$input['body']??[],'references'=>[],'spans'=>[],'output_type'=>null];
        if($operation==='rest'&&($input['method']??'POST')==='DELETE'&&!preg_match('~^/wp/v2/media/[1-9][0-9]*$~D',$input['route']??'')){$c['reasons'][]='No source deletion contract for this route';return $c;}
        if($operation!=='rest'||!preg_match('~^/wp/v2/(posts|pages)(?:/([1-9][0-9]*))?$~D',$input['route']??'',$m)){
            return ConstructionPluginContract::describe($operation,$input,$c);
        }
        $c['endpoint']='/wp/v2/'.$m[1];$c['output_type']='post';
        if(isset($m[2]))$c['target']=['type'=>'post','id'=>(int)$m[2]];
        $allowed=['title','content','excerpt','status','slug','date','date_gmt','password','author','parent','featured_media','categories','tags','comment_status','ping_status','menu_order'];
        foreach(array_keys($c['arguments']) as $k)if(!in_array($k,$allowed,true))$c['reasons'][]='Unspecified input field: '.$k;
        if(!$c['target']&&!isset($c['arguments']['author'])){
            if(empty($input['actor']))$c['reasons'][]='Missing actor for the normal default author';
            else $c['arguments']['author']=$input['actor']; // Raw input remains untouched.
        }
        foreach(['author'=>'user','parent'=>'post','featured_media'=>'post'] as $key=>$type)if(isset($c['arguments'][$key])){
            $id=$c['arguments'][$key];
            if(!ctype_digit((string)$id)){$c['reasons'][]='Invalid reference: '.$key;continue;}
            if((int)$id)$c['references'][]=['path'=>[$key],'type'=>$type,'id'=>(int)$id];
        }
        foreach(['categories'=>'category','tags'=>'tag'] as $key=>$type)if(isset($c['arguments'][$key])){
            if(!is_array($c['arguments'][$key])){$c['reasons'][]='Invalid reference list: '.$key;continue;}
            foreach($c['arguments'][$key] as $i=>$id){
                if(!ctype_digit((string)$id)||(int)$id<1){$c['reasons'][]='Invalid term reference';continue;}
                $c['references'][]=['path'=>[$key,$i],'type'=>$type,'id'=>(int)$id];
            }
        }
        foreach(['content','excerpt'] as $key)if(isset($c['arguments'][$key])){
            $s=$c['arguments'][$key];if(!is_string($s)){$c['reasons'][]='Non-text content';continue;}
            ConstructionEmbeds::capture($s,[$key],$c);
        }
        if(!$c['reasons'])$c['coverage']='complete';
        return $c;
    }
    public static function outputs(array $contract,array $result,bool $accepted): array {
        if(!$accepted)return [];
        if($contract['coverage']!=='complete'||$contract['output_type']===null)return [];
        $id=$result['response']['id']??null;
        $endpoint=$contract['endpoint'];
        if($endpoint==='flamingo.add')$id=$result['id']??null;
        if($endpoint==='tablepress.import'){
            parse_str(parse_url($result['redirect']??'',PHP_URL_QUERY)??'',$q);
            if(($q['message']??'')==='success_import'&&!is_array($q['table_id']??null))$id=$q['table_id']??null;
        }
        if(in_array($endpoint,['markdown.import','wordpress.edit','members.create','members.profile'],true)){
            $ids=[];foreach($result['effects']??[] as $e){
                $wanted=$contract['output_type']==='user'?'user':'post';
                if(($e['type']??'')!==$wanted||($e['post_type']??'')==='revision')continue;
                if($endpoint==='markdown.import'&&($e['post_type']??'')!=='ozmd_document')continue;
                $ids[(string)$e['id']]=$e['id'];
            }
            if(count($ids)===1)$id=reset($ids);
        }
        if($endpoint==='tablepress.save')foreach($result['effects']??[] as $e)if(($e['type']??'')==='table-saved')$id=$e['id'];
        if($id===null||$id==='')return [];
        $id=$contract['output_type']==='table'?(string)$id:(int)$id;
        if($contract['target']&&($contract['result_mode']??'update')!=='create'&&(string)$contract['target']['id']!==(string)$id)return [];
        return [['type'=>$contract['output_type'],'id'=>$id]];
    }
    public static function hash(array $value): string {return hash('sha256',wp_json_encode($value));}
}
