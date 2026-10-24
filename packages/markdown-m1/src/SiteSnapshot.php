<?php
declare(strict_types=1);
namespace Owr\M1;

/** Portable, complete content baseline. No SQL dump, credentials or source-host dependency. */
final class SiteSnapshot
{
    private const TABLES=['posts','postmeta','terms','term_taxonomy','term_relationships','termmeta','comments','commentmeta'];
    private const OPTIONS=['blogname','blogdescription','show_on_front','page_on_front','page_for_posts','permalink_structure','category_base','tag_base','posts_per_page','posts_per_rss','date_format','time_format','timezone_string','gmt_offset','start_of_week','WPLANG','template','stylesheet','site_icon','default_category','sidebars_widgets','sticky_posts','wp_page_for_privacy_policy','default_comment_status','default_ping_status'];
    public function __construct(private Store $store) {}
    public static function safePath(string $p): void {
        if ($p==='' || str_contains($p,'\\') || str_contains($p,"\0") || str_starts_with($p,'/') || preg_match('~(^|/)\.\.?(/|$)|:~',$p)) throw new \RuntimeException('Unsafe resource path.');
    }
    private static function decode(string $s): mixed {
        return is_serialized($s)?unserialize($s,['allowed_classes'=>false]):$s;
    }
    public static function relocate(mixed $v,string $from,string $to): mixed {
        if (is_array($v)) {foreach($v as &$x)$x=self::relocate($x,$from,$to);return $v;}
        if (is_object($v)) throw new \RuntimeException('Object-valued settings are not portable.');
        if (!is_string($v)) return $v;
        // Boundary prevents rewriting another host with a similar name.
        return preg_replace('~'.preg_quote(rtrim($from,'/'),'~').'(?=/|[\s"\'<>)]|$)~',rtrim($to,'/'),$v);
    }
    private function data(): array {
        global $wpdb;
        $data=['tables'=>[],'options'=>[],'authors'=>[]];
        foreach(self::TABLES as $t) {
            $data['tables'][$t]=$wpdb->get_results('SELECT * FROM `'.$wpdb->$t.'`',ARRAY_A);
            if($wpdb->last_error)throw new \RuntimeException('Cannot read content table '.$t);
        }
        $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($r)=>!in_array($r['meta_key'],['_edit_lock','_edit_last'],true)));
        foreach(self::OPTIONS as $k)$data['options'][$k]=get_option($k);
        foreach($wpdb->get_col("SELECT option_name FROM {$wpdb->options} WHERE option_name LIKE 'widget_%' OR option_name LIKE 'theme_mods_%'") as $k)$data['options'][$k]=get_option($k);
        foreach(array_unique(array_column($data['tables']['posts'],'post_author')) as $id){$u=get_userdata((int)$id);if($u)$data['authors'][(string)$id]=['display_name'=>$u->display_name,'user_nicename'=>$u->user_nicename];}
        if(TableHistory::enabled())TableHistory::baseline($data);
        if(MemberHistory::enabled())$data['membership']=MemberHistory::baseline();
        return $data;
    }
    private function files(string $root,string $prefix,array &$out): void {
        if(!is_dir($root))throw new \RuntimeException('Missing resource root '.$prefix);
        foreach(new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($root,\FilesystemIterator::SKIP_DOTS)) as $f){
            if($f->isLink())throw new \RuntimeException('Symlink not portable: '.$f->getFilename());
            if(!$f->isFile())continue;
            $rel=$prefix.'/'.substr($f->getPathname(),strlen($root)+1);self::safePath($rel);
            if($f->getSize()>32*1024*1024)throw new \RuntimeException('Resource exceeds 32 MiB: '.$rel);
            $out[$rel]=file_get_contents($f->getPathname());
        }
    }
    /** Preserve only CF7's exact deny-all guard; never accept arbitrary upload directives. */
    public static function validateUpload(string $path,string $body): void {
        if(!preg_match('~\.(php[0-9]?|phtml|phar|htaccess)$~i',$path))return;
        $deny="# Apache 2.4+\n<IfModule authz_core_module>\n    Require all denied\n</IfModule>\n\n# Apache 2.2\n<IfModule !authz_core_module>\n    Deny from all\n</IfModule>\n";
        if($path==='uploads/wpcf7_uploads/.htaccess'&&str_replace("\r\n","\n",$body)===$deny)return;
        throw new \RuntimeException('Executable upload is outside portable media scope.');
    }
    public function capture(bool $trusted,array $plugins): array {
        if(!$trusted)throw new \RuntimeException('Administrator must trust the initial site and pause editing.');
        if(get_option('owr_m1_pending')||get_option('owr_m1_comment_pending'))throw new \RuntimeException('Resume pending history first.');
        // Include supported form runtimes in a new trusted baseline; no external worker.
        foreach(array_merge(FormHistory::DEPENDENCIES,[MemberHistory::PLUGIN,TableHistory::PLUGIN]) as $dependency)if(in_array($dependency,(array)get_option('active_plugins'),true)&&!in_array($dependency,$plugins,true))$plugins[]=$dependency;
        $data=$this->data();$files=[];$software=[];
        $theme=get_stylesheet();$parent=get_template();
        foreach(array_unique([$theme,$parent]) as $name){self::safePath($name);$this->files(get_theme_root().'/'.$name,'themes/'.$name,$software);}
        foreach($plugins as $plugin){
            self::safePath($plugin);
            if(!in_array($plugin,(array)get_option('active_plugins'),true))throw new \RuntimeException('Dependency must be an active plugin.');
            $dir=dirname($plugin);if($dir==='.')throw new \RuntimeException('Select a directory-based dependency.');
            $this->files(WP_PLUGIN_DIR.'/'.$dir,'plugins/'.$dir,$software);
        }
        $upload=wp_upload_dir();$this->files($upload['basedir'],'uploads',$files);
        foreach($files as $path=>$body)self::validateUpload($path,$body);
        foreach($data['tables']['postmeta'] as $r)if($r['meta_key']==='_ozmd_source')$files['markdown/'.$r['post_id'].'.md']=$r['meta_value'];
        // Bundling program files avoids thousands of requests; content remains independent files.
        $tmp=tempnam(sys_get_temp_dir(),'owr-site-');$zip=new \ZipArchive();$zip->open($tmp,\ZipArchive::OVERWRITE);$hashes=[];
        ksort($software);foreach($software as $path=>$body){$zip->addFromString($path,$body);$hashes[$path]=hash('sha256',$body);}$zip->close();
        $files['software.zip']=file_get_contents($tmp);unlink($tmp);
        if(Store::json($data)!==Store::json($this->data()))throw new \RuntimeException('Site changed during capture; retry while editing is paused.');
        $files['content.json']=Store::json($data);
        $state=$this->store->latestState();
        $manifest=['schema'=>'owr-site-snapshot-1','origin'=>'administrator_initial','source_url'=>home_url(),
            'wordpress'=>$GLOBALS['wp_version'],'php'=>PHP_VERSION,'through'=>$state['through'],'plugins'=>$plugins,
            'software_hashes'=>$hashes,'excluded_plugins'=>array_values(array_diff((array)get_option('active_plugins'),$plugins)),
            'excluded'=>'Administrator credentials, sessions, reset tokens, cron queues, mail transport and unsupported plugin settings are excluded; WP-Members subscriber password hashes and configured member fields are included when active.'];
        return $this->save($files,$manifest);
    }
    public function save(array $files,array $manifest): array {
        ksort($files);$identity=[];foreach($files as $p=>$body){self::safePath($p);$identity[$p]=hash('sha256',$body);}
        unset($manifest['resources'],$manifest['created_at']);
        $base='site-snapshots/'.hash('sha256',Store::json([$manifest,$identity])).'/';$refs=[];
        $until=gmdate('c',time()+86400*max(1,(int)((new Plugin())->config()['retention_days']??36)));
        foreach($files as $p=>$body){$type=str_ends_with($p,'.md')?'text/markdown':(str_ends_with($p,'.json')?'application/json':'application/octet-stream');$refs[$p]=$this->store->put($base.'resources/'.$p,$body,$type,$until);}
        $manifest['resources']=$refs;
        $ref=$this->store->put($base.'manifest.json',Store::json($manifest),'application/json',$until);
        return ['manifest'=>$ref,'files'=>count($files),'through'=>$manifest['through']];
    }
    public function load(array $ref): array {
        $m=json_decode($this->store->get($ref),true,512,JSON_THROW_ON_ERROR);
        if(($m['schema']??'')!=='owr-site-snapshot-1'||!is_array($m['resources']??null))throw new \RuntimeException('Invalid site manifest.');
        $base=dirname($ref['key']).'/resources/';$files=[];
        foreach($m['resources'] as $p=>$r){self::safePath($p);if($r['key']!==$base.$p)throw new \RuntimeException('Site snapshot depends on another snapshot.');$files[$p]=$this->store->get($r);}
        return [$m,$files];
    }
    /** Checkpoint copies the trusted complete baseline and overlays confirmed content history. */
    public function checkpoint(array $ref): array {
        [$m,$files]=$this->load($ref);[$m,$files]=$this->replay($m,$files);return $this->save($files,$m);
    }
    private function replay(array $m,array $files): array {
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        $rows=$this->store->history((int)$m['through']);$through=(int)$m['through'];
        foreach($rows as $r){
            if($r['sequence']!==++$through)throw new \RuntimeException('History gap.');
            if(($r['attributes']['post_type']??'')==='owr_native'){
                $this->store->get($r['original']['metadata']);
                self::applyMedia($d,$files,$r['attributes']['media']??[],$this->store);
                NativeHistory::replay($d,$files,$this->store->get($r['original']['source']),$r['attributes']);continue;
            }
            if(($r['attributes']['post_type']??'')==='owr_table'){
                $this->store->get($r['original']['metadata']);
                TableHistory::replay($d,$this->store->get($r['original']['source']),$r['attributes']);
                $m['required_tablepress_version']=$r['attributes']['tablepress_version'];continue;
            }
            if(($r['attributes']['post_type']??'')==='owr_member'){
                $this->store->get($r['original']['metadata']);
                MemberHistory::replay($d,$this->store->get($r['original']['source']),$r['attributes']);continue;
            }
            if(($r['attributes']['post_type']??'')==='owr_form'){
                $this->store->get($r['original']['metadata']);
                FormHistory::replay($d,$this->store->get($r['original']['source']),$r['attributes']);
                $m['required_form_plugins']=$r['attributes']['dependencies'];continue;
            }
            if(($r['attributes']['post_type']??'')==='owr_comment'){
                $this->store->get($r['original']['metadata']);
                CommentHistory::replay($d,$this->store->get($r['original']['source']),$r['attributes']);continue;
            }
            $a=$r['attributes'];$id=(string)$a['origin_id'];$type=$a['post_type']??'ozmd_document';$found=false;
            if(!in_array($type,['ozmd_document','page','post'],true)||!in_array($a['status'],['publish','private','draft','pending','trash'],true))throw new \RuntimeException('Unsupported history type or state.');
            $raw=$this->store->get($r['original']['source']);$this->store->get($r['original']['metadata']);
            self::applyMedia($d,$files,$a['media']??[],$this->store);
            $values=['post_title'=>$a['title'],'post_name'=>$a['slug'],'post_status'=>$a['status'],'post_date'=>$a['date'],'post_date_gmt'=>$a['date_gmt']];
            if($type!=='ozmd_document')$values['post_content']=$raw;
            foreach(['post_excerpt','post_parent','menu_order','comment_status','ping_status'] as $key)if(isset($a[$key]))$values[$key]=$a[$key];
            foreach($d['tables']['posts'] as &$p)if((string)$p['ID']===$id){if($p['post_type']!==$type)throw new \RuntimeException('History identity conflicts with baseline.');$p=array_replace($p,$values);$found=true;}unset($p);
            if(!$found){
                $d['tables']['posts'][]=array_replace(['ID'=>$id,'post_author'=>'0','post_date'=>$a['date'],'post_date_gmt'=>$a['date_gmt'],'post_content'=>'','post_title'=>$a['title'],'post_excerpt'=>'','post_status'=>$a['status'],'comment_status'=>'closed','ping_status'=>'closed','post_password'=>'','post_name'=>$a['slug'],'to_ping'=>'','pinged'=>'','post_modified'=>$a['date'],'post_modified_gmt'=>$a['date_gmt'],'post_content_filtered'=>'','post_parent'=>'0','guid'=>$a['origin_url'],'menu_order'=>'0','post_type'=>$type,'post_mime_type'=>'','comment_count'=>'0'],$values);
                $next=max(array_merge([0],array_map('intval',array_column($d['tables']['postmeta'],'meta_id'))))+1;
                foreach(($type==='ozmd_document'?['_ozmd_source'=>'']:[])+['_owr_m1_asset'=>$r['original']['asset']] as $k=>$v)$d['tables']['postmeta'][]=['meta_id'=>(string)$next++,'post_id'=>$id,'meta_key'=>$k,'meta_value'=>$v];
            }
            if($type==='ozmd_document'){
                $files['markdown/'.$id.'.md']=$raw;
                foreach($d['tables']['postmeta'] as &$meta)if((string)$meta['post_id']===$id && $meta['meta_key']==='_ozmd_source')$meta['meta_value']=$raw;unset($meta);
            }else $files['posts/'.$id.'.html']=$raw;
        }
        $files['content.json']=Store::json($d);$m['through']=$through;$m['origin']='confirmed_s3';return [$m,$files];
    }
    public static function applyMedia(array &$d,array &$files,array $mediaRecords,Store $store): void {
            foreach($mediaRecords as $media){
                $attachment=$media['post'];$aid=(string)$attachment['ID'];
                if($attachment['post_type']!=='attachment'||!str_starts_with($attachment['post_mime_type'],'image/'))throw new \RuntimeException('Invalid image record.');
                foreach($media['files'] as $path=>$ref){self::safePath($path);if(!str_starts_with($path,'uploads/')||!preg_match('/\.(jpe?g|png|gif|webp|avif)$/i',$path))throw new \RuntimeException('Invalid image path.');$files[$path]=$store->get($ref);}
                $exists=false;foreach($d['tables']['posts'] as &$ap)if((string)$ap['ID']===$aid){if($ap['post_type']!=='attachment')throw new \RuntimeException('Image identity conflict.');$ap=$attachment;$exists=true;}unset($ap);
                if(!$exists)$d['tables']['posts'][]=$attachment;
                foreach($media['meta'] as $key=>$value){
                    if(!in_array($key,['_wp_attached_file','_wp_attachment_metadata','_wp_attachment_image_alt'],true))throw new \RuntimeException('Unexpected image metadata.');
                    $value=is_array($value)?serialize($value):$value;$exists=false;
                    foreach($d['tables']['postmeta'] as &$am)if((string)$am['post_id']===$aid&&$am['meta_key']===$key){$am['meta_value']=$value;$exists=true;}unset($am);
                    if(!$exists){$next=max(array_merge([0],array_map('intval',array_column($d['tables']['postmeta'],'meta_id'))))+1;$d['tables']['postmeta'][]=['meta_id'=>(string)$next,'post_id'=>$aid,'meta_key'=>$key,'meta_value'=>$value];}
                }
            }
    }
    public function restore(array $ref,bool $replace,string $work): array {
        global $wpdb;
        if(!$replace)throw new \RuntimeException('Explicit replacement of destination content required.');
        if(!empty((new Plugin())->config()['protect'])||get_option('owr_m1_pending'))throw new \RuntimeException('Use a recovery destination with writing protection disabled and no pending history.');
        [$m,$files]=$this->load($ref);[$m,$files]=$this->replay($m,$files);$to=home_url();$from=$m['source_url'];
        if(rtrim($from,'/')===rtrim($to,'/'))throw new \RuntimeException('Refusing to replace the source site.');
        foreach($m['required_form_plugins']??[] as $plugin=>$version){
            FormHistory::checkDependency($plugin,$version);
            if(!in_array($plugin,$m['plugins'],true))$m['plugins'][]=$plugin;
        }
        $runtime=$GLOBALS['wp_version'];
        if(implode('.',array_slice(explode('.',$m['wordpress']),0,2))!==implode('.',array_slice(explode('.',$runtime),0,2))||version_compare($runtime,$m['wordpress'],'<'))throw new \RuntimeException('Use the recorded WordPress release line with the same or a newer maintenance patch.');
        if(!is_dir($work)||!is_writable($work)||realpath($work)===false||str_starts_with(realpath($work),realpath(ABSPATH)))throw new \RuntimeException('Private writable staging directory outside web root required.');
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        $memberPlan=isset($d['membership'])?MemberHistory::plan($d['membership'],$from):[];
        foreach(self::TABLES as $t){if(!isset($d['tables'][$t]))throw new \RuntimeException('Missing table '.$t);$engine=$wpdb->get_row($wpdb->prepare('SHOW TABLE STATUS WHERE Name=%s',$wpdb->$t));if(strtolower($engine->Engine??'')!=='innodb')throw new \RuntimeException('Transactional tables required.');}
        file_put_contents($work.'/software.zip',$files['software.zip']);$zip=new \ZipArchive();if($zip->open($work.'/software.zip')!==true)throw new \RuntimeException('Invalid software bundle.');$program=[];
        for($i=0;$i<$zip->numFiles;$i++){$p=$zip->getNameIndex($i);self::safePath($p);if(!isset($m['software_hashes'][$p])||!preg_match('~^(themes|plugins)/~',$p))throw new \RuntimeException('Unexpected program path.');$body=$zip->getFromIndex($i);if(!hash_equals($m['software_hashes'][$p],hash('sha256',$body)))throw new \RuntimeException('Software mismatch.');$program[$p]=$body;}$zip->close();
        if(isset($m['required_tablepress_version'])){
            $code=$program['plugins/'.TableHistory::PLUGIN]??'';
            if(!preg_match('/Version:\s*([^\s]+)/',$code,$version)||$version[1]!==$m['required_tablepress_version'])throw new \RuntimeException('Create a new trusted baseline after changing TablePress version.');
        }
        if(count($program)!==count($m['software_hashes']))throw new \RuntimeException('Incomplete software bundle.');
        $install=$program;foreach($files as $p=>$body)if(str_starts_with($p,'uploads/'))$install[$p]=$body;
        file_put_contents($work.'/before-content.json',Store::json($this->data()));chmod($work.'/before-content.json',0600);
        $backups=[];
        foreach($install as $p=>$body){$target=WP_CONTENT_DIR.'/'.$p;$parent=dirname($target);if(!is_dir($parent)&&!wp_mkdir_p($parent))throw new \RuntimeException('Cannot create resource directory.');if(is_link($target)||!str_starts_with(realpath($parent).'/',realpath(WP_CONTENT_DIR).'/'))throw new \RuntimeException('Resource escapes destination.');$before=is_file($target)?file_get_contents($target):null;if($before===$body){unset($install[$p]);continue;}if(!is_writable($parent))throw new \RuntimeException('Destination resource directory is not writable: '.$p);$backups[$target]=$before;}
        file_put_contents($work.'/before-files.json',Store::json(array_map(fn($v)=>$v===null?null:base64_encode($v),$backups)));chmod($work.'/before-files.json',0600);
        $oldOptions=[];foreach($d['options'] as $k=>$v)$oldOptions[$k]=get_option($k);$oldOptions['active_plugins']=get_option('active_plugins');
        file_put_contents($work.'/before-options.json',Store::json($oldOptions));chmod($work.'/before-options.json',0600);
        $touched=[];
        try {
            foreach($install as $p=>$body){$target=WP_CONTENT_DIR.'/'.$p;if(file_put_contents($target.'.owr-tmp',$body)!==strlen($body)||!rename($target.'.owr-tmp',$target))throw new \RuntimeException('Resource installation failed.');$touched[]=$target;}
            // Imported authors have no login identity from the lost system and no capabilities.
            $authors=[];foreach($d['authors'] as $id=>$a){$login='owr-author-'.substr(hash('sha256',$from.'|'.$id),0,20);$u=get_user_by('login',$login);$uid=$u?$u->ID:wp_insert_user(['user_login'=>$login,'user_pass'=>wp_generate_password(64,true,true),'display_name'=>$a['display_name'],'user_nicename'=>$a['user_nicename'],'role'=>'']);if(is_wp_error($uid))throw new \RuntimeException($uid->get_error_message());$authors[(string)$id]=$uid;}
            $wpdb->query('START TRANSACTION');
            if(isset($d['membership']))$authors=MemberHistory::install($d['membership'],$memberPlan,$from,$to)+$authors;
            foreach(array_reverse(self::TABLES) as $t)if($wpdb->query('DELETE FROM `'.$wpdb->$t.'`')===false)throw new \RuntimeException('Cannot replace destination content.');
            foreach(self::TABLES as $t)foreach($d['tables'][$t] as $row){
                if($t==='posts')$row['post_author']=$authors[(string)$row['post_author']]??0;
                if($t==='comments')$row['user_id']=$authors[(string)$row['user_id']]??0;
                foreach($row as $k=>$v)if(is_string($v)){if($t==='postmeta'&&$k==='meta_value'&&$row['meta_key']==='_ozmd_source')continue;$value=self::relocate(self::decode($v),$from,$to);$row[$k]=is_serialized($v)?serialize($value):$value;}
                if($wpdb->insert($wpdb->$t,$row)===false)throw new \RuntimeException('Content import failed: '.$t.' '.$wpdb->last_error);
            }
            foreach($d['options'] as $k=>$v){if(!in_array($k,self::OPTIONS,true)&&!in_array($k,TableHistory::OPTIONS,true)&&!str_starts_with($k,'widget_')&&!str_starts_with($k,'theme_mods_'))throw new \RuntimeException('Disallowed option.');if($k==='tablepress_plugin_options'){$options=json_decode($v,true,512,JSON_THROW_ON_ERROR);$options['use_custom_css_file']=false;$v=Store::json($options);}update_option($k,self::relocate($v,$from,$to));}
            $active=array_values(array_unique(array_merge(['ozeki-wordpress-resilience/ozeki-wordpress-resilience.php'],$m['plugins'])));update_option('active_plugins',$active);
            // Re-render sources with the recorded installed Markdown implementation.
            wp_cache_flush();foreach($files as $p=>$raw)if(preg_match('~^markdown/([0-9]+)\.md$~D',$p,$match)&&get_post_type((int)$match[1])==='ozmd_document'){
                (new \OzekiMarkdownDocuments\Content\MarkdownSource())->store((int)$match[1],$raw);
                update_post_meta((int)$match[1],'_owr_m1_origin_url',$from.'/?ozmd_document='.get_post((int)$match[1])->post_name);
            }
            $wpdb->query('COMMIT');wp_cache_flush();delete_option('rewrite_rules');
        }catch(\Throwable $e){$wpdb->query('ROLLBACK');foreach($touched as $p){$body=$backups[$p];if($body===null){if(is_file($p))unlink($p);}else file_put_contents($p,$body);}wp_cache_flush();throw $e;}
        // Raw Markdown stays byte-identical; URLs in rendered output are rebased, not originals.
        update_option('owr_site_origin_url',$from,false);
        update_option('owr_site_restore_result',['manifest'=>$ref,'through'=>$m['through'],'at'=>gmdate('c'),'posts'=>count($d['tables']['posts']),'files'=>count($install),'source_url'=>$from],false);
        return (array)get_option('owr_site_restore_result');
    }
}
