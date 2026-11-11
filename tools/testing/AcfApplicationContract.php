<?php
declare(strict_types=1);

/** Development-only requirements for normal, supported ACF free originals. */
final class AcfApplicationContract
{
    public const TYPES=['text','textarea','number','range','email','url','select','checkbox','radio','button_group','true_false','date_picker','date_time_picker','time_picker','color_picker'];
    public const FIELD=['key','name','label','type','required','default_value','choices','multiple','allow_null','return_format','min','max','step','maxlength','placeholder','prepend','append','rows','new_lines','display_format','first_day','ui','message','ui_on_text','ui_off_text','layout','toggle','allow_custom','save_custom','menu_order'];
    public const GROUP=['key','title','location','active'];

    public static function expected(array $state): array {
        $out=['groups'=>[],'posts'=>[]];$fields=[];
        foreach($state['acf']['acf_definitions'] as $group){
            if(!empty($group['local']))throw new RuntimeException('Fixture contains local group');
            $g=[];foreach(self::GROUP as $key){if(!array_key_exists($key,$group))throw new RuntimeException('Incomplete group fixture');$g[$key]=$group[$key];}
            $g['fields']=[];
            foreach($group['fields'] as $field){
                if(!in_array($field['type'],self::TYPES,true))throw new RuntimeException('Fixture contains unsupported field');
                $f=[];foreach(self::FIELD as $key)if(array_key_exists($key,$field))$f[$key]=$field[$key];
                if(isset($fields[$f['key']]))throw new RuntimeException('Duplicate field identity');
                $fields[$f['key']]=$f;$g['fields'][$f['key']]=$f;
            }
            $out['groups'][$g['key']]=$g;
        }
        $owners=[];foreach($state['tables']['posts'] as $post)$owners[(string)$post['ID']]=$post['post_type'];
        foreach($state['acf']['posts'] as $id=>$post){
            if(!isset($owners[(string)$id]))continue;
            if($owners[(string)$id]!==$post['type'])throw new RuntimeException('Owner type mismatch');
            $meta=[];
            foreach($post['acf_references'] as $name=>$key){
                if(!isset($fields[$key])||$fields[$key]['name']!==$name)throw new RuntimeException('Fixture contains unmatched reference');
                $values=$post['acf_values'][$name]??[];
                if(count($values)>1)throw new RuntimeException('Ambiguous fixture value');
                if($values){
                    $v=$values[0];
                    $meta[$name]=[is_array($v)?$v:(string)$v];
                    $meta['_'.$name]=[$key];
                }else{$meta[$name]=[];$meta['_'.$name]=[];}
            }
            $out['posts'][$id]=['type'=>$post['type'],'meta'=>$meta];
        }
        return $out;
    }
    public static function differences(mixed $expected,mixed $actual,string $path='acf'): array {
        $errors=[];
        if(is_array($expected)&&is_array($actual)){
            foreach($expected as $key=>$value){
                if(!array_key_exists($key,$actual))$errors[]=['code'=>'missing','path'=>$path.'.'.$key];
                else $errors=array_merge($errors,self::differences($value,$actual[$key],$path.'.'.$key));
            }
            foreach($actual as $key=>$value)if(!array_key_exists($key,$expected))$errors[]=['code'=>'unexpected','path'=>$path.'.'.$key];
        }elseif($expected!==$actual)$errors[]=['code'=>'changed','path'=>$path];
        return $errors;
    }
    /** Observe declared requirements directly; never call the product projector. */
    public static function observe(array $expected): array {
        $out=['groups'=>[],'posts'=>[]];
        foreach(acf_get_field_groups() as $group){
            $g=[];foreach(self::GROUP as $key)if(array_key_exists($key,$group))$g[$key]=$group[$key];
            $g['fields']=[];
            foreach(acf_get_fields($group)?:[] as $field){
                $f=[];foreach(self::FIELD as $key)if(array_key_exists($key,$field))$f[$key]=$field[$key];
                if(isset($g['fields'][$field['key']]))throw new RuntimeException('Duplicate observed field');
                $g['fields'][$field['key']]=$f;
            }
            $out['groups'][$group['key']]=$g;
        }
        foreach($expected['posts'] as $id=>$post){
            $meta=[];foreach($post['meta'] as $key=>$value)$meta[$key]=get_post_meta((int)$id,$key,false);
            $out['posts'][$id]=['type'=>get_post_type((int)$id),'meta'=>$meta];
        }
        return $out;
    }
}
