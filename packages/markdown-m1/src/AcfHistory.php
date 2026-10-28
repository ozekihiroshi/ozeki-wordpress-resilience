<?php
declare(strict_types=1);
namespace Owr\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/SaveFailure.php';

/** ACF free, database-defined basic fields on posts/pages. Originals are never filtered. */
final class AcfHistory {
    public const PLUGIN='advanced-custom-fields/acf.php';
    public const TYPES=['text','textarea','number','range','email','url','select','checkbox','radio','button_group','true_false','date_picker','date_time_picker','time_picker','color_picker'];
    private array $dirty=[];
    public static function enabled(): bool {return function_exists('acf_get_field_groups')&&!(defined('ACF_PRO')&&ACF_PRO)&&in_array(self::PLUGIN,(array)get_option('active_plugins'),true);}
    public function boot(): void {
        add_action('wp_after_insert_post',fn($id)=>$this->mark((int)$id),PHP_INT_MAX,1);
        add_action('acf/save_post',function($id){if(is_numeric($id))$this->mark((int)$id);},30);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)
            add_action($hook,function($mid,$id,$key){if(!str_starts_with((string)$key,'_owr_'))$this->mark((int)$id);},PHP_INT_MAX,3);
        add_action('deleted_post',function($id){unset($this->dirty[(int)$id]);});
        add_action('shutdown',[$this,'flush'],PHP_INT_MAX);
    }
    private function mark(int $id): void {
        if(!self::enabled()||empty((new Plugin())->config()['protect']))return;
        $p=get_post($id);
        if($p&&in_array($p->post_type,['post','page'],true)&&($p->post_status==='publish'||get_post_meta($id,'_owr_m1_asset',true)))$this->dirty[$id]=true;
    }
    public static function capture(int $id): array {
        global $wpdb;
        $post=get_post($id);
        if(!$post||!in_array($post->post_type,['post','page'],true))throw new \RuntimeException('Invalid ACF owner.');
        $groups=[];
        foreach(acf_get_field_groups() as $g){$g['fields']=acf_get_fields($g)?:[];$groups[]=$g;}
        $rows=$wpdb->get_results($wpdb->prepare("SELECT meta_key,meta_value FROM {$wpdb->postmeta} WHERE post_id=%d ORDER BY meta_id",$id),ARRAY_A);
        if($wpdb->last_error)throw new \RuntimeException('Cannot freeze ACF values.');
        $raw=[];$references=[];$values=[];
        foreach($rows as $row){$key=$row['meta_key'];if(in_array($key,['_edit_lock','_edit_last'],true)||str_starts_with($key,'_owr_'))continue;$raw[$key][]=$row['meta_value'];
            if(str_starts_with($key,'_')&&preg_match('/^field_[A-Za-z0-9_-]+$/D',$row['meta_value']))$references[substr($key,1)]=$row['meta_value'];
        }
        foreach($references as $name=>$key){
            if(count($raw['_'.$name])!==1)throw new \RuntimeException('Ambiguous ACF field reference.');
            if(isset($raw[$name]))foreach($raw[$name] as $v){
            $decoded=is_serialized($v)?@unserialize($v,['allowed_classes'=>false]):$v;
            // Unrecognized object encodings remain opaque bytes; never instantiate or discard them.
            $values[$name][]=self::plain($decoded)?$decoded:$v;
        }}
        return ['schema'=>'owr-acf-1','id'=>$id,'type'=>$post->post_type,'version'=>acf_get_setting('version'),
            'acf_values'=>$values,'acf_definitions'=>$groups,'acf_references'=>$references,'raw_meta'=>$raw];
    }
    public static function baseline(array &$data): void {
        if(!self::enabled())return;
        foreach($data['tables']['posts'] as $post)if(in_array($post['post_type'],['post','page'],true))
            self::replay($data,Store::json(self::capture((int)$post['ID'])),['origin_id'=>(int)$post['ID']]);
    }
    public function flush(): void {
        foreach(array_keys($this->dirty) as $id){
            SaveFailure::run('ACF completed field save',function()use($id){
                $v=self::capture($id);
                (new CommentHistory())->enqueue('acf-'.$id,Store::json($v),['post_type'=>'owr_acf','content_format'=>'acf-json','origin_id'=>$id,'title'=>'ACF fields #'.$id,'status'=>'saved']);
            });
            unset($this->dirty[$id]);
        }
    }
    private static function plain(mixed $v): bool {
        if(is_array($v)){foreach($v as $x)if(!self::plain($x))return false;return true;}
        return is_scalar($v)||$v===null;
    }
    public static function replay(array &$data,string $source,array $attributes): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);
        if(($v['schema']??'')!=='owr-acf-1'||!is_int($v['id']??null)||$v['id']<=0||$v['id']!==(int)$attributes['origin_id']||!in_array($v['type']??'',['post','page'],true))throw new \RuntimeException('Invalid ACF identity.');
        foreach(['acf_values','acf_definitions','acf_references','raw_meta'] as $key)if(!is_array($v[$key]??null))throw new \RuntimeException('Invalid ACF original.');
        $found=false;foreach($data['tables']['posts'] as $p)if((int)$p['ID']===$v['id']&&$p['post_type']===$v['type'])$found=true;
        if(!$found)throw new \RuntimeException('ACF owner is absent from confirmed site state.');
        $data['acf']['version']=$v['version'];$data['acf']['acf_definitions']=$v['acf_definitions'];
        $data['acf']['posts'][(string)$v['id']]=$v;
    }
    /** Prepare recognized definitions and values without touching the preserved state. */
    public static function project(array $data): array {
        $out=['groups'=>[],'meta'=>[],'skipped'=>[],'keys'=>[]];
        if(!isset($data['acf']))return $out;
        $omit=function($item,$reason)use(&$out){$out['skipped'][]=['item'=>$item,'reason'=>$reason];};
        $fields=[];
        foreach($data['acf']['acf_definitions'] as $g){
            $path='acf.definition.'.($g['key']??'?');
            if(!preg_match('/^group_[A-Za-z0-9_-]+$/D',$g['key']??'')||!empty($g['local'])){$omit($path,'Only database-defined groups are applied');continue;}
            $location=$g['location']??[];$valid=(bool)$location;
            foreach($location as $and){if(!is_array($and)||!$and){$valid=false;break;}foreach($and as $r)if(($r['param']??'')!=='post_type'||!in_array($r['operator']??'',['==','!='],true)||!in_array($r['value']??'',['post','page'],true))$valid=false;}
            if(!$valid){$omit($path.'.location','Only post/page post_type location rules are applied');continue;}
            $group=['key'=>$g['key'],'title'=>(string)$g['title'],'location'=>$location,'active'=>(bool)($g['active']??true),'fields'=>[]];
            foreach($g['fields']??[] as $f){
                $fp=$path.'.'.($f['key']??'?');
                if(!in_array($f['type']??'',self::TYPES,true)){$omit($fp,'Unsupported ACF field type; original retained');continue;}
                if(!preg_match('/^field_[A-Za-z0-9_-]+$/D',$f['key']??'')||!preg_match('/^[A-Za-z][A-Za-z0-9_]*$/D',$f['name']??''))throw new \RuntimeException('Invalid recognized ACF field identity.');
                $allowed=['key','name','label','type','required','default_value','choices','multiple','allow_null','return_format','min','max','step','maxlength','placeholder','prepend','append','rows','new_lines','display_format','return_format','first_day','ui','message','ui_on_text','ui_off_text','layout','toggle','allow_custom','save_custom','menu_order'];
                $field=[];foreach($f as $k=>$value){if(in_array($k,$allowed,true)){
                    if(!self::plain($value)||(!in_array($k,['default_value','choices'],true)&&!is_scalar($value)&&$value!==null))throw new \RuntimeException('Invalid ACF setting.');
                    if($k==='choices'&&(!is_array($value)||array_filter($value,fn($x)=>!is_string($x))))throw new \RuntimeException('Invalid ACF choices.');
                    $field[$k]=$value;}
                    elseif(!in_array($k,['ID','parent','prefix','_name','_valid'],true))$omit($fp.'.'.$k,'Setting outside basic-field application rules');}
                if(isset($fields[$field['key']]))throw new \RuntimeException('Duplicate ACF field key.');
                $fields[$field['key']]=$field;$group['fields'][]=$field;
            }
            foreach($g as $k=>$v)if(!in_array($k,['ID','key','title','location','active','fields','local','local_file','modified','_valid'],true))$omit($path.'.'.$k,'Group setting outside basic-field application rules');
            $out['groups'][]=$group;
        }
        $posts=[];foreach($data['tables']['posts'] as $p)$posts[(string)$p['ID']]=$p['post_type'];
        foreach($data['acf']['posts'] as $id=>$v){
            if(!isset($posts[(string)$id]))continue; // Confirmed native deletion removed the owner.
            if($posts[(string)$id]!==$v['type'])throw new \RuntimeException('ACF owner type conflict.');
            foreach($v['acf_references'] as $name=>$key){
                $path='acf.post.'.$id.'.'.$name;$out['keys'][(string)$id][$name]=true;$out['keys'][(string)$id]['_'.$name]=true;
                $field=$fields[$key]??null;
                if(!$field||$field['name']!==$name){$omit($path,'No recognized matching field definition');continue;}
                $values=$v['acf_values'][$name]??[];
                if(count($values)>1)throw new \RuntimeException('Ambiguous ACF value: '.$path);
                foreach($values as $value){
                    $list=in_array($field['type'],['checkbox'],true)||($field['type']==='select'&&!empty($field['multiple']));
                    if($list){if($value!==''&&$value!==false&&(!is_array($value)||array_filter($value,fn($x)=>!is_string($x))))throw new \RuntimeException('Invalid ACF selection: '.$path);}
                    elseif(!is_scalar($value)&&$value!==null)throw new \RuntimeException('Invalid ACF scalar: '.$path);
                    if(in_array($field['type'],['number','range'],true)&&$value!==''&&$value!==null&&!is_numeric($value))throw new \RuntimeException('Invalid ACF number: '.$path);
                    if($field['type']==='true_false'&&!in_array($value,['0','1',0,1,false,true,''],true))throw new \RuntimeException('Invalid ACF boolean: '.$path);
                    $out['meta'][]=['post_id'=>(string)$id,'meta_key'=>$name,'meta_value'=>is_array($value)?serialize($value):(string)$value];
                }
                if($values)$out['meta'][]=['post_id'=>(string)$id,'meta_key'=>'_'.$name,'meta_value'=>$key];
            }
        }
        return $out;
    }
    public static function check(array $data): void {
        if(!isset($data['acf']))return;
        if(!self::enabled()||acf_get_setting('version')!==$data['acf']['version'])throw new \RuntimeException('Activate the recorded ACF free version before recovery.');
    }
    public static function install(array $groups): void {
        global $wpdb;
        if($groups)acf_get_store('fields')->reset();
        foreach($groups as $group){
            $wpdb->last_error='';$saved=acf_import_field_group($group);
            if(!$saved||empty($saved['ID'])||$wpdb->last_error)throw new \RuntimeException('ACF definition import failed.');
            foreach($group['fields'] as $f){
                $row=$wpdb->get_row($wpdb->prepare("SELECT post_excerpt FROM {$wpdb->posts} WHERE post_type='acf-field' AND post_name=%s",$f['key']),ARRAY_A);
                if(!$row||$row['post_excerpt']!==$f['name'])throw new \RuntimeException('ACF field definition was not persisted.');
            }
        }
    }
}
