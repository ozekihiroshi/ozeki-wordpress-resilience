<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Read-only destination application plan. Never used to filter preserved originals. */
final class RecoverySettings {
    private static function row(array $tables,string $table,string $key,int $id): ?array {
        foreach($tables[$table]??[] as $row)if((int)($row[$key]??0)===$id)return $row;
        return null;
    }
    private static function meta(array $tables,int $id,string $key): mixed {
        foreach($tables['postmeta']??[] as $row)if((int)$row['post_id']===$id&&$row['meta_key']===$key)return $row['meta_value'];
        return null;
    }
    private static function post(array $after,int $id,string $type,?array $before=null): bool {
        $new=self::row($after,'posts','ID',$id);
        if(!$new||$new['post_type']!==$type)return false;
        if($before===null)return true;
        $old=self::row($before,'posts','ID',$id);
        if(!$old||$old['post_type']!==$type||empty($old['guid'])||$old['guid']!==($new['guid']??null))return false;
        return $type!=='attachment'||(self::meta($before,$id,'_wp_attached_file')!==null&&self::meta($before,$id,'_wp_attached_file')===self::meta($after,$id,'_wp_attached_file'));
    }
    private static function term(array $after,int $id,string $taxonomy,?array $before=null): bool {
        $term=self::row($after,'terms','term_id',$id);$found=false;
        foreach($after['term_taxonomy']??[] as $row)if((int)$row['term_id']===$id&&$row['taxonomy']===$taxonomy)$found=true;
        if(!$term||!$found)return false;
        if($before===null)return true;
        $old=self::row($before,'terms','term_id',$id);
        return $old&&($old['slug']??null)===($term['slug']??null)&&self::term($before,$id,$taxonomy);
    }
    private static function widget(string $id,array $prepared,array $after,array $before): bool {
        if(!preg_match('/^(.+)-([0-9]+)$/D',$id,$match))return false;
        $kind=$match[1];$instance=$prepared['widget_'.$kind][(int)$match[2]]??null;
        if(!is_array($instance))return false;
        if($kind==='nav_menu')return empty($instance['nav_menu'])||self::term($after,(int)$instance['nav_menu'],'nav_menu',$before);
        if(in_array($kind,['media_image','media_audio','media_video'],true))return !empty($instance['attachment_id'])&&self::post($after,(int)$instance['attachment_id'],'attachment',$before);
        if($kind==='media_gallery'){
            foreach($instance['ids']??[] as $id)if(!self::post($after,(int)$id,'attachment',$before))return false;
            return true;
        }
        if($kind==='pages'){
            foreach(array_filter(array_map('trim',explode(',',(string)($instance['exclude']??'')))) as $id)if(!ctype_digit($id)||!self::post($after,(int)$id,'page',$before))return false;
            return true;
        }
        if(in_array($kind,['text','custom_html'],true)){
            $body=(string)($instance['text']??$instance['content']??'');
            // Rich blocks, links and shortcodes can bind to replaced content or other plugins.
            return !preg_match('/\[|<!--\s*wp:|<(?:a|img|iframe|video|audio|source)\b|https?:\/\//i',$body);
        }
        // These core widgets query the recovered collection, rather than a saved object ID.
        return in_array($kind,['search','calendar','archives','categories','recent-posts','recent-comments','meta','tag_cloud'],true);
    }
    public static function plan(array $saved,array $prepared,array $after,array $before,string $theme): array {
        $out=$saved;$report=[];$localPosts=[];$localMeta=[];
        $omit=static function(string $key,string $reason,string $origin='source')use(&$report){$report[]=['item'=>$key,'reason'=>$reason,'origin'=>$origin];};
        // The registry is content; plugin-wide operational settings belong to the prepared site.
        if(array_key_exists('tablepress_plugin_options',$out)){
            unset($out['tablepress_plugin_options']);
            $omit('options.tablepress_plugin_options','Prepared destination TablePress settings retained; archived global settings are not applied');
        }
        unset($out['sidebars_widgets']);
        foreach(array_keys($out) as $key){
            if(str_starts_with($key,'widget_'))unset($out[$key]);
            if(str_starts_with($key,'theme_mods_')&&$key!=='theme_mods_'.$theme){unset($out[$key]);$omit('options.'.$key,'Destination theme differs; prepared theme retained');}
        }
        $key='theme_mods_'.$theme;$base=$prepared[$key]??false;$source=$saved[$key]??false;
        if(is_array($base)||is_array($source)){
            $mods=is_array($base)?$base:[];
            // Core Custom CSS is prepared theme content stored in wp_posts, not in theme_mods.
            // Preserve that trusted destination record before replacing the content tables.
            $cssId=(int)($mods['custom_css_post_id']??0);
            if($cssId>0){
                $css=self::row($before,'posts','ID',$cssId);
                if($css&&$css['post_type']==='custom_css'){
                    $newId=1;foreach($after['posts']??[] as $row)$newId=max($newId,(int)$row['ID']+1);
                    $css['ID']=$newId;$css['post_parent']=0;$localPosts[]=$css;$mods['custom_css_post_id']=$newId;
                    foreach($before['postmeta']??[] as $row)if((int)$row['post_id']===$cssId&&!in_array($row['meta_key'],['_edit_lock','_edit_last'],true)){
                        unset($row['meta_id']);$row['post_id']=$newId;$localMeta[]=$row;
                    }
                }else{
                    unset($mods['custom_css_post_id']);$omit('options.'.$key.'.custom_css_post_id','Prepared custom CSS reference is missing; review the destination theme CSS','destination');
                }
            }
            // Absence in an old record is not an instruction to delete prepared settings.
            foreach(['nav_menu_locations','custom_logo','background_color','header_textcolor'] as $field){
                $incoming=is_array($source)&&array_key_exists($field,$source);
                if($incoming)$mods[$field]=$source[$field];
                if(!array_key_exists($field,$mods))continue;
                if($field==='custom_logo'&&!empty($mods[$field])&&!self::post($after,(int)$mods[$field],'attachment',$incoming?null:$before)){
                    unset($mods[$field]);$omit('options.'.$key.'.'.$field,'Logo reference unavailable or changed identity; select the logo again','destination');
                }
                if($field==='nav_menu_locations')foreach((array)$mods[$field] as $location=>$id){
                    if($id&&!self::term($after,(int)$id,'nav_menu',$incoming?null:$before)){
                        unset($mods[$field][$location]);$omit('options.'.$key.'.nav_menu_locations.'.$location,'Menu reference unavailable or changed identity; assign the menu again','destination');
                    }
                }
            }
            $out[$key]=$mods;
        }
        if(is_array($prepared['sidebars_widgets']??null)){
            $sidebars=$prepared['sidebars_widgets'];$inactive=(array)($sidebars['wp_inactive_widgets']??[]);
            foreach($sidebars as $sidebar=>&$ids){
                if($sidebar==='wp_inactive_widgets'||!is_array($ids))continue;
                $kept=[];foreach($ids as $id){
                    if(is_string($id)&&self::widget($id,$prepared,$after,$before))$kept[]=$id;
                    else {if(is_string($id))$inactive[]=$id;$omit('widgets.'.(string)$id,'Placement held: referenced content changed or widget references cannot be verified; configuration retained for administrator review','destination');}
                }$ids=$kept;
            }unset($ids);
            $sidebars['wp_inactive_widgets']=array_values(array_unique($inactive));$out['sidebars_widgets']=$sidebars;
        }
        if(array_key_exists('sidebars_widgets',$saved))$omit('options.sidebars_widgets','Source widget layout not applied; destination widget configuration retained');
        return ['options'=>$out,'report'=>$report,'local_posts'=>$localPosts,'local_postmeta'=>$localMeta];
    }
}
