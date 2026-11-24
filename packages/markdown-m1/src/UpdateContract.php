<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Fields shared by baseline, daily preservation and article application. */
final class UpdateContract {
    public const SCHEMA='owr-core-updates-1';
    public const ORIGINAL_FORMAT='owr-original-core-updates-1';
    public const SNAPSHOT_FORMAT='owr-separated-assets-core-updates-1';
    public const INDEX_FORMAT='owr-snapshot-core-updates-1';
    public const FIELDS=['post_excerpt','post_parent','menu_order','comment_status','ping_status','post_password','post_author'];
    public const OPTIONS=['blogname','show_on_front','page_on_front','page_for_posts','timezone_string','gmt_offset','posts_per_page'];
    public static function requireArticleConditions(array $attributes): void {
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Localized diagnostic; escaped by the existing admin error renderer.
        if(($attributes['update_contract']??'')!==self::SCHEMA)throw new \RuntimeException(SetupReadiness::text('This older article history does not record password changes. Update both sites and create a new trusted initial save on the healthy source. Existing originals and history remain unchanged.','この旧記事履歴にはパスワード変更が記録されていません。保存元・復旧先を新版に揃え、健全な保存元で新しい初回保存を作成してください。既存の原本・履歴は変更しません。'));
    }
    public static function options(): array {
        $defaults=['blogname'=>'','show_on_front'=>'posts','page_on_front'=>0,'page_for_posts'=>0,'timezone_string'=>'','gmt_offset'=>0,'posts_per_page'=>10];
        $values=[];foreach($defaults as $key=>$default)$values[$key]=get_option($key,$default);
        return $values;
    }
    public static function author(int $id): ?array {
        $u=get_userdata($id);
        return $u?['display_name'=>(string)$u->display_name,'user_nicename'=>(string)$u->user_nicename]:null;
    }
    public static function capture(array $post): array {
        $a=['update_contract'=>self::SCHEMA];
        foreach(self::FIELDS as $key){
            if(!array_key_exists($key,$post))throw new \RuntimeException('Incomplete article capture.');
            $a[$key]=(string)$post[$key];
        }
        $a['author']=self::author((int)$a['post_author']);
        self::validate($a);return $a;
    }
    public static function validate(array $a): void {
        if(($a['update_contract']??'')!==self::SCHEMA)throw new \RuntimeException('Unknown article update contract.');
        foreach(self::FIELDS as $key)if(!array_key_exists($key,$a)||!is_string($a[$key]))throw new \RuntimeException('Incomplete article update fields.');
        foreach(['post_author','post_parent'] as $key)if(!ctype_digit($a[$key]))throw new \RuntimeException('Invalid article identity.');
        if(!preg_match('/^-?[0-9]+$/D',$a['menu_order'])||!in_array($a['comment_status'],['open','closed'],true)||!in_array($a['ping_status'],['open','closed'],true))throw new \RuntimeException('Invalid article update values.');
        if((int)$a['post_author']>0&&(!is_array($a['author']??null)||array_keys($a['author'])!==['display_name','user_nicename']||!is_string($a['author']['display_name'])||!is_string($a['author']['user_nicename'])))throw new \RuntimeException('Missing author description.');
    }
    public static function apply(array $a,array &$data): array {
        if(!isset($a['update_contract']))return array_intersect_key($a,array_flip(['post_excerpt','post_parent','menu_order','comment_status','ping_status']));
        self::validate($a);
        if((int)$a['post_author']>0)$data['authors'][(string)$a['post_author']]=$a['author'];
        return array_intersect_key($a,array_flip(self::FIELDS));
    }
    /** Destination-local author account, with no imported credentials or capabilities. */
    public static function authorId(string $origin,int $id,array $author): int {
        if($id===0)return 0;
        $login='owr-author-'.substr(hash('sha256',$origin.'|'.$id),0,20);
        $u=get_user_by('login',$login);
        $uid=$u?$u->ID:wp_insert_user(['user_login'=>$login,'user_pass'=>wp_generate_password(64,true,true),'display_name'=>$author['display_name'],'user_nicename'=>$author['user_nicename'],'role'=>'']);
        if(is_wp_error($uid))throw new \RuntimeException($uid->get_error_message());
        return (int)$uid;
    }
}
