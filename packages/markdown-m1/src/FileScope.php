<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Shared selection for capture and recovery, including legacy recovery points. */
final class FileScope {
    public const REASON='File ownership or public access is outside recognized media rules';
    private static function value(mixed $v): mixed {
        if(is_string($v)&&preg_match('/^(?:a|s|i|b|d|O|C):|^N;$/',$v))return @unserialize($v,['allowed_classes'=>false]);
        return $v;
    }
    private static function ordinary(string $p): bool {
        // Plugin-managed subdirectories are not ordinary public WordPress media.
        if(!preg_match('~^(?:[0-9]{4}/(?:0[1-9]|1[0-2])/)?[^/]+$~D',$p))return false;
        try{return SiteSnapshot::isInformationFile('uploads/'.$p);}
        catch(\RuntimeException $e){return false;}
    }
    public static function paths(array $data): array {
        $posts=[];$meta=[];$out=[];$denied=[];$unknownReferences=[];
        foreach($data['tables']['posts']??[] as $p)$posts[(string)$p['ID']]=$p;
        foreach($data['tables']['postmeta']??[] as $m)$meta[(string)$m['post_id']][$m['meta_key']]=self::value($m['meta_value']);
        foreach($posts as $id=>$p)if(!in_array($p['post_type'],['attachment','post','page','ozmd_document','revision','nav_menu_item','wp_block','wp_template','wp_template_part','wp_navigation','wpcf7_contact_form','flamingo_inbound','tablepress_table','acf-field','acf-field-group'],true))
            $unknownReferences[]=json_encode([$p,$meta[$id]??[]],JSON_UNESCAPED_SLASHES|JSON_INVALID_UTF8_SUBSTITUTE);
        foreach($posts as $id=>$p){
            if($p['post_type']!=='attachment')continue;
            $m=$meta[$id]??[];$file=$m['_wp_attached_file']??null;
            if(!is_string($file)||!self::ordinary($file))continue;
            $paths=['uploads/'.$file=>true];$details=$m['_wp_attachment_metadata']??[];
            if(is_array($details)){
                $dir=dirname($file);$dir=$dir==='.'?'':$dir.'/';$extra=[];
                foreach($details['sizes']??[] as $size)if(is_array($size))$extra[]=$size['file']??null;
                $extra[]=$details['original_image']??null;
                foreach($extra as $name)if(is_string($name)&&basename($name)===$name&&self::ordinary($dir.$name))$paths['uploads/'.$dir.$name]=true;
            }
            if(!in_array($p['post_status'],['inherit','publish'],true)||!empty($p['post_password'])){$denied+=$paths;continue;}
            $ownedElsewhere=false;foreach($unknownReferences as $references)foreach($paths as $path=>$_)if($references===false||str_contains($references,substr($path,8))){$ownedElsewhere=true;break 2;}
            if($ownedElsewhere){$denied+=$paths;continue;}
            $known=['_wp_attached_file','_wp_attachment_metadata','_wp_attachment_image_alt','_wp_attachment_backup_sizes','_wp_attachment_context','_wp_attachment_is_custom_header','_wp_attachment_is_custom_background','_edit_lock','_edit_last'];
            if(array_diff(array_keys($m),$known)){$denied+=$paths;continue;}
            $parent=(string)($p['post_parent']??0);$seen=[];$public=true;
            while($parent!=='0'&&$parent!==''){
                $q=$posts[$parent]??null;
                if(!$q||isset($seen[$parent])||!in_array($q['post_type'],['post','page','ozmd_document'],true)||$q['post_status']!=='publish'||!empty($q['post_password'])||!empty($meta[$parent]['_wpmem_block'])){$public=false;break;}
                $seen[$parent]=true;$parent=(string)($q['post_parent']??0);
            }
            if(!$public){$denied+=$paths;continue;}
            $out+=$paths;
        }
        return array_diff_key($out,$denied);
    }
}
