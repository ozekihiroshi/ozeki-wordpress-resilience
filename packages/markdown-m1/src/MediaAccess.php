<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/FileScope.php';

/** File placement permission is independent of the parent page's viewing rules. */
final class MediaAccess {
    public const SNAPSHOT_FORMAT='owr-separated-assets-media-access-1';
    public const ORIGINAL_FORMAT='owr-md-original-media-access-1';
    public const SCHEMA='owr-media-access-1';
    public const OPTION='ozeki_resilience_media_hold';
    private bool $dirty=false;
    public static function validate(array $rules): array {
        foreach($rules as $path=>$rule){
            if(!is_string($path)||!SiteSnapshot::isInformationFile($path)||!is_array($rule)||array_keys($rule)!==['state']||!in_array($rule['state'],['public','held','unknown'],true))throw new \RuntimeException('Invalid media access contract.');
        }
        ksort($rules);return $rules;
    }
    public static function effective(array $rules,array $files): array {
        $rules=self::validate($rules);
        foreach($files as $path=>$_)if(str_starts_with($path,'uploads/')&&SiteSnapshot::isInformationFile($path)&&!isset($rules[$path]))$rules[$path]=['state'=>'unknown'];
        return self::validate($rules);
    }
    public static function classify(array $data,array $guarded,array $inherited=[]): array {
        $public=FileScope::paths($data);$rules=[];
        foreach(FileScope::paths($data,true) as $path=>$_){
            $state=isset($public[$path])&&!in_array($path,$guarded,true)?'public':'held';
            if(isset($inherited[$path])&&$inherited[$path]['state']!=='public')$state=$inherited[$path]['state'];
            $rules[$path]=['state'=>$state];
        }
        // Projected metadata must not erase unresolved access conditions.
        foreach($inherited as $path=>$rule)if($rule['state']!=='public'&&!isset($rules[$path]))$rules[$path]=$rule;
        return self::validate($rules);
    }
    public static function current(?array $data=null): array {
        global $wpdb;
        clearstatcache();
        if($data===null){
            $data=['tables'=>['posts'=>$wpdb->get_results("SELECT * FROM {$wpdb->posts}",ARRAY_A),'postmeta'=>$wpdb->get_results("SELECT * FROM {$wpdb->postmeta}",ARRAY_A)]];
            if($wpdb->last_error)throw new \RuntimeException('Cannot inspect media access conditions.');
        }
        $root=rtrim(wp_upload_dir()['basedir'],'/');$guarded=[];
        foreach(FileScope::paths($data,true) as $path=>$_){
            for($dir=dirname($root.'/'.substr($path,8));$dir===$root||str_starts_with($dir,$root.'/');$dir=dirname($dir)){
                if(is_file($dir.'/.htaccess')||is_file($dir.'/web.config')||is_link($dir)){$guarded[]=$path;break;}
                if($dir===$root)break;
            }
        }
        $held=(array)get_option(self::OPTION,[]);
        return self::classify($data,$guarded,$held['rules']??[]);
    }
    /** Held bytes stay in non-autoloaded local state, never a publicly served directory. */
    public static function heldBody(string $path): ?string {
        $held=(array)get_option(self::OPTION,[]);$entry=$held['files'][$path]??null;
        if($entry===null)return null;
        $body=base64_decode($entry['body'],true);
        if($body===false||strlen($body)>32*1024*1024||!hash_equals($entry['sha256'],hash('sha256',$body)))throw new \RuntimeException('Held media integrity check failed.');
        return $body;
    }
    public static function hold(array $rules,array $files): array {
        $out=['rules'=>self::validate($rules),'files'=>[]];
        foreach($files as $path=>$body)if(isset($rules[$path])&&$rules[$path]['state']!=='public'){
            if(strlen($body)>32*1024*1024)throw new \RuntimeException('Held media exceeds 32 MiB.');
            $out['files'][$path]=['body'=>base64_encode($body),'sha256'=>hash('sha256',$body)];
        }
        return $out;
    }
    public function boot(): void {
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)add_action($hook,function($mid,$id,$key){
            if(!str_starts_with($key,'_ozeki_resilience')&&!in_array($key,['_edit_lock','_edit_last'],true))$this->dirty=true;
        },PHP_INT_MAX,3);
        foreach(['wp_after_insert_post','deleted_post'] as $hook)add_action($hook,function(){$this->dirty=true;},PHP_INT_MAX);
        add_action('shutdown',function(){if($this->dirty)SaveFailure::run('Media access capture',fn()=>self::record());},PHP_INT_MAX);
    }
    public static function record(): void {
        $config=(new Plugin())->config();
        if(empty($config['protect'])||($config['setup_role']??'source')==='recovery')return;
        (new CommentHistory())->enqueueCurrent('media-access',fn()=>Store::json(['schema'=>self::SCHEMA,'rules'=>self::current()]),['post_type'=>'owr_media_access','content_format'=>'media-access-json','media_access_schema'=>self::SCHEMA]);
    }
    public static function replay(array &$data,string $source): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);
        if(($v['schema']??null)!==self::SCHEMA||!is_array($v['rules']??null))throw new \RuntimeException('Invalid media access history.');
        $data['media_access']=self::validate($v['rules']);
    }
}
