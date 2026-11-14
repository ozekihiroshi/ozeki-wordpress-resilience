<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** One registered information attachment, its derivatives and placement conditions. */
final class AttachmentHistory {
    public const SCHEMA='owr-attachment-bundle-1';
    public const ORIGINAL_FORMAT='owr-original-attachment-bundle-1';
    public const SNAPSHOT_FORMAT='owr-separated-assets-attachment-bundle-1';
    public const INDEX_FORMAT='owr-snapshot-attachment-bundle-1';
    public const PENDING='ozeki_resilience_attachment_pending';
    public const ERRORS='ozeki_resilience_attachment_errors';
    private static bool $running=false;
    private static function lock(): string {
        global $wpdb;$name='ozeki-resilience-'.$wpdb->prefix;
        if((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 10)',$name))!==1)throw new \RuntimeException('Attachment capture is busy; retry.');
        wp_cache_delete(self::PENDING,'options');wp_cache_delete(self::ERRORS,'options');return $name;
    }
    private static function unlock(string $name): void {global $wpdb;$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$name));}
    private static function enabled(): bool {
        $c=(new Plugin())->config();return !empty($c['protect'])&&($c['setup_role']??'source')==='source';
    }
    public static function assertComplete(array $data,array $files): void {
        $paths=FileScope::paths($data,true);$rules=MediaAccess::validate($data['media_access']??[]);
        foreach($paths+$rules as $path=>$_){
            if(!array_key_exists($path,$files))throw new \RuntimeException('Attachment original or derivative missing: '.$path);
            if(!isset($rules[$path]))throw new \RuntimeException('Attachment viewing condition missing: '.$path);
        }
    }
    public static function missing(array $data,array $files): array {
        return array_keys(array_diff_key(FileScope::paths($data,true)+($data['media_access']??[]),$files));
    }
    private static function mark(int $id,bool $deleted=false): void {
        if(!self::enabled())return;
        $lock=self::lock();try {
        $pending=(array)get_option(self::PENDING,[]);$pending[$id]=$deleted||!empty($pending[$id]);
        update_option(self::PENDING,$pending,false);
        if(get_option(self::PENDING)!==$pending)throw new \RuntimeException('Cannot persist attachment capture pending state.');
        } finally {self::unlock($lock);}
    }
    public function boot(): void {
        foreach(['add_attachment','edit_attachment'] as $hook)add_action($hook,fn($id)=>self::mark((int)$id),PHP_INT_MAX);
        add_action('delete_attachment',fn($id)=>self::mark((int)$id,true),PHP_INT_MAX);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)add_action($hook,function($mid,$id,$key){
            if(get_post_type($id)==='attachment'&&!in_array($key,['_edit_lock','_edit_last'],true))self::mark((int)$id);
        },PHP_INT_MAX,3);
        add_action('shutdown',fn()=>self::flush(),PHP_INT_MAX);
        add_action('admin_notices',function(){
            $pending=(array)get_option(self::PENDING,[]);if(!$pending||!current_user_can('manage_options'))return;
            echo '<div class="notice notice-error"><p>'.esc_html(SetupReadiness::text('Attachment preservation is incomplete. Restore the missing source files, then use Resume history in Tools → Resilience. Attachment IDs: ','添付ファイルの保全が未完了です。保存元の不足ファイルを戻し、ツール → Resilienceの「履歴を再開」を実行してください。添付ID: ').implode(', ',array_map('intval',array_keys($pending)))).'</p><ul>';
            foreach((array)get_option(self::ERRORS,[]) as $id=>$reason)if(isset($pending[$id]))echo '<li>'.esc_html((string)$id.' — '.$reason).'</li>';
            echo '</ul></div>';
        });
    }
    /** Reconcile access-only changes and newly recognised registered media too. */
    public static function reconcile(): bool {
        if(!self::enabled())return true;
        global $wpdb;
        $ids=$wpdb->get_col("SELECT ID FROM {$wpdb->posts} WHERE post_type='attachment'");
        if($wpdb->last_error)throw new \RuntimeException('Cannot inspect registered attachments.');
        foreach($ids as $id)self::mark((int)$id);
        self::flush();return !(array)get_option(self::PENDING,[]);
    }
    public static function flush(): void {
        if(!self::enabled()||self::$running)return;
        $lock=self::lock();
        self::$running=true;
        try {
            foreach((array)get_option(self::PENDING,[]) as $id=>$deleted){
                try {
                    self::capture((int)$id,(bool)$deleted);
                    $pending=(array)get_option(self::PENDING,[]);unset($pending[$id]);update_option(self::PENDING,$pending,false);
                    $errors=(array)get_option(self::ERRORS,[]);unset($errors[$id]);update_option(self::ERRORS,$errors,false);
                } catch(\Throwable $e){
                    $errors=(array)get_option(self::ERRORS,[]);$errors[$id]=$e->getMessage();update_option(self::ERRORS,$errors,false);
                }
            }
        } finally {self::$running=false;self::unlock($lock);}
    }
    private static function capture(int $id,bool $deleted): void {
        global $wpdb;$media=[];$resources=[];
        if(!$deleted){
            $post=$wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->posts} WHERE ID=%d AND post_type='attachment'",$id),ARRAY_A);
            if(!$post)throw new \RuntimeException('Attachment registration missing.');
            $rows=$wpdb->get_results($wpdb->prepare("SELECT * FROM {$wpdb->postmeta} WHERE post_id=%d",$id),ARRAY_A);
            if($wpdb->last_error)throw new \RuntimeException('Cannot read attachment definitions.');
            $data=['tables'=>['posts'=>[$post],'postmeta'=>$rows]];$paths=FileScope::paths($data,true);
            if(!$paths)return; // Outside the registered information-file scope.
            $meta=[];foreach($rows as $r){$v=$r['meta_value'];if($r['meta_key']==='_wp_attachment_metadata'&&is_serialized($v))$v=unserialize($v,['allowed_classes'=>false]);$meta[$r['meta_key']]=$v;}
            $rules=array_intersect_key(MediaAccess::current(),$paths);$data['media_access']=$rules;
            $root=realpath(wp_upload_dir()['basedir']);$files=[];
            foreach($paths as $path=>$_){
                $body=MediaAccess::heldBody($path);
                if($body===null){$full=realpath(wp_upload_dir()['basedir'].'/'.substr($path,8));
                    if(!$root||!$full||!str_starts_with($full,$root.DIRECTORY_SEPARATOR)||!is_file($full)||is_link(wp_upload_dir()['basedir'].'/'.substr($path,8)))throw new \RuntimeException('Attachment original or derivative missing: '.$path);
                    if(filesize($full)>32*1024*1024)throw new \RuntimeException('Attachment exceeds 32 MiB.');
                    $body=file_get_contents($full);if($body===false)throw new \RuntimeException('Cannot read attachment.');
                }
                $files[$path]=$body;$resources[$path]=['body'=>base64_encode($body),'type'=>'application/octet-stream'];
            }
            self::assertComplete($data,$files);
            $allowed=['_wp_attached_file','_wp_attachment_metadata','_wp_attachment_image_alt'];
            $media[]=['post'=>$post,'meta'=>array_intersect_key($meta,array_flip($allowed)),'preserved_meta'=>array_diff_key($meta,array_flip($allowed)),'files'=>array_fill_keys(array_keys($paths),null),'access'=>$rules];
        }
        $source=Store::json(['schema'=>self::SCHEMA,'id'=>$id,'deleted'=>$deleted]);
        (new CommentHistory())->enqueue('attachment-'.$id,$source,['post_type'=>'owr_attachment','content_format'=>'attachment-json','attachment_schema'=>self::SCHEMA,'origin_id'=>$id,'title'=>'Attachment #'.$id,'status'=>$deleted?'deleted':'saved','media'=>$media],$resources);
    }
    public static function validate(array $media): void {
        $p=$media['post']??[];$id=(int)($p['ID']??0);
        if($id<=0||($p['post_type']??'')!=='attachment'||!is_array($media['meta']??null)||!is_array($media['files']??null))throw new \RuntimeException('Invalid attachment bundle.');
        $rows=[];foreach($media['meta'] as $key=>$value){
            if(!in_array($key,['_wp_attached_file','_wp_attachment_metadata','_wp_attachment_image_alt'],true))throw new \RuntimeException('Invalid attachment definition.');
            $rows[]=['post_id'=>$id,'meta_key'=>$key,'meta_value'=>is_array($value)?serialize($value):$value];
        }
        $d=['tables'=>['posts'=>[$p],'postmeta'=>$rows],'media_access'=>$media['access']??[]];$paths=FileScope::paths($d,true);
        if(!$paths||array_diff_key($media['files'],$paths))throw new \RuntimeException('Attachment bundle has unregistered files.');
        self::assertComplete($d,$media['files']);
        if(array_diff_key($d['media_access'],$paths))throw new \RuntimeException('Attachment bundle has unrelated viewing conditions.');
        foreach($media['files'] as $ref)if(!is_array($ref)||!isset($ref['key'],$ref['version'],$ref['sha256']))throw new \RuntimeException('Attachment bundle has unconfirmed files.');
    }
    public static function replay(array &$d,array &$files,string $source,array $a,Store $store): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);$id=(int)($v['id']??0);
        if(($v['schema']??'')!==self::SCHEMA||($a['attachment_schema']??'')!==self::SCHEMA||$id<=0||$id!==(int)($a['origin_id']??0)||!is_bool($v['deleted']??null))throw new \RuntimeException('Invalid attachment history.');
        $media=$a['media']??[];if(count($media)!==($v['deleted']?0:1))throw new \RuntimeException('Incomplete attachment history.');
        if($media){self::validate($media[0]);if((int)$media[0]['post']['ID']!==$id)throw new \RuntimeException('Attachment identity mismatch.');}
        $old=$d;$old['tables']['posts']=array_values(array_filter($d['tables']['posts'],fn($p)=>(int)$p['ID']===$id));
        foreach($old['tables']['posts'] as $p)if($p['post_type']!=='attachment')throw new \RuntimeException('Attachment identity conflict.');
        $other=$d;$other['tables']['posts']=array_values(array_filter($d['tables']['posts'],fn($p)=>(int)$p['ID']!==$id));
        foreach(array_diff_key(FileScope::paths($old,true),FileScope::paths($other,true)) as $path=>$_)unset($files[$path],$d['media_access'][$path]);
        $d['tables']['posts']=$other['tables']['posts'];$d['tables']['postmeta']=array_values(array_filter($d['tables']['postmeta'],fn($m)=>(int)$m['post_id']!==$id));
        if($media)SiteSnapshot::applyMedia($d,$files,$media,$store,true);
    }
}
