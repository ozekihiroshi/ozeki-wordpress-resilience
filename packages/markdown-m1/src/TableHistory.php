<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/SaveFailure.php';

/** TablePress completed operations, complete table originals, shared S3 history. */
final class TableHistory
{
    public static function recoveryMeta(): array {
        return ['_tablepress_table_options'=>['last_editor'=>'number','table_head'=>'number','table_foot'=>'number','alternating_row_colors'=>'bool','row_hover'=>'bool','print_name'=>'bool','print_name_position'=>'text','print_description'=>'bool','print_description_position'=>'text','extra_css_classes'=>'text','use_datatables'=>'bool','datatables_sort'=>'bool','datatables_filter'=>'bool','datatables_paginate'=>'bool','datatables_lengthchange'=>'bool','datatables_paginate_entries'=>'number','datatables_info'=>'bool','datatables_scrollx'=>'bool'], '_tablepress_table_visibility'=>['rows'=>'number-map','columns'=>'number-map']];
    }
    public static function recoveryOptions(): array {
        return ['tablepress_tables'=>['table_post'=>'number-map','last_id'=>'number'], 'tablepress_plugin_options'=>['plugin_options_db_version'=>'number','table_scheme_db_version'=>'number','prev_tablepress_version'=>'text','tablepress_version'=>'text','first_activation'=>'number']];
    }

