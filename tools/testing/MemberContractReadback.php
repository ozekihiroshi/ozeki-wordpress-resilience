<?php
declare(strict_types=1);
require_once __DIR__.'/MemberApplicationContract.php';

/** Read-only WordPress observation; does not call MemberHistory::baseline or projection. */
final class MemberContractReadback
{
    public static function observe(array $raw,string $sourceUrl): array {
        $errors=[];$expected=MemberApplicationContract::expected($raw)['data'];
        $file=WP_PLUGIN_DIR.'/wp-members/wp-members.php';
        $snapshot=['version'=>get_file_data($file,['Version'=>'Version'])['Version'],'settings'=>[],'users'=>[]];
        if(!in_array('wp-members/wp-members.php',(array)get_option('active_plugins'),true))$errors[]=['code'=>'inactive-runtime','path'=>'membership.version'];
        foreach(array_keys($expected['settings']) as $key)$snapshot['settings'][$key]=get_option($key,false);
        $keys=MemberApplicationContract::META;
        foreach(($expected['settings']['wpmembers_fields']??[])?:[] as $f)if(MemberApplicationContract::safeMeta($f[2]))$keys[]=$f[2];
        foreach($raw['users'] as $id=>$entry){
            $u=get_user_by('login',$entry['user']['user_login']);
            if(!$u){$errors[]=['code'=>'missing-member','path'=>'users.'.$id];continue;}
            if(get_user_meta($u->ID,'_ozeki_resilience_member_origin',true)!==hash('sha256',$sourceUrl.'|'.$id))$errors[]=['code'=>'identity-mapping','path'=>'users.'.$id];
            if($u->roles!==['subscriber']||array_diff_key($u->caps,['subscriber'=>true]))$errors[]=['code'=>'privilege-change','path'=>'users.'.$id];
            if($u->user_activation_key!==''||get_user_meta($u->ID,'session_tokens',true)||get_user_meta($u->ID,'_application_passwords',true))$errors[]=['code'=>'unexpected-access-state','path'=>'users.'.$id];
            $user=[];foreach(MemberApplicationContract::USER as $key)$user[$key]=$key==='ID'?(string)$id:(string)$u->data->$key;
            $meta=[];foreach(array_unique($keys) as $key){$values=get_user_meta($u->ID,$key,false);if($values)$meta[$key]=$values;}
            $snapshot['users'][$id]=['user'=>$user,'meta'=>$meta];
        }
        $mapped=get_users(['meta_key'=>'_ozeki_resilience_member_source','meta_value'=>hash('sha256',$sourceUrl),'fields'=>'ID']);
        if(count($mapped)!==count($raw['users']))$errors[]=['code'=>'member-count','path'=>'users'];
        foreach($expected['settings']['wpmembers_settings']['user_pages']??[] as $key=>$value)if(is_numeric($value)&&(int)$value>0&&get_post_type((int)$value)!=='page')$errors[]=['code'=>'missing-page-reference','path'=>'settings.user_pages.'.$key];
        return ['data'=>$snapshot,'errors'=>$errors];
    }
    /** Only explicitly recognized page URL references are rebased; other values stay exact. */
    public static function destinationExpected(array $raw,string $from,string $to): array {
        foreach($raw['settings']['wpmembers_settings']['user_pages']??[] as $key=>$value)if(is_string($value)&&str_starts_with($value,$from))$raw['settings']['wpmembers_settings']['user_pages'][$key]=$to.substr($value,strlen($from));
        return $raw;
    }
    public static function restrictions(array $originalRows,array $posts): array {
        $errors=[];$map=[];$checked=0;
        foreach($originalRows as $row)if($row['meta_key']==='_wpmem_block')$map[(int)$row['post_id']][]=(string)$row['meta_value'];
        foreach($posts as $post){if(!in_array($post['post_type'],['post','page'],true))continue;$id=(int)$post['ID'];$expected=$map[$id]??[];$checked++;
            if(count($expected)>1||array_diff($expected,['','0','1','2']))$errors[]=['code'=>'invalid-restriction','path'=>'post.'.$id];
            elseif(!get_post($id)||get_post_meta($id,'_wpmem_block',false)!==$expected)$errors[]=['code'=>'restriction-mismatch','path'=>'post.'.$id];
        }return ['checked'=>$checked,'errors'=>$errors];
    }
}
