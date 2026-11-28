<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Read-only material selection. Destination writes use CF7's ordinary REST interface. */
final class ContactFormReconstruction {
    public static function plan(array $manifest,array $files): array {
        $data=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        if(($data['update_contract']??'')!==UpdateContract::SCHEMA||!empty($manifest['legacy_incomplete_article_conditions']))throw new \RuntimeException('Complete publication conditions required');
        $out=['schema'=>'owr-normal-cf7-registration-1','source_url'=>$manifest['source_url'],'through'=>$manifest['through'],'forms'=>[],'pages'=>[],'held'=>[],'excluded'=>[]];
        $meta=[];foreach($data['tables']['postmeta'] as $m)$meta[(int)$m['post_id']][$m['meta_key']]=$m['meta_value'];
        foreach($data['tables']['posts'] as $p){
            $id=(int)$p['ID'];$m=$meta[$id]??[];$type=$p['post_type'];
            if($type==='wpcf7_contact_form'){
                try {
                    if($p['post_status']!=='publish'){$out['excluded']['form:'.$id]='Not a current saved form';continue;}
                    $input=['title'=>$p['post_title']];
                    foreach(['form','mail','mail_2','messages','additional_settings','locale'] as $key){
                        if(!array_key_exists('_'.$key,$m))throw new \RuntimeException('Missing form material: '.$key);
                        $v=$m['_'.$key];$input[$key]=is_serialized($v)?unserialize($v,['allowed_classes'=>false]):$v;
                    }
                    // Validate HTML without mutating the archived content. Unknown executable markup is held.
                    if(!is_string($input['form'])||wp_kses_post($input['form'])!==$input['form'])throw new \RuntimeException('Form markup needs an explicit safe application decision');
                    $out['forms'][]=['origin_id'=>(string)$id,'origin_hash'=>(string)($m['_hash']??''),'input'=>$input];
                }catch(\Throwable $e){$out['held']['form:'.$id]=$e->getMessage();}
                continue;
            }
            if(!in_array($type,['post','page'],true)||!str_contains(html_entity_decode($p['post_content'],ENT_QUOTES|ENT_HTML5,'UTF-8'),'[contact-form-7'))continue;
            if(!in_array($p['post_status'],['publish','private'],true)){$out['excluded']['page:'.$id]='Not a formal current publication';continue;}
            if(isset($data['membership'])||in_array((string)($m['_wpmem_block']??''),['1','2'],true)||$p['post_parent']){$out['held']['page:'.$id]='Membership or parent mapping requires the combined registration stage';continue;}
            $out['pages'][]=['origin_id'=>$id,'type'=>$type,'title'=>$p['post_title'],'slug'=>$p['post_name'],'content'=>$p['post_content'],'status'=>$p['post_status'],'password'=>$p['post_password'],'excerpt'=>$p['post_excerpt'],'date_gmt'=>$p['post_date_gmt'],'author_origin'=>(int)$p['post_author'],'comment_status'=>$p['comment_status'],'ping_status'=>$p['ping_status']];
        }
        return $out;
    }
}
