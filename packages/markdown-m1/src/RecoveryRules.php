<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/AcfHistory.php';

/** Projection at the destination boundary only. Never use this to rewrite stored originals. */
final class RecoveryRules
{
    public const VERSION='owr-application-rules-1';
    private array $skipped=[];
    private function omit(string $path,string $reason='No recognized application rule'): void {
        $this->skipped[]=['item'=>$path,'reason'=>$reason];
    }
    private static function plain(mixed $v): bool {
        if(is_array($v)){foreach($v as $x)if(!self::plain($x))return false;return true;}
        return is_scalar($v)||$v===null;
    }
    private function value(mixed $v,array|string $rule,string $path): mixed {
        if(is_array($rule)){
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
            if(!is_array($v))throw new \RuntimeException('Invalid recognized setting: '.$path);
            $out=[];foreach($v as $k=>$x){if(!array_key_exists($k,$rule)){$this->omit($path.'.'.$k);continue;}$out[$k]=$this->value($x,$rule[$k],$path.'.'.$k);}return $out;
        }
        if($rule==='plain'&&self::plain($v))return $v;
        if($rule==='text'&&is_string($v))return $v;
        if($rule==='number'&&(is_int($v)||is_float($v)||(is_string($v)&&is_numeric($v))))return $v;
        if($rule==='number-or-empty'&&($v===''||is_int($v)||(is_string($v)&&is_numeric($v))))return $v;
        if($rule==='bool'&&in_array($v,[true,false,0,1,'0','1'],true))return $v;
        if(in_array($rule,['text-map','number-map'],true)&&is_array($v)){
            foreach($v as $k=>$x)$this->value($x,$rule==='text-map'?'text':'number',$path.'.'.$k);return $v;
        }
        if($rule==='cf7-lines'&&is_string($v)){
            $out=[];foreach(preg_split('/\r\n|\r|\n/',$v) as $i=>$line){
                if(trim($line)===''){$out[]=$line;continue;}
                if(preg_match('/^\s*(skip_mail|demo_mode|acceptance_as_validation|subscribers_only)\s*:\s*(on|off|true|false)\s*$/i',$line))$out[]=$line;
                else $this->omit($path.'.line'.($i+1),'Additional directive is outside recognized core rules');
            }return implode("\n",$out);
        }
        if($rule==='member-fields'&&is_array($v)){
            $out=[];foreach($v as $i=>$field){
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
                if(!is_array($field)||!isset($field[2],$field[3]))throw new \RuntimeException('Invalid member field definition: '.$path);
                if(!in_array($field[3],['text','textarea','email','url','password','checkbox','select','radio','multiselect','number','date','hidden'],true)){
                    $this->omit($path.'.'.$i,'Unsupported registration field type');continue;
                }
                $out[]=$this->value($field,[0=>'number',1=>'text',2=>'text',3=>'text',4=>'text',5=>'text',6=>'text','profile'=>'number','native'=>'bool','value'=>'plain','values'=>'plain'],$path.'.'.$i);
            }return $out;
        }
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
        throw new \RuntimeException('Invalid recognized setting: '.$path);
    }
    private function metadata(string $raw,array|string $rule,string $path,bool $json=false): string {
        if($json){$v=json_decode($raw,true,512,JSON_THROW_ON_ERROR);return Store::json($this->value($v,$rule,$path));}
        // Text may itself look like serialization. Preserve original bytes, especially Markdown.
        if($rule==='text')return $raw;
        // WordPress metadata serialization is storage encoding, never instantiate objects.
        if(preg_match('/^(?:a|s|i|b|d|O|C):|^N;$/',$raw)){
            $v=@unserialize($raw,['allowed_classes'=>false]);
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
            if($v===false&&$raw!=='b:0;')throw new \RuntimeException('Invalid recognized serialization: '.$path);
            $out=$this->value($v,$rule,$path);return $out===$v?$raw:serialize($out);
        }
        $out=$this->value($raw,$rule,$path);return is_string($out)?$out:$raw;
    }
    public static function project(array $data,array $coreOptions): array {
        $self=new self();$d=$data;$types=[];
        $acf=AcfHistory::project($data);$self->skipped=$acf['skipped'];
        if(isset($data['acf'])){
            $removed=[];foreach($d['tables']['posts'] as $p)if(in_array($p['post_type'],['acf-field','acf-field-group'],true))$removed[]=(string)$p['ID'];
            $d['tables']['posts']=array_values(array_filter($d['tables']['posts'],fn($p)=>!in_array((string)$p['ID'],$removed,true)));
            $d['tables']['postmeta']=array_values(array_filter($d['tables']['postmeta'],fn($m)=>!in_array((string)$m['post_id'],$removed,true)&&!isset($acf['keys'][(string)$m['post_id']][$m['meta_key']])));
            $d['acf_restore_groups']=$acf['groups'];
        }
        foreach($d['tables']['posts']??[] as $post)$types[(string)$post['ID']]=$post['post_type'];
        $base=['_owr_m1_asset'=>'text','_owr_m1_origin_url'=>'text','_owr_m1_origin'=>'text','_wpmem_block'=>'text','_thumbnail_id'=>'number','_wp_page_template'=>'text','_wp_trash_meta_status'=>'text','_wp_trash_meta_time'=>'number','_wp_trash_meta_comments_status'=>'plain','_wp_old_slug'=>'text','_wp_old_date'=>'text'];
        $out=[];
        foreach($d['tables']['postmeta']??[] as $row){
            $type=$types[(string)$row['post_id']]??'';$key=$row['meta_key'];$rules=$base;
            if($type==='ozmd_document')$rules+=['_ozmd_source'=>'text'];
            if($type==='attachment')$rules+=['_wp_attached_file'=>'text','_wp_attachment_image_alt'=>'text','_wp_attachment_metadata'=>'plain','_wp_attachment_backup_sizes'=>'plain'];
            if($type==='nav_menu_item')$rules+=array_fill_keys(['_menu_item_type','_menu_item_menu_item_parent','_menu_item_object_id','_menu_item_object','_menu_item_target','_menu_item_xfn','_menu_item_url'],'text')+['_menu_item_classes'=>'plain'];
            if(in_array($type,['wpcf7_contact_form','flamingo_inbound'],true))$rules+=FormHistory::recoveryMeta($type);
            if($type==='tablepress_table')$rules+=TableHistory::recoveryMeta();
            $path='postmeta.'.$row['post_id'].'.'.$key;
            if(!array_key_exists($key,$rules)){$self->omit($path,$key==='_ozmd_source_sha256'?'Derived from restored Markdown; regenerated, not imported':'No recognized application rule');continue;}
            $row['meta_value']=$self->metadata($row['meta_value'],$rules[$key],$path,$type==='tablepress_table'&&str_starts_with($key,'_tablepress_'));$out[]=$row;
        }
        $next=max(array_merge([0],array_map('intval',array_column($out,'meta_id'))))+1;
        foreach($acf['meta'] as $row){$row['meta_id']=(string)$next++;$out[]=$row;}
        $d['tables']['postmeta']=$out;
        foreach(['commentmeta','termmeta'] as $table){
            $kept=[];foreach($d['tables'][$table]??[] as $row){
                $path=$table.'.'.($row['comment_id']??$row['term_id']).'.'.$row['meta_key'];
                if($table==='commentmeta'&&in_array($row['meta_key'],['_wp_trash_meta_status','_wp_trash_meta_time'],true)){
                    $row['meta_value']=$self->metadata($row['meta_value'],$row['meta_key']==='_wp_trash_meta_time'?'number':'text',$path);$kept[]=$row;
                }else $self->omit($path);
            }$d['tables'][$table]=$kept;
        }
        $numbers=['page_on_front','page_for_posts','posts_per_page','posts_per_rss','gmt_offset','start_of_week','site_icon','default_category','wp_page_for_privacy_policy'];
        $rules=[];foreach($coreOptions as $key)$rules[$key]=in_array($key,$numbers,true)?'number':($key==='sticky_posts'?'number-map':($key==='sidebars_widgets'?'plain':'text'));
        $rules+=TableHistory::recoveryOptions();$out=[];
        foreach($d['options']??[] as $key=>$value){
            $path='options.'.$key;
            if(str_starts_with($key,'theme_mods_')){
                $out[$key]=$self->value($value,['nav_menu_locations'=>'number-map','custom_logo'=>'number','background_color'=>'text','header_textcolor'=>'text'],$path);continue;
            }
            if(!array_key_exists($key,$rules)){$self->omit($path,'Unrecognized or theme/widget-specific setting');continue;}
            if(in_array($key,TableHistory::OPTIONS,true))$out[$key]=$self->metadata($value,$rules[$key],$path,true);
            else $out[$key]=$value===false?false:$self->value($value,$rules[$key],$path);
        }
        if(isset($out['tablepress_plugin_options'])){
            $o=json_decode($out['tablepress_plugin_options'],true,512,JSON_THROW_ON_ERROR);
            // Do not inherit destination CSS or module defaults as though they were recovered.
            $o+=['use_custom_css'=>false,'use_custom_css_file'=>false,'custom_css'=>'','custom_css_minified'=>'','modules'=>false];$out['tablepress_plugin_options']=Store::json($o);
        }
        $d['options']=$out;
        if(isset($d['membership'])){
            $settings=[];$rules=MemberHistory::recoverySettings();
            foreach($d['membership']['settings'] as $key=>$v){
                if(!isset($rules[$key])){$self->omit('membership.settings.'.$key);continue;}
                // False denotes an option absent at capture; preserve that absence representation.
                $settings[$key]=$v===false?false:$self->value($v,$rules[$key],'membership.settings.'.$key);
            }
            $d['membership']['settings']=$settings;
            $keys=MemberHistory::metaKeys((array)($settings['wpmembers_fields']??[]));
            foreach($d['membership']['users'] as $id=>&$user){foreach($user['meta'] as $key=>$v){
                if(!in_array($key,$keys,true)){$self->omit('membership.user.'.$id.'.'.$key);unset($user['meta'][$key]);}
                elseif(!self::plain($v))throw new \RuntimeException('Invalid member value');
            }}unset($user);
        }
        return ['data'=>$d,'report'=>['rules'=>self::VERSION,'not_applied'=>$self->skipped,'count'=>count($self->skipped),'originals'=>'Unchanged in S3; omitted values are not copied into this report']];
    }
}
