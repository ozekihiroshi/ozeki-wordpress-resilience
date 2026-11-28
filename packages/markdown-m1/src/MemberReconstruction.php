<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
/** Select saved member materials. Destination writes are ordinary authenticated forms. */
final class MemberReconstruction {
    public static function plan(array $manifest,array $files): array {
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        $state=$d['membership']??null;
        if(!is_array($state)||!is_array($state['settings']??null)||!is_array($state['users']??null))throw new \RuntimeException('Missing saved membership material.');
        $out=['schema'=>'owr-normal-members-registration-1','source_url'=>$manifest['source_url'],'through'=>$manifest['through'],'version'=>$state['version'],'settings'=>$state['settings'],'users'=>[],'restrictions'=>[],'held'=>[]];
        foreach($state['users'] as $id=>$entry){
            $u=$entry['user']??[];$meta=$entry['meta']??[];
            if((string)($u['ID']??'')!==(string)$id||empty($u['user_login'])||empty($u['user_email'])||!is_array($meta)){$out['held']['user:'.$id]='Missing or inconsistent member identity';continue;}
            // A stored hash is not a plaintext argument to ordinary account creation.
            unset($u['user_pass']);
            $out['users'][]=['origin_id'=>(string)$id,'user'=>$u,'meta'=>$meta,'credential'=>'new-password-required; saved hash cannot be passed to normal registration'];
        }
        $meta=[];foreach($d['tables']['postmeta']??[] as $m)if($m['meta_key']==='_wpmem_block')$meta[(string)$m['post_id']]=$m['meta_value'];
        foreach($d['tables']['posts']??[] as $p){
            if(!in_array($p['post_type'],['post','page'],true)||!in_array($p['post_status'],['publish','private'],true))continue;
            $id=(string)$p['ID'];$value=(string)($meta[$id]??'');
            if(!in_array($value,['','0','1','2'],true)){$out['held']['restriction:'.$id]='Unknown saved restriction';continue;}
            $effective=$value===''?(string)($state['settings']['wpmembers_settings']['block'][$p['post_type']]??''):$value;
            if(!in_array($effective,['0','1','2'],true)){$out['held']['restriction:'.$id]='Missing default restriction';continue;}
            $out['restrictions'][]=['origin_id'=>$id,'type'=>$p['post_type'],'value'=>$effective,'stored_value'=>$value];
        }
        return $out;
    }
}
