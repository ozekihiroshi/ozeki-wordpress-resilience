<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Explicit registration material; never credentials, roles, or inferred account matches. */
final class ConstructionAuthors {
    public const PATH='construction/authors.json';
    public const SCHEMA='owr-construction-authors-experiment-1';
    private const FIELDS=['user_login','user_email','user_nicename','display_name'];
    public static function capture(array $files): array {
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);$users=[];
        foreach($d['tables']['posts'] as $p){
            if(!in_array($p['post_status'],['publish','private','inherit'],true)||!in_array($p['post_type'],['post','page','attachment','ozmd_document'],true))continue;
            $id=(int)$p['post_author'];if(!$id)continue;
            $u=get_userdata($id);if(!$u)throw new \RuntimeException('Source author is missing: '.$id);
            $record=[];foreach(self::FIELDS as $k)$record[$k]=(string)$u->$k;
            self::validate($record);$users[(string)$id]=$record;
        }
        ksort($users);$files[self::PATH]=wp_json_encode(['schema'=>self::SCHEMA,'users'=>$users]);return $files;
    }
    private static function validate(array $r): void {
        if(array_keys($r)!==self::FIELDS)throw new \RuntimeException('Unexpected author registration fields');
        foreach($r as $v)if(!is_string($v))throw new \RuntimeException('Invalid author value');
        if($r['user_login']===''||sanitize_user($r['user_login'],true)!==$r['user_login']||!is_email($r['user_email']))throw new \RuntimeException('Author login/email unavailable for normal registration');
    }
    public static function read(array $files): array {
        if(!isset($files[self::PATH]))return [];
        $data=json_decode($files[self::PATH],true,512,JSON_THROW_ON_ERROR);
        if(($data['schema']??'')!==self::SCHEMA||!is_array($data['users']??null))throw new \RuntimeException('Invalid author material');
        foreach($data['users'] as $id=>$r){if(!ctype_digit((string)$id)||(int)$id<1)throw new \RuntimeException('Invalid source author identity');self::validate($r);}
        return $data['users'];
    }
    public static function register(array $kit): array {
        if(!defined('OWR_CONSTRUCTION_ISOLATED')||OWR_CONSTRUCTION_ISOLATED!==true||!current_user_can('create_users'))throw new \RuntimeException('Isolated author registration only');
        $users=self::read($kit['files']);$key='owr_construction_authors_'.hash('sha256',wp_json_encode([$kit['anchor'],$users]));
        $state=get_option($key,null);
        if($state!==null){
            if(($state['state']??'')!=='complete')throw new \RuntimeException('Author registration outcome unresolved; do not duplicate');
            foreach($state['map'] as $old=>$new){$u=get_userdata($new);if(!$u)throw new \RuntimeException('Registered author missing');foreach(self::FIELDS as $f)if((string)$u->$f!==$users[$old][$f])throw new \RuntimeException('Registered author changed');}
            return $state['map'];
        }
        // Reject conflicts before creating any account. No prepared-admin adoption.
        foreach($users as $r)if(username_exists($r['user_login'])||email_exists($r['user_email']))throw new \RuntimeException('Author login/email conflicts with a prepared account');
        if(!add_option($key,['state'=>'registering'],'',false))throw new \RuntimeException('Author registration already started');
        $map=[];
        foreach($users as $old=>$r){
            $id=wp_insert_user($r+['user_pass'=>wp_generate_password(64,true,true),'role'=>'']);
            if(is_wp_error($id))throw new \RuntimeException($id->get_error_message());
            $map[$old]=(int)$id;
            if(!update_option($key,['state'=>'registering','map'=>$map],false))throw new \RuntimeException('Cannot record author registration');
        }
        $complete=['state'=>'complete','map'=>$map];update_option($key,$complete,false);
        if(get_option($key)!==$complete)throw new \RuntimeException('Cannot confirm author registration');
        return $map;
    }
}
