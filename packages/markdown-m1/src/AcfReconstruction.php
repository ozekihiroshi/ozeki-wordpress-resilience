<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Read-only selection; portable definitions are produced by ACF's own exporter. */
final class AcfReconstruction {
    public static function plan(array $manifest,array $files): array {
        $data=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        $acf=$data['acf']??null;
        if(!is_array($acf)||!AcfHistory::enabled()||acf_get_setting('version')!==($acf['version']??null))throw new \RuntimeException('Prepare the recorded ACF free version to export saved definitions.');
        $out=['schema'=>'owr-normal-acf-registration-1','source_url'=>$manifest['source_url'],'through'=>$manifest['through'],'version'=>$acf['version'],'groups'=>[],'posts'=>[],'held'=>[]];
        $fields=[];
        foreach($acf['acf_definitions'] as $g){
            $key=$g['key']??'?';
            try {
                if(!preg_match('/^group_[A-Za-z0-9_-]+$/D',$key)||!empty($g['local']))throw new \RuntimeException('Only database-defined groups supported');
                if(empty($g['location']))throw new \RuntimeException('Missing location');
                foreach($g['location'] as $and)foreach($and as $rule)if(($rule['param']??'')!=='post_type'||!in_array($rule['operator']??'',['==','!='],true)||!in_array($rule['value']??'',['post','page'],true))throw new \RuntimeException('Location requires an unverified registration operation');
                foreach($g['fields']??[] as $f){
                    if(!in_array($f['type']??'',AcfHistory::TYPES,true)||!empty($f['sub_fields']))throw new \RuntimeException('Unsupported field type');
                    if(!preg_match('/^field_[A-Za-z0-9_-]+$/D',$f['key']??'')||!preg_match('/^[A-Za-z0-9_-]+$/D',$f['name']??''))throw new \RuntimeException('Invalid field identity');
                    if(isset($fields[$f['key']]))throw new \RuntimeException('Duplicate field key');
                }
                $portable=acf_prepare_internal_post_type_for_export($g,'acf-field-group');
                $out['groups'][]=$portable;
                foreach($g['fields'] as $f)$fields[$f['key']]=$f;
            }catch(\Throwable $e){$out['held']['group:'.$key]=$e->getMessage();}
        }
        $posts=[];foreach($data['tables']['posts']??[] as $p)$posts[(string)$p['ID']]=$p;
        foreach($acf['posts']??[] as $id=>$v){
            $post=$posts[(string)$id]??null;
            if(!$post||!in_array($post['post_status']??'', ['publish','private'],true))continue;
            try {
                if(!in_array($post['post_type'],['post','page'],true)||$post['post_type']!==$v['type'])throw new \RuntimeException('Owner type mismatch');
                $values=[];
                foreach($v['acf_references'] as $name=>$key){
                    if(!isset($fields[$key])||$fields[$key]['name']!==$name)throw new \RuntimeException('Missing supported field definition: '.$name);
                    $saved=$v['acf_values'][$name]??[];
                    if(count($saved)!==1)throw new \RuntimeException('Missing or ambiguous saved value: '.$name);
                    $value=$saved[0];
                    if(!is_string($value)&&(!is_array($value)||array_filter($value,fn($x)=>!is_string($x))))throw new \RuntimeException('Unverified form input shape: '.$name);
                    $values[$key]=$value;
                }
                // No registered ACF values means no value-save operation. Empty
                // strings for actual fields remain entries and are preserved.
                if($values)$out['posts'][]=['origin_id'=>(string)$id,'type'=>$v['type'],'values'=>$values];
            }catch(\Throwable $e){$out['held']['post:'.$id]=$e->getMessage();}
        }
        // Partial definitions can change meaning; require resolution before any destination write.
        if($out['held'])$out['requires_resolution']=true;
        return $out;
    }
}