    public const PLUGIN='tablepress/tablepress.php';
    public const OPTIONS=['tablepress_tables','tablepress_plugin_options'];
    public static function enabled(): bool {return class_exists('TablePress')&&in_array(self::PLUGIN,(array)get_option('active_plugins'),true);}
    public function boot(): void {
        foreach(['added','saved','copied'] as $event)add_action('tablepress_event_'.$event.'_table',fn($id)=>$this->capture('table',(string)$id),PHP_INT_MIN,1);
        add_action('tablepress_event_deleted_table',fn($id)=>$this->capture('delete',(string)$id),PHP_INT_MIN,1);
        add_action('tablepress_event_changed_table_id',fn($id,$old)=>$this->capture('table',(string)$id,(string)$old),PHP_INT_MIN,2);
        add_action('tablepress_event_deleted_all_tables',fn()=>$this->capture('clear'),PHP_INT_MIN);
        add_action('added_option',function($name,$value){if($name==='tablepress_plugin_options')$this->capture('settings','', '',$value);},PHP_INT_MIN,2);
        add_action('updated_option',function($name,$old,$value){if($name==='tablepress_plugin_options')$this->capture('settings','', '',$value);},PHP_INT_MIN,3);
    }
    private static function object(string $raw): array {
        $v=json_decode($raw,true,512,JSON_THROW_ON_ERROR);if(!is_array($v))throw new \RuntimeException('Invalid TablePress JSON.');return $v;
    }
    private static function id(string $id): void {if($id===''||$id==='0'||preg_match('/[^a-zA-Z0-9_-]/',$id))throw new \RuntimeException('Invalid TablePress ID.');}
    public static function baseline(array &$data): void {
        foreach(self::OPTIONS as $key){$value=get_option($key);if($value===false){$value=Store::json($key==='tablepress_tables'?\TablePress::$model_table->_debug_get_tables():\TablePress::$model_options->_debug_get_plugin_options());}if(!is_string($value))throw new \RuntimeException('Invalid TablePress settings.');self::object($value);$data['options'][$key]=$value;}
        // Render caches are derived and must never hide a newly restored table.
        $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($m)=>!str_starts_with($m['meta_key'],'_tablepress_cache')));
    }
    public function capture(string $kind,string $id='',string $old='',mixed $settings=null): void {
        SaveFailure::run('Table capture',fn()=>$this->captureOperation($kind,$id,$old,$settings));
    }
    private function captureOperation(string $kind,string $id='',string $old='',mixed $settings=null): void {
        if(!self::enabled()||empty((new Plugin())->config()['protect']))return;
        global $wpdb;
        $v=['schema'=>'owr-table-1','kind'=>$kind,'id'=>$id,'old_id'=>$old,'version'=>\TablePress::version];
        if($kind==='settings'){$v['settings']=(string)$settings;self::object($v['settings']);}
        elseif($kind!=='clear'){
            self::id($id);$map=self::object((string)get_option('tablepress_tables'));$v['last_id']=(int)$map['last_id'];
            if($kind==='table'){
                $pid=(int)($map['table_post'][$id]??0);
                $post=$wpdb->get_row($wpdb->prepare('SELECT * FROM '.$wpdb->posts.' WHERE ID=%d',$pid),ARRAY_A);
                if(!$post||$post['post_type']!=='tablepress_table')throw new \RuntimeException('Missing completed TablePress table.');
                $meta=$wpdb->get_results($wpdb->prepare('SELECT meta_key,meta_value FROM '.$wpdb->postmeta.' WHERE post_id=%d ORDER BY meta_id',$pid),ARRAY_A);
                if($wpdb->last_error)throw new \RuntimeException('Cannot read TablePress metadata.');
                $v['post']=$post;$v['meta']=array_values(array_filter($meta,fn($m)=>in_array($m['meta_key'],['_tablepress_table_options','_tablepress_table_visibility'],true)));
            }
        }
        $attrs=['post_type'=>'owr_table','content_format'=>'table-json','origin_id'=>$id,'title'=>'TablePress '.($id?:$kind),'status'=>in_array($kind,['delete','clear'],true)?'deleted':'saved','tablepress_version'=>\TablePress::version];
        (new CommentHistory())->enqueue('tablepress-'.($id!==''?'table-'.$id:$kind),Store::json($v),$attrs);
    }
    public static function replay(array &$data,string $source,array $attributes): void {
        $v=self::object($source);$kind=$v['kind']??'';$id=$v['id']??'';
        if(($v['schema']??'')!=='owr-table-1'||!in_array($kind,['table','delete','clear','settings'],true)||$id!==($attributes['origin_id']??null)||($v['version']??'')!==($attributes['tablepress_version']??null))throw new \RuntimeException('Invalid TablePress history.');
        if(!isset($data['options']['tablepress_tables'],$data['options']['tablepress_plugin_options']))throw new \RuntimeException('Create a baseline with TablePress active before table recovery.');
        $map=self::object($data['options']['tablepress_tables']);
        if(!isset($map['table_post'],$map['last_id'])||!is_array($map['table_post']))throw new \RuntimeException('Invalid TablePress registry.');
        if($kind==='settings'){self::object($v['settings']);$data['options']['tablepress_plugin_options']=$v['settings'];return;}
        $removed=[];
        if($kind==='clear'){$removed=array_values($map['table_post']);$map['table_post']=[];}
        else {
            self::id($id);$map['last_id']=max((int)$map['last_id'],(int)$v['last_id']);
            if($kind==='delete'){if(isset($map['table_post'][$id]))$removed[]=$map['table_post'][$id];unset($map['table_post'][$id]);}
            else {
                $p=$v['post']??[];$pid=(int)($p['ID']??0);$old=$v['old_id']??'';
                if($pid<=0||($p['post_type']??'')!=='tablepress_table'||!is_array($v['meta']??null))throw new \RuntimeException('Invalid TablePress record.');
                self::object($p['post_content']);
                foreach($data['tables']['posts'] as $existing)if((int)$existing['ID']===$pid&&$existing['post_type']!=='tablepress_table')throw new \RuntimeException('TablePress post identity conflict.');
                if(isset($map['table_post'][$id])&&(int)$map['table_post'][$id]!==$pid)throw new \RuntimeException('TablePress ID conflict.');
                if($old!==''){self::id($old);if(isset($map['table_post'][$old])&&(int)$map['table_post'][$old]!==$pid)throw new \RuntimeException('TablePress old ID conflict.');unset($map['table_post'][$old]);}
                foreach($map['table_post'] as $key=>$value)if((string)$key!==$id&&(int)$value===$pid)throw new \RuntimeException('Duplicate TablePress post identity.');
                $map['table_post'][$id]=$pid;
                $data['tables']['posts']=array_values(array_filter($data['tables']['posts'],fn($row)=>(int)$row['ID']!==$pid));$data['tables']['posts'][]=$p;
                $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($row)=>(int)$row['post_id']!==$pid));
                $next=max(array_merge([0],array_map('intval',array_column($data['tables']['postmeta'],'meta_id'))))+1;
                $keys=[];foreach($v['meta'] as $meta){
                    if(!in_array($meta['meta_key'],['_tablepress_table_options','_tablepress_table_visibility'],true)||isset($keys[$meta['meta_key']]))throw new \RuntimeException('Invalid TablePress metadata.');
                    self::object($meta['meta_value']);$keys[$meta['meta_key']]=true;
                    $data['tables']['postmeta'][]=['meta_id'=>(string)$next++,'post_id'=>(string)$pid,'meta_key'=>$meta['meta_key'],'meta_value'=>$meta['meta_value']];
                }
                if(count($keys)!==2)throw new \RuntimeException('Incomplete TablePress options or visibility.');
            }
        }
        $removed=array_map('intval',$removed);
        $data['tables']['posts']=array_values(array_filter($data['tables']['posts'],fn($p)=>!in_array((int)$p['ID'],$removed,true)));
        $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($p)=>!in_array((int)$p['post_id'],$removed,true)));
        $data['options']['tablepress_tables']=Store::json($map);
    }
}
