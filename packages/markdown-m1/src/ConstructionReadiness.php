<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** No destination lookup or fabricated identities: use only the saved kit. */
final class ConstructionReadiness {
    public static function inspect(array $kit): array {
        $d=json_decode($kit['files']['content.json'],true,512,JSON_THROW_ON_ERROR);
        $out=['state'=>'ready_for_registration','blocking'=>[],'affected'=>[],'materials'=>[],'tail_count'=>count($kit['tail'])];
        $posts=[];$meta=[];$registration=ConstructionAuthors::read($kit['files']);
        foreach($d['tables']['posts'] as $p)$posts[(int)$p['ID']]=$p;
        foreach($d['tables']['postmeta'] as $m)$meta[(int)$m['post_id']][$m['meta_key']]=$m['meta_value'];
        foreach($posts as $id=>$p){
            if(!in_array($p['post_status'],['publish','private','inherit'],true))continue;
            $out['materials'][$p['post_type']]=($out['materials'][$p['post_type']]??0)+1;
            if(!in_array($p['post_type'],['post','page','ozmd_document'],true))continue;
            $author=(string)$p['post_author'];$member=$registration[$author]??($d['membership']['users'][$author]['user']??[]);
            if($author!=='0' && (empty($member['user_login'])||empty($member['user_email']))){
                $key='author:'.$author;
                $out['blocking'][$key]=['reason'=>'normal_account_registration_material_missing','available'=>$d['authors'][$author]??null,'required'=>['user_login','user_email'],'policy'=>'Do not adopt a prepared administrator or invent a login/email'];
                $out['affected'][(string)$id]=['type'=>$p['post_type'],'reason'=>$key];
            }
        }
        foreach($posts as $id=>$p){
            if($p['post_type']!=='attachment')continue;
            $path='uploads/'.($meta[$id]['_wp_attached_file']??'');
            if(!isset($kit['files'][$path]))$out['blocking']['attachment:'.$id]=['reason'=>'original_file_missing','path'=>$path];
        }
        foreach($kit['tail'] as $e){
            if($e['state']==='rejected')continue;
            if($e['operation']==='rest'&&preg_match('~^/wp/v2/(?:posts|pages)/(\d+)$~D',$e['input']['route'],$m)&&isset($out['affected'][$m[1]]))$out['blocking']['operation:'.$e['sequence']]=['reason'=>'baseline_reference_not_registered','origin_id'=>(int)$m[1]];
        }
        if($out['blocking'])$out['state']='held_before_destination_writes';
        return $out;
    }
}
