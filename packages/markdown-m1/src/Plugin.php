<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/SaveFailure.php';
require_once __DIR__.'/CheckpointSchedule.php';
require_once __DIR__.'/GfsPolicy.php';
require_once __DIR__.'/SetupReadiness.php';
require_once __DIR__.'/AdminText.php';

final class Plugin
{
    private ?array $active=null;
    private bool $transaction=false;
    private bool $locked=false;
    private bool $restoring=false;
    private const SOURCE='_ozmd_source';
    private const ID='_owr_m1_asset';
    private const CONFIG='owr_m1_config';
    private const PENDING='owr_m1_pending';
    public function boot(): void {
        add_filter('wp_handle_upload_prefilter',[$this,'protectUpload']);
        add_filter('wp_handle_sideload_prefilter',[$this,'protectUpload']);
        add_filter('wp_insert_post_data',[$this,'before'],PHP_INT_MAX,4);
        add_action('wp_after_insert_post',[$this,'after'],PHP_INT_MAX,4);
        add_action('edit_form_after_title',[$this,'token']);
        add_action('admin_menu',function(){add_management_page('Resilience','Resilience','manage_options','owr-m1',[$this,'page']);});
        add_action('admin_post_owr_m1',[$this,'action']);
        add_action('admin_notices',[$this,'notice']);
        add_filter('the_content',[$this,'links'],100);
        add_filter('the_content',[$this,'relocateContent'],101);
        add_action('init',[$this,'scheduleCheckpoints']);
        add_action('owr_m1_checkpoint',[$this,'checkpointTick']);
        register_shutdown_function([$this,'release']);
    }
    public function config(): array { return (array)get_option(self::CONFIG,[]); }
    public static function renderGfsSettings(array $c): void {
        echo '<h3>'.esc_html(AdminText::text('Weekly / monthly / yearly Checkpoints')).'</h3><p>'.esc_html(AdminText::text('Timezone:')).' '.esc_html(wp_timezone()->getName()).''.esc_html(AdminText::text('. Select each schedule independently. Coincident times create one complete Checkpoint with all matching retention labels. Unchanged content is still copied independently.')).'</p>';
        if(!array_key_exists('gfs',$c)&&!empty($c['checkpoint_interval_days']))echo '<p>'.esc_html(AdminText::text('Legacy interval remains active until these settings are saved. Select GFS schedules before saving to replace it.')).'</p>';
        foreach(['weekly'=>AdminText::text('Weekly'),'monthly'=>AdminText::text('Monthly'),'yearly'=>AdminText::text('Yearly')] as $kind=>$label){
            $r=$c['gfs'][$kind]??[];$name='gfs['.$kind.']';
            echo '<fieldset><legend>'.esc_html($label).'</legend><label><input type="checkbox" name="'.esc_attr($name).'[enabled]" '.checked(!empty($r['enabled']),true,false).'>'.esc_html(AdminText::text('Enabled')).'</label> ';
            if($kind==='weekly'){
                echo '<label>'.esc_html(AdminText::text('Weekday')).' <select name="'.esc_attr($name).'[weekday]">';
                foreach([AdminText::text('Sunday'),AdminText::text('Monday'),AdminText::text('Tuesday'),AdminText::text('Wednesday'),AdminText::text('Thursday'),AdminText::text('Friday'),AdminText::text('Saturday')] as $i=>$day)echo '<option value="'.(int)$i.'" '.selected($r['weekday']??0,$i,false).'>'.esc_html($day).'</option>';
                echo '</select></label> ';
            }else{
                if($kind==='yearly')echo '<label>'.esc_html(AdminText::text('Month')).' <input type="number" min="1" max="12" name="'.esc_attr($name).'[month]" value="'.(int)($r['month']??1).'"></label> ';
                echo '<label>'.esc_html(AdminText::text('Day')).''.esc_html($kind==='monthly'?AdminText::text(' (0 = month end)'):'').' <input type="number" min="'.($kind==='monthly'?0:1).'" max="31" name="'.esc_attr($name).'[day]" value="'.(int)($r['day']??1).'"></label> ';
            }
            echo '<label>'.esc_html(AdminText::text('Start time')).' <input type="time" name="'.esc_attr($name).'[time]" value="'.esc_attr($r['time']??'02:00').'"></label> <label>'.esc_html(AdminText::text('Keep for')).' <input type="number" min="1" max="100" name="'.esc_attr($name).'[keep]" value="'.(int)($r['keep']??1).'"> '.esc_html(['weekly'=>AdminText::text('weeks'),'monthly'=>AdminText::text('calendar months'),'yearly'=>AdminText::text('calendar years')][$kind]).'</label></fieldset>';
        }
        echo '<p>'.esc_html(AdminText::text('Missing calendar dates use month end. Retention starts at actual confirmation; an older point keeps its recorded labels when settings change. WP-Cron needs traffic or an existing server cron runner. Late runs show their planned time separately and do not invent missed historical snapshots. Optional S3 deletion protection is separate.')).'</p>';
    }
    /** The temporary original is durable before WordPress moves/registers an image. */
    public function protectUpload(array $file): array {
        if(empty($this->config()['protect']) || !empty($file['error']))return $file;
        $mime=is_file($file['tmp_name']??'')?wp_get_image_mime($file['tmp_name']):false;
        if(!$mime && !str_starts_with((string)($file['type']??''),'image/'))return $file;
        try {
            if(!current_user_can('upload_files'))throw new \RuntimeException('Invalid upload permission.');
            if(!is_file($file['tmp_name']) || filesize($file['tmp_name'])>32*1024*1024)throw new \RuntimeException('Image exceeds 32 MiB.');
            if(!in_array($mime,['image/jpeg','image/png','image/gif','image/webp','image/avif'],true))throw new \RuntimeException('Unsupported image original.');
            $this->store()->put('image-ingress/'.wp_generate_uuid4().'/'.sanitize_file_name($file['name']),file_get_contents($file['tmp_name']),$mime);
        }catch(\Throwable $e){$file['error']='Resilience: image not registered: '.$e->getMessage();update_option('owr_m1_notice',$file['error'],false);}
        return $file;
    }
    /** Freeze the images used by this exact body, not the entire media library. */
    public function mediaForBody(string $body,Store $store,string $base,?array &$resources=null): array {
        global $wpdb;
        $ids=[];$upload=wp_upload_dir();
        preg_match_all('/(?:wp-image-|"id"\s*:\s*)([0-9]+)/',$body,$matches);
        foreach($matches[1] as $id)if(get_post_type((int)$id)==='attachment')$ids[(int)$id]=true;
        preg_match_all('~'.preg_quote($upload['baseurl'],'~').'/[^\s"<>\)]+~',$body,$urls);
        foreach($urls[0] as $url){$url=html_entity_decode($url,ENT_QUOTES,'UTF-8');if(!preg_match('/\.(jpe?g|png|gif|webp|avif)(?:[?#].*)?$/i',$url))continue;$url=preg_replace('/[?#].*$/','',$url);$id=attachment_url_to_postid($url);
            if(!$id){$full=preg_replace('/-\d+x\d+(?=\.[^.]+$)/','',$url);$id=attachment_url_to_postid($full);}
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
            if(!$id)throw new \RuntimeException('Cannot identify local media: '.$url);
            $ids[$id]=true;
        }
        $out=[];$root=realpath($upload['basedir']);
        foreach(array_keys($ids) as $id){
            $p=get_post($id);$meta=wp_get_attachment_metadata($id);
            if(!$p || !str_starts_with($p->post_mime_type,'image/') || !is_array($meta)||empty($meta['file']))throw new \RuntimeException('Image metadata is incomplete.');
            $paths=[$meta['file']];$dir=dirname($meta['file']);$dir=$dir==='.'?'':$dir.'/';
            foreach($meta['sizes']??[] as $size)$paths[]=$dir.$size['file'];
            if(!empty($meta['original_image']))$paths[]=$dir.$meta['original_image'];
            $refs=[];foreach(array_unique($paths) as $path){SiteSnapshot::safePath($path);$full=realpath($upload['basedir'].'/'.$path);
                if(!$full||!str_starts_with($full,$root.DIRECTORY_SEPARATOR)||!is_file($full)||filesize($full)>32*1024*1024)throw new \RuntimeException('Invalid image resource.');
                $mime=wp_get_image_mime($full);if(!in_array($mime,['image/jpeg','image/png','image/gif','image/webp','image/avif'],true))throw new \RuntimeException('Invalid image bytes.');
                if($resources===null)$refs['uploads/'.$path]=$store->put($base.'media/'.$path,file_get_contents($full),$mime);
                else {$resources['uploads/'.$path]=['body'=>base64_encode(file_get_contents($full)),'type'=>$mime];$refs['uploads/'.$path]=null;}
            }
            $row=$wpdb->get_row($wpdb->prepare("SELECT * FROM {$wpdb->posts} WHERE ID=%d",$id),ARRAY_A);
            $out[]=['post'=>$row,'meta'=>['_wp_attached_file'=>get_post_meta($id,'_wp_attached_file',true),'_wp_attachment_metadata'=>$meta,'_wp_attachment_image_alt'=>get_post_meta($id,'_wp_attachment_image_alt',true)],'files'=>$refs];
        }
        return $out;
    }
    public function scheduleCheckpoints(): void {
        wp_clear_scheduled_hook('owr_m1_checkpoint_daily');
        $c=$this->config();$days=(int)($c['checkpoint_interval_days']??0);
        $event=wp_get_scheduled_event('owr_m1_checkpoint');
        if(array_key_exists('gfs',$c)){
            if($event && !empty($event->schedule)){wp_clear_scheduled_hook('owr_m1_checkpoint');$event=false;}
            if(!$c['gfs']){wp_clear_scheduled_hook('owr_m1_checkpoint');delete_option('owr_gfs_due');return;}
            if(!$event){
                $slot=GfsPolicy::next($c['gfs'],time(),wp_timezone());
                update_option('owr_gfs_due',$slot,false);
                $r=wp_schedule_single_event($slot['at'],'owr_m1_checkpoint',[],true);
                if(is_wp_error($r)||$r===false)update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>false,'error'=>'Unable to schedule GFS Checkpoint'],false);
            }
            return;
        }

        if ($event && ($days===0 || !empty($event->schedule))) {wp_clear_scheduled_hook('owr_m1_checkpoint');$event=false;}
        if ($days>0 && !$event) {
            $next=CheckpointSchedule::next(time(),$days,$c['checkpoint_interval_unit']??'days',wp_timezone(),(int)($c['checkpoint_anchor_day']??0));
            $r=wp_schedule_single_event($next,'owr_m1_checkpoint',[],true);
            if(is_wp_error($r)||$r===false)update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>false,'error'=>'Unable to schedule Checkpoint'],false);
        }
    }
    public function checkpointTick(): void {
        $c=$this->config();$slot=null;
        if(array_key_exists('gfs',$c)){
            if(!$c['gfs'])return;
            $slot=get_option('owr_gfs_due');
            if(!is_array($slot)||empty($slot['rules'])||!isset($slot['at'],$slot['timezone'])||$slot['at']>time())return;
        }elseif(empty($c['checkpoint_interval_days']))return;
        try { $this->wholeCheckpoint(null,$slot); } catch (\Throwable $e) {
            update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>false,'error'=>$e->getMessage()],false);
            if($slot!==null)wp_clear_scheduled_hook('owr_m1_checkpoint');
            $this->scheduleCheckpoints();
            return;
        }
        if (!empty($this->config()['cleanup_enabled'])) {
            try {$this->runSiteCleanup(true);} catch (\Throwable $e) {update_option('owr_site_cleanup_status',['at'=>gmdate('c'),'ok'=>false,'error'=>$e->getMessage()],false);}
        }
        if($slot!==null)wp_clear_scheduled_hook('owr_m1_checkpoint');
        $this->scheduleCheckpoints();
    }
    public function wholeCheckpoint(?array $ref=null,?array $slot=null): array {
        try{
            $this->lock();
            if(get_option(self::PENDING)||get_option('owr_m1_comment_pending'))throw new \RuntimeException('Resolve pending operations before creating a Checkpoint.');
            $store=$this->store();
            if($slot!==null){
                foreach($store->siteSnapshots() as $point)if(($point['scheduled_at']??null)===gmdate('c',$slot['at'])){
                    (new SiteSnapshot($store))->load($point['ref']);
                    $result=['manifest'=>$point['ref'],'through'=>$point['through'],'already_confirmed'=>true];
                    update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>true,'result'=>$result],false);return $result;
                }
            }
            if($ref===null){$points=$store->siteSnapshots();if(!$points)throw new \RuntimeException('Create an initial complete-site snapshot first.');$ref=end($points)['ref'];}
            $result=(new SiteSnapshot($store))->checkpoint($ref,$slot);
            update_option('owr_site_snapshot_result',$result,false);
            update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>true,'result'=>$result],false);
            return $result;
        }catch(\Throwable $e){update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>false,'error'=>$e->getMessage()],false);throw $e;}
        finally{$this->release();}
    }
    public function runSiteCleanup(bool $automatic=false,string $hash=''): array {
        try{
            $this->lock();
            if(get_option(self::PENDING)||get_option('owr_m1_comment_pending'))throw new \RuntimeException('Resolve pending operations before deletion.');
            if($automatic){
                if(empty($this->config()['cleanup_enabled']))throw new \RuntimeException('Automatic cleanup disabled.');
                $cutoff=max(0,time()-max(0,(int)($this->config()['cleanup_keep_days']??90))*DAY_IN_SECONDS);
                $plan=$this->store()->siteCleanupPreview($cutoff);$hash=$plan['hash'];
            }else{
                $plan=(array)get_option('owr_site_cleanup_preview',[]);
                if(empty($plan['hash'])||!hash_equals($plan['hash'],$hash))throw new \RuntimeException('Preview complete-site deletion first.');
                $cutoff=$plan['cutoff_timestamp'];
            }
            $result=$this->store()->siteCleanup($cutoff,$hash);
            update_option('owr_site_cleanup_status',['at'=>gmdate('c')]+$result,false);
            delete_option('owr_site_cleanup_preview');return $result;
        }catch(\Throwable $e){update_option('owr_site_cleanup_status',['at'=>gmdate('c'),'ok'=>false,'error'=>$e->getMessage()],false);throw $e;}
        finally{$this->release();}
    }
    public function previewSiteCleanup(): array {
        try {
            $this->lock();
            if(get_option(self::PENDING) || get_option('owr_m1_comment_pending'))throw new \RuntimeException('Resume article and shared pending operations before calculating candidates.');
            $days=max(0,min(3650,(int)($this->config()['cleanup_keep_days']??90)));
            $plan=$this->store()->siteCleanupPreview(max(0,time()-$days*DAY_IN_SECONDS));
        } catch(\Throwable $e) {
            $plan=['read_only'=>true,'at'=>gmdate('c'),'error'=>$e->getMessage()];
        } finally {$this->release();}
        update_option('owr_site_cleanup_preview',$plan,false);
        return $plan;
    }
    public function renewSiteRetention(): array {
        update_option('owr_site_retention_result',['status'=>'running','at'=>gmdate('c')],false);
        try{
            $this->lock();
            if(get_option(self::PENDING)||get_option('owr_m1_comment_pending'))throw new \RuntimeException('Resume pending operations before renewing Checkpoint protection.');
            $result=$this->store()->renewLatestSiteRetention();
            update_option('owr_site_retention_result',$result,false);return $result;
        }catch(\Throwable $e){
            update_option('owr_site_retention_result',['status'=>'failed','at'=>gmdate('c'),'error'=>$e->getMessage()],false);throw $e;
        }finally{$this->release();}
    }
    public static function renderSiteCleanup(array $plan): void {
        echo '<h2>'.esc_html(AdminText::text('Complete-site Checkpoint retention preview')).'</h2><p>'.esc_html(AdminText::text('The retention window applies to recovery points, not the age of articles or images. Keeps the latest Checkpoint, the baseline at the window boundary, and required history and resources. Unknown resources are retained. S3-locked resources wait until protection expires. Preview itself does not delete anything.')).'</p>';
        if(!$plan)return;
        if(isset($plan['error']))echo '<p><strong>'.esc_html(AdminText::text('Candidates not calculated:')).'</strong> '.esc_html($plan['error']).'</p>';
        else {
            echo '<p>'.esc_html(AdminText::text('History ').$plan['from'].' → '.$plan['through'].AdminText::text('; subsequent records: ').$plan['tail_count'].AdminText::text('; cutoff: ').$plan['cutoff']).'</p>';
            echo '<p>'.esc_html($plan['limitation']).'</p>';
            echo '<p>'.esc_html($plan['inventory_note']).'</p>';
            echo '<details><summary>'.esc_html(AdminText::text('Retained Checkpoints (')).''.count($plan['keep']).')</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'.esc_html(Store::json($plan['keep'])).'</pre></details>';
            foreach(['retained'=>AdminText::text('Assets to retain'),'candidates'=>AdminText::text('Deletion candidates (not executed)'),'blocked'=>AdminText::text('Deletion not established / retained')] as $key=>$label){
                echo '<details><summary>'.esc_html($label).' ('.count($plan[$key]).')</summary><table class="widefat" style="table-layout:fixed;overflow-wrap:anywhere"><thead><tr><th>'.esc_html(AdminText::text('S3 key / version')).'</th><th>'.esc_html(AdminText::text('Reason')).'</th></tr></thead><tbody>';
                foreach($plan[$key] as $v)echo '<tr><td>'.esc_html($v['key']).'<br>'.esc_html($v['version']).'</td><td>'.esc_html($v['reason']).'</td></tr>';
                echo '</tbody></table></details>';
            }
        }
        echo '<details><summary>'.esc_html(AdminText::text('Detailed retention preview JSON')).'</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'.esc_html(Store::json($plan)).'</pre></details>';
    }
    public function previewCleanup(): array {
        try {
            $this->lock();
            if (get_option(self::PENDING)) throw new \RuntimeException('Resume pending history before cleanup.');
            $days=max(0,min(3650,(int)($this->config()['cleanup_keep_days']??90)));
            $plan=$this->store()->cleanupPlan(max(0,time()-$days*DAY_IN_SECONDS));
            update_option('owr_m1_cleanup_preview',$plan,false);return $plan;
        } finally {$this->release();}
    }
    public function runCleanup(bool $automatic=false, string $hash=''): array {
        try {
            $this->lock();
            if (get_option(self::PENDING)) throw new \RuntimeException('Resume pending history before cleanup.');
            if ($automatic) {
                if (empty($this->config()['cleanup_enabled'])) throw new \RuntimeException('Automatic cleanup disabled.');
                $days=max(0,min(3650,(int)($this->config()['cleanup_keep_days']??90)));
                $plan=$this->store()->cleanupPlan(max(0,time()-$days*DAY_IN_SECONDS));
            } else {
                $plan=(array)get_option('owr_m1_cleanup_preview',[]);
                if (!$plan || !hash_equals((string)$plan['hash'],$hash)) throw new \RuntimeException('Preview cleanup before confirming.');
            }
            $result=$this->store()->cleanup((int)$plan['cutoff'],(string)$plan['hash']);
            update_option('owr_m1_cleanup_status',['at'=>gmdate('c')]+$result,false);
            delete_option('owr_m1_cleanup_preview');return $result;
        } finally {$this->release();}
    }
    public function checkpoint(): array {
        try {
            $this->lock();
            if (get_option(self::PENDING)) throw new \RuntimeException('Resume pending formal history before creating a Checkpoint.');
            $result=$this->store()->createCheckpoint();
            update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>true,'result'=>$result],false);
            return $result;
        } finally { $this->release(); }
    }
    public function initialSnapshot(bool $trusted): array {
        if (!$trusted) throw new \RuntimeException('The administrator must accept the current published Markdown assets as the trusted starting point and pause editing during capture.');
        try {
            $this->lock();$materials=[];$ids=[];
            if (get_option(self::PENDING)) throw new \RuntimeException('Resume pending formal history first.');
            foreach (get_posts(['post_type'=>'ozmd_document','post_status'=>'publish','numberposts'=>-1,'orderby'=>'ID','order'=>'ASC']) as $p) {
                $asset=(string)get_post_meta($p->ID,self::ID,true);
                if ($asset==='') $asset=hash('sha256',home_url().'|ozmd_document|'.$p->ID);
                $attrs=['title'=>$p->post_title,'slug'=>$p->post_name,'status'=>$p->post_status,'date'=>$p->post_date,'date_gmt'=>$p->post_date_gmt,'origin_id'=>$p->ID,'origin_url'=>get_permalink($p)];
                $materials[$asset]=['source'=>(string)get_post_meta($p->ID,self::SOURCE,true),'row'=>['schema'=>'owr-md-history-1','sequence'=>0,'attributes'=>$attrs]];
                $ids[$p->ID]=$asset;
            }
            $result=$this->store()->createInitialSnapshot($materials);
            foreach ($ids as $id=>$asset) update_post_meta($id,self::ID,$asset);
            update_option('owr_m1_checkpoint_status',['at'=>gmdate('c'),'ok'=>true,'result'=>$result],false);
            return $result;
        } finally {$this->release();}
    }
    public function store(): Store {
        $c=$this->config();
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
        if (!SetupReadiness::accepted($c)) throw new \RuntimeException(SetupReadiness::text('Save storage settings and confirm the terms before connecting.','接続する前に、保存先の設定と利用条件の確認を保存してください。'));
        if (empty($c['bucket']) || empty($c['prefix']) || empty($c['region'])) throw new \RuntimeException('Configure the S3 bucket, region and dedicated prefix first.');
        return $this->storeForSetup($c);
    }
    private function storeForSetup(array $c): Store {
        $options=apply_filters('owr_m1_s3_options',['version'=>'latest','region'=>$c['region'],'http'=>['connect_timeout'=>5,'timeout'=>30],'retries'=>1]);
        $client=new \Aws\S3\S3Client($options);
        return new Store($client,$c);
    }
    private function fingerprint(int $id): string {
        $p=get_post($id);
        return hash('sha256',Store::json([$p?->post_title,$p?->post_name,$p?->post_status,$p?->post_modified_gmt,$p?->post_content,(string)get_post_meta($id,self::SOURCE,true)]));
    }
    public function token($post): void {
        if ($post->post_type==='ozmd_document' && !empty($this->config()['protect']))
            echo '<input type="hidden" name="owr_m1_base" value="'.esc_attr($this->fingerprint((int)$post->ID)).'">';
    }
    private function lock(): void {
        global $wpdb;
        if ($this->locked) return;
        if ((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 5)','owr-m1-'.$wpdb->prefix))!==1) throw new \RuntimeException('Another protected save is running. Retry after it completes.');
        $this->locked=true;
        foreach ([$wpdb->posts,$wpdb->postmeta,$wpdb->options] as $table) {
            $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));
            if (strtolower((string)$engine)!=='innodb') throw new \RuntimeException('M1 requires InnoDB for posts, postmeta and options.');
        }
    }
    private function begin(): void {
        global $wpdb;
        if ($wpdb->query('START TRANSACTION')===false) throw new \RuntimeException('Cannot start WordPress transaction.');
        $this->transaction=true;
    }
    private function commitDb(): void {
        global $wpdb;
        if ($wpdb->query('COMMIT')===false) throw new \RuntimeException('WordPress commit failed.');
        $this->transaction=false;
    }
    public function release(): void {
        global $wpdb;
        if ($this->transaction) { $wpdb->query('ROLLBACK');$this->transaction=false;wp_cache_flush(); }
        if ($this->locked) {$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)','owr-m1-'.$wpdb->prefix));$this->locked=false;}
    }
    private function stop(\Throwable $e): never {
        $this->release();
        update_option('owr_m1_notice','Last article save failed; inspect pending history before retrying the editor. Reason: '.$e->getMessage(),false);
        // api-fetch needs a nonempty error code to retain the reason in the block editor.
        $message='Resilience: '.wp_strip_all_tags($e->getMessage()).' WordPress was not confirmed. Check Resilience for pending history before retrying.';
        // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- WP_Error is required by the REST error handler; its message is escaped at construction.
        wp_die(new \WP_Error('owr_save_failed',esc_html($message)),'Resilience',['response'=>409,'code'=>'owr_save_failed','back_link'=>true]);
        exit;
    }
    public function before(array $data,array $postarr,array $unsanitized,bool $update): array {
        if ($this->restoring || !in_array($data['post_type'],['ozmd_document','page','post'],true) || empty($this->config()['protect']) || (defined('DOING_AUTOSAVE') && DOING_AUTOSAVE)) return $data;
        $id=(int)($postarr['ID']??0);
        $old=$id?get_post($id):null;
        $markdown=$data['post_type']==='ozmd_document';
        $editor=$markdown && isset($_POST['ozmd_source'],$_POST['ozmd_source_nonce']);
        $wasProtected=$id?(string)get_post_meta($id,self::ID,true):'';
        if ($data['post_status']!=='publish' && !$wasProtected && $old?->post_status!=='publish') return $data;
        // Scheduling remains a normal WordPress operation, outside automatic M1 protection.
        if ($data['post_status']==='future' || $old?->post_status==='future') return $data;
        try {
            // REST, classic editor and trash/untrash have already passed their core permission checks.
            if (($id && !current_user_can('edit_post',$id)) || (!$id && !current_user_can(get_post_type_object($data['post_type'])->cap->create_posts))) throw new \RuntimeException('Invalid save permission.');
            if ($editor && !wp_verify_nonce(sanitize_text_field(wp_unslash(is_string($_POST['ozmd_source_nonce'])?$_POST['ozmd_source_nonce']:'')),'ozmd_save_markdown_source')) throw new \RuntimeException('Invalid Markdown save permission.');
            if ($this->active) throw new \RuntimeException('Nested protected saves are unsupported.');
            $this->lock();
            if (get_option(self::PENDING)) throw new \RuntimeException('A previous WordPress save is awaiting formal S3 history. Resume it in Tools → Resilience first.');
            if (get_option('owr_m1_comment_pending')) throw new \RuntimeException('Resume pending comment history in Tools → Resilience first.');
            clean_post_cache($id);
            $wasProtected=$id?(string)get_post_meta($id,self::ID,true):'';
            if ($wasProtected && $editor && (!isset($_POST['owr_m1_base']) || !hash_equals($this->fingerprint($id),sanitize_text_field(wp_unslash($_POST['owr_m1_base']))))) throw new \RuntimeException('The document changed since this editor was opened. Reload before saving.');
            $source=$markdown?($editor?self::validatedMarkdown(wp_unslash($_POST['ozmd_source'])):(string)get_post_meta($id,self::SOURCE,true)):(string)wp_unslash($data['post_content']);
            if (strlen($source)>5*1024*1024 || str_contains($source,"\0") || !preg_match('//u',$source)) throw new \RuntimeException('Markdown must be UTF-8 without NUL, at most 5 MiB.');
            $asset=$wasProtected?(string)$wasProtected:wp_generate_uuid4();$operation=wp_generate_uuid4();
            $store=$this->store();$state=$store->latestState();$sequence=$state['through']+1;
            $attributes=['title'=>wp_unslash($data['post_title']),'slug'=>wp_unslash($data['post_name']),'status'=>$data['post_status'],'date'=>$data['post_date'],'date_gmt'=>$data['post_date_gmt'],'origin_id'=>$id,'origin_url'=>get_permalink($id)];
            $attributes['post_type']=$data['post_type'];
            $attributes['content_format']=$markdown?'markdown':'wordpress-block-html';
            foreach(['post_excerpt','post_parent','menu_order','comment_status','ping_status'] as $key)$attributes[$key]=wp_unslash($data[$key]);
            // Gutenberg separately posts legacy meta boxes after REST body saving.
            // Skip only a matching, already-confirmed body; metadata hooks still run.
            if(!$markdown && isset($_GET['meta-box-loader']) && sanitize_key(wp_unslash($_POST['action']??''))==='editpost'
                && self::sameConfirmedArticle($state['assets'][$asset]??null,$source,$attributes)){
                $this->release();return $data;
            }
            $attributes['media']=$this->mediaForBody($source,$store,'originals/'.$asset.'/'.$operation.'/');
            $original=$store->prepare($asset,$operation,$source,$attributes);
            $this->active=['id'=>$id,'original'=>$original,'sequence'=>$sequence,'attributes'=>$attributes,'store'=>$store];
            $this->begin();
        } catch (\Throwable $e) { $this->stop($e); }
        return $data;
    }
    public static function sameConfirmedArticle(?array $row,string $source,array $attributes): bool {
        if(!$row || ($row['original']['source']['sha256']??'')!==hash('sha256',$source))return false;
        foreach($attributes as $key=>$value)if(!array_key_exists($key,$row['attributes']??[]) || (string)$row['attributes'][$key] !== (string)$value)return false;
        return true;
    }
    public function after(int $id,\WP_Post $post,bool $update,?\WP_Post $before): void {
        if (!$this->active || ($this->active['id']!==0 && $id!==$this->active['id']) || $post->post_type!==$this->active['attributes']['post_type']) return;
        try {
            $a=$this->active;$source=$post->post_type==='ozmd_document'?(string)get_post_meta($id,self::SOURCE,true):$post->post_content;
            if (hash('sha256',$source)!==$a['original']['source']['sha256'] || $post->post_title!==$a['attributes']['title'] || $post->post_status!==$a['attributes']['status'] || $post->post_name!==$a['attributes']['slug']) throw new \RuntimeException('WordPress did not apply the saved original exactly.');
            update_post_meta($id,self::ID,$a['original']['asset']);
            $attrs=$a['attributes'];$attrs['origin_url']=get_permalink($id);$attrs['origin_id']=$id;
            $record=['schema'=>'owr-md-history-1','sequence'=>$a['sequence'],'original'=>$a['original'],'attributes'=>$attrs,'confirmed_at'=>gmdate('c')];
            if (!update_option(self::PENDING,['id'=>$id,'fingerprint'=>$this->fingerprint($id),'record'=>$record],false)) throw new \RuntimeException('Cannot persist pending confirmation.');
            $this->commitDb();$this->active=null;
            try {$a['store']->commit($record);delete_option(self::PENDING);delete_option('owr_m1_notice');}
            catch (\Throwable $e) {update_option('owr_m1_notice','WordPress saved; formal S3 history is pending. Use Resume history. No successful history has been assumed. Reason: '.$e->getMessage(),false);}
            $this->release();
        } catch (\Throwable $e) {$this->active=null;$this->stop($e);}
    }
    public function resume(): void {
        $this->lock();
        try {
            $pending=get_option(self::PENDING);
            if (!$pending) return;
            clean_post_cache($pending['id']);
            if (!hash_equals($pending['fingerprint'],$this->fingerprint($pending['id']))) throw new \RuntimeException('Pending content no longer matches WordPress. Do not certify it as successful.');
            $this->store()->commit($pending['record']);delete_option(self::PENDING);delete_option('owr_m1_notice');
        } finally {$this->release();}
    }
    public function restore(array $sequences): array {
        if (!class_exists('OzekiMarkdownDocuments\\Content\\MarkdownSource')) throw new \RuntimeException('Install and activate Ozeki Markdown Documents first.');
        $store=$this->store();$selected=[];
        foreach ($store->history() as $row) if (in_array((string)$row['sequence'],$sequences,true)) {
            if(in_array($row['attributes']['post_type']??'',['owr_comment','owr_form','owr_member','owr_table','owr_native','owr_acf'],true))throw new \RuntimeException('Use complete site recovery for comments, forms, memberships, tables, article relationships and ACF fields.');
            $asset=$row['original']['asset'];
            if (isset($selected[$asset])) throw new \RuntimeException('Select only one version per document.');
            $source=$store->originalSource($row['original']);
            $store->get($row['original']['metadata']);
            if (strlen($source)>5*1024*1024 || !preg_match('//u',$source) || str_contains($source,"\0")) throw new \RuntimeException('Invalid Markdown original.');
            $selected[$asset]=[$row,$source];
        }
        if (count($selected)!==count($sequences) || !$selected) throw new \RuntimeException('Select valid formal versions.');
        return $this->restoreRecords($selected);
    }
    public function restoreSite(?string $checkpoint): array {
        $store=$this->store();$state=$store->recoveryState($checkpoint);$selected=[];
        foreach ($state['assets'] as $asset=>$row) {
            if(in_array($row['attributes']['post_type']??'',['owr_comment','owr_form','owr_member','owr_table','owr_native','owr_acf'],true))throw new \RuntimeException('Use complete site recovery for comment/form/member/table/ACF history.');
            $source=$store->originalSource($row['original']);$store->get($row['original']['metadata']);
            if (strlen($source)>5*1024*1024 || !preg_match('//u',$source) || str_contains($source,"\0")) throw new \RuntimeException('Invalid Markdown original.');
            $selected[$asset]=[$row,$source];
        }
        if (!$selected) throw new \RuntimeException('No confirmed documents to restore.');
        return $this->restoreRecords($selected);
    }
    private function restoreRecords(array $selected): array {
        if (!class_exists('OzekiMarkdownDocuments\\Content\\MarkdownSource')) throw new \RuntimeException('Install and activate Ozeki Markdown Documents first.');
        $this->lock();$this->restoring=true;$result=[];
        try {
            $this->begin();
            foreach ($selected as $asset=>[$row,$source]) {
                $attr=$row['attributes'];
                if (!in_array($attr['status'],['publish','private','draft','pending','trash'],true)) throw new \RuntimeException('Unsupported recorded status.');
                $type=$attr['post_type']??'ozmd_document';
                if(!in_array($type,['ozmd_document','page','post'],true))throw new \RuntimeException('Unsupported post type.');
                $existing=get_posts(['post_type'=>$type,'post_status'=>['publish','private','draft','pending','trash'],'meta_key'=>self::ID,'meta_value'=>$asset,'fields'=>'ids','posts_per_page'=>2]);
                if (count($existing)>1) throw new \RuntimeException('Duplicate document identity.');
                $args=['post_type'=>$type,'post_title'=>$attr['title'],'post_name'=>$attr['slug'],'post_status'=>$attr['status'],'post_date'=>$attr['date'],'post_date_gmt'=>$attr['date_gmt']];
                if($type!=='ozmd_document')$args['post_content']=$source;
                foreach(['post_excerpt','post_parent','menu_order','comment_status','ping_status'] as $key)if(isset($attr[$key]))$args[$key]=$attr[$key];
                if ($existing) $args['ID']=$existing[0];
                $id=wp_insert_post(wp_slash($args),true);
                if (is_wp_error($id)) throw new \RuntimeException($id->get_error_message());
                if($type==='ozmd_document')(new \OzekiMarkdownDocuments\Content\MarkdownSource())->store($id,$source);
                update_post_meta($id,self::ID,$asset);
                update_post_meta($id,'_owr_m1_origin_url',$attr['origin_url']);
                update_post_meta($id,'_owr_m1_origin_id',$attr['origin_id']);
                $p=get_post($id);
                if ($p->post_title!==$attr['title'] || $p->post_status!==$attr['status'] || $p->post_name!==$attr['slug'] || ($type==='ozmd_document'?get_post_meta($id,self::SOURCE,true):$p->post_content)!==$source) throw new \RuntimeException('Restore did not match the selected original (possibly a slug collision).');
                $result[]=['asset'=>$asset,'sequence'=>$row['sequence'],'post_id'=>$id,'sha256'=>hash('sha256',$source),'status'=>$p->post_status];
            }
            update_option('owr_m1_restore_result',$result,false);$this->commitDb();
        } finally {$this->restoring=false;$this->release();}
        return $result;
    }
    /** Reject malformed input without changing the bytes of the independent original. */
    public static function validatedMarkdown(mixed $source): string {
        if(!is_string($source) || strlen($source)>5*1024*1024 || str_contains($source,"\0") || !preg_match('//u',$source))throw new \RuntimeException('Markdown must be UTF-8 without NUL, at most 5 MiB.');
        // Markdown is archival text, never evaluated or emitted here as HTML.
        // Ozeki Markdown Documents renders it; our admin views escape their output.
        return $source;
    }
    /** Validate the complete reference before recording it or reading from S3. */
    public static function snapshotReference(mixed $json): array {
        if(!is_string($json) || strlen($json)>4096)throw new \RuntimeException('Invalid snapshot reference.');
        $ref=json_decode($json,true,8,JSON_THROW_ON_ERROR);
        if(!is_array($ref) || count($ref)!==3 || !isset($ref['key'],$ref['version'],$ref['sha256'])
            || !is_string($ref['key']) || !preg_match('~^site-snapshots/[a-f0-9]{64}/manifest\.json$~D',$ref['key'])
            || !is_string($ref['version']) || $ref['version']==='null' || !preg_match('~^[A-Za-z0-9+/_=.-]{1,1024}$~D',$ref['version'])
            || !is_string($ref['sha256']) || !preg_match('/^[a-f0-9]{64}$/D',$ref['sha256']))throw new \RuntimeException('Invalid snapshot reference.');
        return ['key'=>$ref['key'],'version'=>$ref['version'],'sha256'=>$ref['sha256']];
    }
    /** Alter URL attributes only; preserve HTML already rendered by core/shortcodes. */
    public function relocateContent(string $html): string {
        $from=get_option('owr_site_origin_url');
        $to=esc_url_raw(home_url(),['http','https']);
        if(!is_string($from) || $from==='' || !$to || esc_url_raw($from,['http','https'])!==$from)return $html;
        $fromUploads=get_option('ozeki_resilience_origin_upload_url');
        if(!is_string($fromUploads)||esc_url_raw($fromUploads,['http','https'])!==$fromUploads)$fromUploads=null;
        $toUploads=wp_upload_dir()['baseurl'];
        $processor=new \WP_HTML_Tag_Processor($html);
        while($processor->next_tag()){
            foreach(['href','src','action','poster','cite','data','srcset'] as $attribute){
                $value=$processor->get_attribute($attribute);
                if(!is_string($value))continue;
                $rebased=SiteSnapshot::relocate($value,$from,$to,$fromUploads,$toUploads);
                if($rebased!==$value)$processor->set_attribute($attribute,$attribute==='srcset'?$rebased:esc_url_raw($rebased,['http','https']));
            }
        }
        // WP_HTML_Tag_Processor escapes changed attribute values. Do not strip
        // forms/embeds from unrelated HTML emitted by earlier content filters.
        return $processor->get_updated_html();
    }
    public function links(string $html): string {
        // Remap rendered links only. Canonical .md bytes are never rewritten.
        $posts=get_posts(['post_type'=>'ozmd_document','post_status'=>['publish','private','draft','pending'],'meta_key'=>'_owr_m1_origin_url','numberposts'=>-1]);
        foreach ($posts as $p) {
            $old=(string)get_post_meta($p->ID,'_owr_m1_origin_url',true);
            if ($old!=='') $html=str_replace(['href="'.esc_attr($old).'"','href="'.esc_attr($old).'#'],['href="'.esc_url(get_permalink($p)).'"','href="'.esc_url(get_permalink($p)).'#'],$html);
        }
        return $html;
    }
    public static function renderCaptureFailure(array $error): void {
        if(!$error)return;
        echo '<div class="notice notice-error"><p><strong>'.esc_html(AdminText::text('Last recorded capture / queue-registration failure')).'</strong> — '.esc_html((string)($error['at']??'')).' / '.esc_html((string)($error['context']??'')).': '.esc_html((string)($error['reason']??'')).'</p><p>'.esc_html(AdminText::text('This is a diagnostic, not a saved recovery payload or proof of a currently pending operation. Queue count zero does not resolve it. Inspect the affected operation and S3 history. Resume history applies only to existing queued payloads; otherwise correct the cause and save the affected data again. Later unrelated saves do not clear this historical notice. If the database cannot record the error, this notice may be unavailable.')).'</p></div>';
    }
    public function notice(): void {
        if (!current_user_can('manage_options')) return;
        $failure=(array)get_option(SaveFailure::OPTION,[]);
        if($failure){
            $screen=function_exists('get_current_screen')?get_current_screen():null;
            if($screen && $screen->id==='tools_page_owr-m1')self::renderCaptureFailure($failure);
            else echo '<div class="notice notice-error"><p>'.esc_html(SetupReadiness::text('Resilience: a content protection operation needs attention.','Resilience：保護処理で確認が必要な項目があります。')).' <a href="'.esc_url(admin_url('tools.php?page=owr-m1')).'">'.esc_html(SetupReadiness::text('View details','詳細を確認')).'</a></p></div>';
        }
        if (get_option(self::PENDING)) echo '<div class="notice notice-warning"><p>'.esc_html(AdminText::text('Resilience: WordPress saved, S3 formal history pending. This operation is not yet included in recovery. ')).'<a href="'.esc_url(admin_url('tools.php?page=owr-m1')).'">'.esc_html(AdminText::text('Resume history')).'</a>.</p></div>';
    }
    public function action(): void {
        if (!current_user_can('manage_options')) wp_die('Forbidden',403);
        check_admin_referer('owr_m1');
        try {
            $action=sanitize_key(wp_unslash($_POST['operation']??''));
            if ($action==='configure') {
                if (get_option(self::PENDING) || get_option('owr_m1_comment_pending')) throw new \RuntimeException('Resume pending history before changing storage.');
                $old=$this->config();
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
                if(!isset($_POST['confirm_terms']))throw new \RuntimeException(SetupReadiness::text('Review the terms and select the confirmation checkbox before saving settings.','利用条件を読み、確認欄にチェックしてから設定を保存してください。'));
                $c=[];foreach (['bucket','region','prefix','owner'] as $key) $c[$key]=sanitize_text_field(wp_unslash($_POST[$key]??''));
                foreach([
                    'bucket'=>['/^[a-z0-9.-]{3,63}$/D',SetupReadiness::text('Enter the S3 bucket name without s3://.','bucketにS3バケット名を入力してください。s3://は付けません。')],
                    'region'=>['/^[a-z0-9-]+$/D',SetupReadiness::text('Enter the bucket region, for example ap-northeast-1.','regionにバケットのリージョンを入力してください（例：ap-northeast-1）。')],
                    'prefix'=>['~^[a-zA-Z0-9/_-]+/$~D',SetupReadiness::text('Enter a dedicated prefix ending in /, for example sites/my-site/.','prefixにサイト専用の保存先を入力してください（例：sites/my-site/）。末尾の/も必要です。')],
                    'owner'=>['/^(|[0-9]{12})$/D',SetupReadiness::text('Enter the owner account ID as 12 digits, or leave it blank.','ownerには所有者の12桁のアカウントIDを入力するか、空欄にしてください。')],
                ] as $key=>[$pattern,$message])if(!preg_match($pattern,$c[$key]))throw new \RuntimeException($message);
                $c['setup_version']=1;
                $c['setup_role']=sanitize_key(wp_unslash($_POST['setup_role']??'source'))==='recovery'?'recovery':'source';
                $c['terms_version']=SetupReadiness::TERMS;
                $c['terms_confirmed_at']=gmdate('c');
                $c['terms_confirmed_by']=get_current_user_id();
                $c['protect']=isset($_POST['protect']);
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
                if($c['protect'] && $c['setup_role']==='recovery')throw new \RuntimeException(SetupReadiness::text('Keep protection disabled on a recovery destination.','復旧先では保護を無効にしてください。'));
                if($c['protect'] && (empty($old['protect']) || SetupReadiness::identity($c)!==SetupReadiness::identity($old))){
                    SetupReadiness::requireStart($c);
                    $this->storeForSetup($c)->checkSetupStorage();
                }
                $c['retention_days']=max(0,min(3650,(int)sanitize_text_field(wp_unslash($_POST['retention_days']??'0'))));
                $gfs=wp_unslash($_POST['gfs']??[]);
                if(!is_array($gfs))throw new \RuntimeException('Invalid GFS settings.');
                $c['gfs']=GfsPolicy::normalize($gfs);$c['checkpoint_interval_days']=0;
                $c['cleanup_enabled']=isset($_POST['cleanup_enabled']);
                $c['cleanup_keep_days']=max(0,min(3650,(int)sanitize_text_field(wp_unslash($_POST['cleanup_keep_days']??'90'))));
                if ($c['cleanup_enabled'] && !$c['gfs']) throw new \RuntimeException('Set a Checkpoint interval before enabling automatic cleanup.');
                update_option(self::CONFIG,$c,false);
                delete_option('owr_m1_cleanup_preview');
                delete_option('owr_site_cleanup_preview');
                wp_clear_scheduled_hook('owr_m1_checkpoint');
                $this->scheduleCheckpoints();
            } elseif ($action==='setup_check') {
                $c=$this->config();
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
                if(!SetupReadiness::accepted($c))throw new \RuntimeException(SetupReadiness::text('Save storage settings and confirm the terms first.','先に保存先の設定と利用条件の確認を保存してください。'));
                $r=['identity'=>SetupReadiness::identity($c),'at'=>gmdate('c'),'ok'=>false];
                try {
                    $this->store()->checkSetupStorage();
                    $r['ok']=true;$r['message']=SetupReadiness::text('Connection and versioning confirmed.','接続とバージョン管理を確認しました。');
                } catch (\Throwable $e) {
                    $r['message']=$e->getMessage();
                }
                update_option('owr_setup_storage',$r,false);
            } elseif ($action==='resume') { $this->resume(); (new CommentHistory())->resume(); }
            elseif ($action==='restore') $this->restore(array_map('sanitize_text_field',(array)wp_unslash($_POST['sequences']??[])));
            elseif ($action==='checkpoint') $this->checkpoint();
            elseif ($action==='site_cleanup_preview') $this->previewSiteCleanup();
            elseif ($action==='site_cleanup_execute') {
                if(!isset($_POST['confirm_cleanup']))throw new \RuntimeException('Confirm deletion of the previewed expired recovery resources.');
                $this->runSiteCleanup(false,sanitize_text_field(wp_unslash($_POST['cleanup_hash']??'')));
            }
            elseif ($action==='site_retention_renew') $this->renewSiteRetention();
            elseif ($action==='initial_snapshot') {
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
                if(($this->config()['setup_role']??'source')==='recovery')throw new \RuntimeException(SetupReadiness::text('This is a recovery destination. Select an existing Checkpoint instead.','このサイトは復旧先です。既存のCheckpointを選択してください。'));
                $this->initialSnapshot(isset($_POST['trust_initial']));
            }
            elseif ($action==='whole_initial') {
                $c=$this->config();
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal diagnostic data; the admin output escapes the message at its HTML sink.
                if(($c['setup_role']??'source')==='recovery')throw new \RuntimeException(SetupReadiness::text('This is a recovery destination. Select an existing Checkpoint instead.','このサイトは復旧先です。既存のCheckpointを選択してください。'));
                SetupReadiness::requireLocal();
                // Repeat the read-only check; cached UI results never authorize a write.
                $this->store()->checkSetupStorage();
                $result=(new SiteSnapshot($this->store()))->capture(isset($_POST['trust_initial']),[]);
                update_option('owr_setup_baseline',SetupReadiness::baselineRecord($c,$result['manifest']),false);
                update_option('owr_site_snapshot_result',$result,false);
            }
            elseif ($action==='whole_checkpoint') {
                $ref=self::snapshotReference(wp_unslash($_POST['site_ref']??''));
                $this->wholeCheckpoint($ref);
            }
            elseif ($action==='whole_restore') {
                $attempt=['status'=>'running','at'=>gmdate('c')];
                try {
                    SiteSnapshot::writeOption('owr_site_restore_attempt',$attempt,false);
                    $end=wp_unslash($_POST['site_through']??'');
                    if(!is_string($end)||!preg_match('/^(0|[1-9][0-9]*)$/D',$end)||filter_var($end,FILTER_VALIDATE_INT)===false)throw new \RuntimeException('Select a valid formal history end number.');
                    $target=(int)$end;$attempt['requested_through']=$target;
                    $ref=self::snapshotReference(wp_unslash($_POST['site_ref']??''));
                    if(!is_array($ref))throw new \RuntimeException('Invalid snapshot reference.');
                    $attempt['manifest']=$ref;SiteSnapshot::writeOption('owr_site_restore_attempt',$attempt,false);
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_mkdir -- Recovery uses private local staging, restrictive OS permissions and same-filesystem replacement/rollback; paths are validated. These are restored resources, not plugin operational data.
                    $work=sys_get_temp_dir().'/owr-site-restore-'.bin2hex(random_bytes(8));if(!mkdir($work,0700))throw new \RuntimeException('Cannot create private staging directory.');
                    $result=(new SiteSnapshot($this->store()))->restore($ref,isset($_POST['replace_site']),$work,$target);
                    SiteSnapshot::writeOption('owr_site_restore_attempt',['status'=>'success']+$result,false);
                } catch (\Throwable $e) {
                    $message=$e->getMessage();
                    try { SiteSnapshot::writeOption('owr_site_restore_attempt',array_merge($attempt,['status'=>'failed','at'=>gmdate('c'),'error'=>$message]),false); }
                    catch (\Throwable $recordError) { $message.=' | Failure record could not be saved: '.$recordError->getMessage().'. Stored results may belong to an earlier attempt.'; }
                    // The current response remains authoritative even if the database cannot store the failure.
                    wp_die(esc_html('Site recovery failed: '.$message),'Site recovery failed',['response'=>500,'back_link'=>true]);
                    return;
                }
            }
            elseif ($action==='cleanup_preview') $this->previewCleanup();
            elseif ($action==='cleanup_execute') {
                if (!isset($_POST['confirm_cleanup'])) throw new \RuntimeException('Confirm permanent deletion of the previewed versions.');
                $this->runCleanup(false,sanitize_text_field(wp_unslash($_POST['cleanup_hash']??'')));
            }
            elseif ($action==='restore_site') $this->restoreSite(!empty($_POST['checkpoint'])?sanitize_text_field(wp_unslash($_POST['checkpoint'])):null);
            else throw new \RuntimeException('Unknown action.');
            delete_option('owr_m1_error');
        } catch (\Throwable $e) {update_option('owr_m1_error',$e->getMessage(),false);}
        wp_safe_redirect(admin_url('tools.php?page=owr-m1'));exit;
    }
    /** Render only recorded facts; a failed/latest attempt never inherits old success counts. */
    public static function renderSiteResult(array $attempt,array $success,array $snapshot,array $snapshots=[]): void {
        echo '<h3>'.esc_html(AdminText::text('Last site-wide recovery result')).'</h3>';
        $r=$attempt?:$success;
        if(!$r){echo '<p>'.esc_html(AdminText::text('No site-wide recovery recorded.')).'</p>';}
        else {
            $status=$attempt?($attempt['status']??'unknown'):(isset($success['at'],$success['posts'])?'success':'unknown');
            $labels=['success'=>AdminText::text('Success'),'failed'=>AdminText::text('Failed'),'running'=>AdminText::text('Started — completion not confirmed'),'unknown'=>AdminText::text('Status unknown')];
            echo '<p role="status"><strong>'.esc_html($labels[$status]??$labels['unknown']).'</strong></p>';
            $rows=[AdminText::text('Recorded at (UTC)')=>$r['at']??AdminText::text('Not recorded'),AdminText::text('Checkpoint / snapshot key')=>$r['manifest']['key']??AdminText::text('Not recorded'),AdminText::text('S3 Version ID')=>$r['manifest']['version']??AdminText::text('Not recorded')];
            $base=isset($r['checkpoint_through'])?(int)$r['checkpoint_through']:null;
            foreach($snapshots as $item)if(($item['ref']??null)===($r['manifest']??null)){$base=(int)$item['through'];$rows[AdminText::text('Recovery point type')]=$item['origin'];break;}
            $rows[AdminText::text('Checkpoint includes history through')]=$base===null?AdminText::text('Not available'):(string)$base;
            $rows[AdminText::text('Requested formal history end')]=isset($r['requested_through'])?(string)$r['requested_through']:AdminText::text('Not recorded (older result)');
            if($status==='success'){
                $end=isset($r['through'])?(int)$r['through']:null;
                $rows[AdminText::text('Applied formal history through')]=$end===null?AdminText::text('Not recorded'):(string)$end;
                $rows[AdminText::text('Subsequent history records')]=$base===null||$end===null||$end<$base?AdminText::text('Not available'):($end===$base?AdminText::text('None'):($base+1).'–'.$end.' ('.($end-$base).AdminText::text(' records)'));
                $rows[AdminText::text('Restored post records (all post types)')]=isset($r['posts'])?(string)$r['posts']:AdminText::text('Not recorded');
                $rows[AdminText::text('Files written / replaced')]=isset($r['files'])?(string)$r['files']:AdminText::text('Not recorded');
            }else{
                $rows[AdminText::text('Applied history / recovery counts')]=AdminText::text('Not confirmed; do not infer zero changes or completed rollback.');
                if(isset($r['error']))$rows[AdminText::text('Failure reason')]=$r['error'];
            }
            echo '<table class="widefat striped"><tbody>';
            foreach($rows as $label=>$value)echo '<tr><th scope="row">'.esc_html($label).'</th><td style="overflow-wrap:anywhere">'.esc_html($value).'</td></tr>';
            echo '</tbody></table><p>'.esc_html(AdminText::text('Post records include pages, attachments, revisions and plugin post types; this is not a count of public articles. Matching existing files are reused, so zero files written does not mean no files were recovered. History records are not unique user edits.')).'</p>';
        }
        if(($attempt['status']??(isset($success['at'])?'success':''))==='success' && isset($r['application_report'])){
            $report=$r['application_report'];
            echo '<h4>'.esc_html(AdminText::text('Preserved in S3 — not automatically applied')).'</h4><p>'.esc_html((string)$report['count']).esc_html(AdminText::text(' item(s). Rules: ')).esc_html($report['rules']).''.esc_html(AdminText::text('. Original resources remain unchanged; omission is not data deletion.')).'</p><ul>';
            foreach($report['not_applied'] as $item)echo '<li>'.esc_html($item['item']).' — '.esc_html($item['reason']).'</li>';
            echo '</ul>';
        }
        echo '<details><summary>'.esc_html(AdminText::text('Detailed JSON — latest attempt, last successful recovery and snapshot')).'</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere;max-height:32em;overflow:auto">'.esc_html(Store::json(['latest_attempt'=>$attempt,'last_successful_recovery'=>$success,'last_snapshot'=>$snapshot])).'</pre></details>';
    }
    private function form(string $operation): void {
        echo '<form id="owr-action-'.esc_attr($operation).'" method="post" action="'.esc_url(admin_url('admin-post.php')).'"><input type="hidden" name="action" value="owr_m1"><input type="hidden" name="operation" value="'.esc_attr($operation).'">';wp_nonce_field('owr_m1');
    }
    /** Read-only summary: local pending data is never treated as S3 confirmation. */
    public static function renderSaveStatus(?array $history, string $readError, array $pending, array $queue, string $notice, string $queueError, bool $protect, array $captureError=[]): void {
        echo '<h2>'.esc_html(AdminText::text('Save protection status')).'</h2><p>'.esc_html(AdminText::text('Protection setting:')).' '.esc_html($protect?AdminText::text('Enabled'):AdminText::text('Disabled')).''.esc_html(AdminText::text('. This setting alone does not prove that all site changes are protected.')).'</p>';
        if($history===null)echo '<p role="alert">'.esc_html(AdminText::text('S3 formal history could not be read. Last confirmation is unknown:')).' '.esc_html($readError).'</p>';
        elseif(!$history)echo '<p>'.esc_html(AdminText::text('No confirmed formal history in this prefix. This does not mean no snapshot exists.')).'</p>';
        else {
            $last=$history[count($history)-1];
            echo '<table class="widefat striped"><tbody>';
            foreach([AdminText::text('Last confirmed sequence')=>$last['sequence']??AdminText::text('Unknown'),AdminText::text('Confirmed at (UTC)')=>$last['confirmed_at']??AdminText::text('Not recorded'),AdminText::text('Asset')=>$last['original']['asset']??AdminText::text('Not recorded'),AdminText::text('Title')=>$last['attributes']['title']??AdminText::text('Not recorded'),AdminText::text('Recorded state')=>$last['attributes']['status']??AdminText::text('Not recorded')] as $k=>$v)echo '<tr><th>'.esc_html($k).'</th><td>'.esc_html((string)$v).'</td></tr>';
            echo '</tbody></table>';
        }
        echo '<p>'.esc_html(AdminText::text('Formal history confirmation records a completed S3 save. This display reads history only: it does not re-fetch or verify all referenced originals now. Original retrieval status: not checked by this display.')).'</p>';
        $details=0;foreach($queue as $entry)if(($entry['attributes']['post_type']??$entry['record']['attributes']['post_type']??'')==='owr_native')$details++;
        echo '<p>'.esc_html(AdminText::text('Pending article body:')).' '.($pending?1:0).esc_html(AdminText::text('; pending article details (images/categories/tags/deletion): ')).(int)$details.esc_html(AdminText::text('; other shared operations: ')).(count($queue)-$details).''.esc_html(AdminText::text('. Body confirmation does not confirm the entire editing session or its related operations.')).'</p>';
        self::renderCaptureFailure($captureError);
        $count=($pending?1:0)+count($queue);
        echo '<p>'.esc_html(AdminText::text('Locally pending operations:')).' '.(int)$count.'</p>';
        if($count){
            echo '<p role="alert"><strong>'.esc_html(AdminText::text('Resume history required.')).'</strong> '.esc_html(AdminText::text('These operations are not confirmed for recovery. Resume uses the existing saved payload and article-state checks; do not create a replacement operation to bypass a failure.')).'</p><table class="widefat striped"><tr><th>'.esc_html(AdminText::text('Operation / asset')).'</th><th>'.esc_html(AdminText::text('Type')).'</th><th>'.esc_html(AdminText::text('Title / state')).'</th></tr>';
            $entries=$queue;if($pending)$entries=['article'=>$pending['record']??[]]+$entries;
            foreach($entries as $key=>$entry){$a=$entry['attributes']??[];$o=$entry['original']??[];echo '<tr><td>'.esc_html((string)($entry['operation']??$o['operation']??$key)).' / '.esc_html((string)($entry['asset']??$o['asset']??AdminText::text('Not recorded'))).'</td><td>'.esc_html((string)($a['post_type']??AdminText::text('Not recorded'))).'</td><td>'.esc_html((string)($a['title']??AdminText::text('Not recorded'))).' / '.esc_html((string)($a['status']??AdminText::text('Not recorded'))).'</td></tr>';}
            echo '</table>';
        }else echo '<p>'.esc_html(AdminText::text('No locally pending operations. This is not a guarantee of unsupported changes or operations lost before local capture.')).'</p>';
        foreach([AdminText::text('Last recorded article/image save notice')=>$notice,AdminText::text('Shared adapter queue: last recorded error')=>$queueError] as $label=>$value)if($value!=='')echo '<p role="alert">'.esc_html($label).': '.esc_html($value).'</p>';
        if($count && $notice==='' && $queueError==='')echo '<p>'.esc_html(AdminText::text('No failure reason was recorded; pending state still requires inspection and resume.')).'</p>';
        echo '<p>'.esc_html(AdminText::text('Recovery adopts only confirmed S3 history. If the source is lost before confirmation, omit that operation. An old error alone does not establish a current pending operation. Checkpoint, recovery and other administration errors are shown separately below.')).'</p>';
    }
    private function setupSettings(): void {
        echo '<h2 id="owr-storage">'.esc_html(AdminText::text('Storage and optional scheduling settings')).'</h2>';
        $c=$this->config();$this->form('configure');
        echo '<p><label>'.esc_html(SetupReadiness::text('Use this site to: ','このサイトの用途：')).'<select name="setup_role"><option value="source" '.selected($c['setup_role']??'source','source',false).'>'.esc_html(SetupReadiness::text('Protect this site','このサイトを保護')).'</option><option value="recovery" '.selected($c['setup_role']??'source','recovery',false).'>'.esc_html(SetupReadiness::text('Recover another site','別サイトを復旧')).'</option></select></label></p>';
        foreach (['bucket','region','prefix','owner'] as $key) echo '<p><label>'.esc_html(SetupReadiness::text($key,['bucket'=>'バケット名（bucket）','region'=>'リージョン（region）','prefix'=>'サイト専用の保存先（prefix）','owner'=>'所有者のアカウントID（owner）'][$key])).' <input name="'.esc_attr($key).'" value="'.esc_attr((string)($c[$key]??'')).'"></label></p>';
        echo '<p><label><input type="checkbox" name="protect" '.checked(!empty($c['protect']),true,false).'>'.esc_html(AdminText::text('Protect supported operations (one writer per prefix)')).'</label></p>';
        $terms='https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/terms-of-use'.(str_starts_with(determine_locale(),'ja')?'-ja':'').'.md';
        echo '<p><a href="'.esc_url($terms).'">'.esc_html(SetupReadiness::text('Terms of use and saved content','利用条件と保存対象')).'</a></p><p>'.esc_html(SetupReadiness::text('Supported site content is sent to your specified Amazon S3 storage. Your AWS contract and storage charges apply. Recovery reads from that storage.','保存対象のサイト情報を、指定したAmazon S3へ送信します。AWSの契約・利用料金は利用者の負担です。復旧時は同じ保存先から読み取ります。')).'</p>';
        echo '<p><label><input type="checkbox" name="confirm_terms" required>'.esc_html(SetupReadiness::text('I have reviewed the terms and saved content, and approve access to the specified Amazon S3 storage for saving or recovery.','利用条件と保存対象を確認し、保存・復旧のために指定したAmazon S3へ接続することを了承しました。')).'</label></p>';
        echo '<details><summary>'.esc_html(SetupReadiness::text('Optional: schedules, retention and cleanup','任意：定期保存・保持期間・自動整理')).'</summary>';
        self::renderGfsSettings($c);
        echo '<p><label>'.esc_html(AdminText::text('Optional S3 deletion protection in days (0 = do not request a lock)')).' <input type="number" min="0" max="3650" name="retention_days" value="'.(int)($c['retention_days']??0).'"></label></p><p>'.esc_html(AdminText::text('Bucket defaults and existing locks still apply. Changing this value does not shorten existing locks. Locked expired points wait; protection is never bypassed.')).'</p>';
        echo '<p><label>'.esc_html(AdminText::text('Detailed history recovery window in days (0 = latest Checkpoint and required tail)')).' <input type="number" name="cleanup_keep_days" min="0" max="3650" value="'.(int)($c['cleanup_keep_days']??90).'"></label></p><p><label><input type="checkbox" name="cleanup_enabled" '.checked(!empty($c['cleanup_enabled']),true,false).'>'.esc_html(AdminText::text('Automatically clean expired versions after successful scheduled Checkpoint checks')).'</label></p>';echo '</details>';submit_button(AdminText::text('Save settings'));echo '</form>';
        $this->form('setup_check');submit_button(SetupReadiness::text('Check storage','保存先を確認'));echo '</form>';
        $check=(array)get_option('owr_setup_storage',[]);if(($check['identity']??'')===SetupReadiness::identity($c))echo '<p role="status">'.esc_html(AdminText::message((string)($check['message']??''))).'</p>';
    }
    public function page(): void {
        if (!current_user_can('manage_options')) return;
        echo '<div class="wrap"><h1>'.esc_html(AdminText::text('Resilience — Site recovery')).'</h1><p>'.esc_html(AdminText::text('Normal Markdown, Page and Post editing → complete S3 originals → formal history → WordPress reconstruction.')).'</p>';
        SetupReadiness::render($this->config());
        $this->setupSettings();
        if ($error=get_option('owr_m1_error')) echo '<p role="alert">'.esc_html(AdminText::message($error)).'</p>';
        if(!SetupReadiness::accepted($this->config())){echo '</div>';return;}
        echo '<h2>'.esc_html(AdminText::text('Recovery boundary')).'</h2><p>'.esc_html(AdminText::text('Recovery uses a trusted snapshot / Checkpoint and only operations confirmed in S3 formal history. An original saved to S3 or a successful WordPress write alone does not confirm an operation. If history remains pending when the source is lost, omit that operation: an unconfirmed new article is absent; an unconfirmed update leaves the previous confirmed version. Do not infer success from prepared originals.')).'</p><p>'.esc_html(AdminText::text('Prepare the destination WordPress, required plugins and S3 access as administrator tasks. Recovery runs when requested; continuous replication is not required. Recorded publication status is preserved. Network exposure and DNS remain the administrator’s responsibility.')).'</p>';
        $history=null;$historyReadError='';
        try{$history=$this->store()->history();}catch(\Throwable $e){$historyReadError=$e->getMessage();}
        self::renderSaveStatus($history,$historyReadError,(array)get_option(self::PENDING,[]),(array)get_option('owr_m1_comment_pending',[]),(string)get_option('owr_m1_notice',''),(string)get_option('owr_m1_comment_error',''),!empty($this->config()['protect']),(array)get_option(SaveFailure::OPTION,[]));
        if(get_option(self::PENDING)||get_option('owr_m1_comment_pending')){$this->form('resume');submit_button(AdminText::text('Resume history'));echo '</form>';}
        if (get_option(self::PENDING)) echo '<p role="alert"><strong>'.esc_html(AdminText::text('WordPress applied; S3 formal history pending.')).'</strong> '.esc_html(AdminText::text('This operation is not yet part of the recovery state. If the source remains available, use Resume history below to verify and confirm it.')).'</p>';
        if ($error=get_option('owr_m1_error')) echo '<p role="alert">'.esc_html(AdminText::message($error)).'</p>';
        echo '<p>'.esc_html(SetupReadiness::text('Prepare WordPress, themes and required plugins from trusted distributors. Recovery restores information assets, not software from S3; the destination theme and active plugins remain unchanged.','WordPress・テーマ・必要なプラグインは信頼できる配布元から準備してください。復旧するのは情報資産です。S3からソフトウェアを配置せず、復旧先のテーマと有効なプラグインを維持します。')).'</p>';
        echo '<h2>'.esc_html(AdminText::text('Site-wide recovery — primary workflow')).'</h2><p>'.esc_html(AdminText::text('Select a complete site snapshot / Checkpoint; recovery includes its subsequent formal history. This replaces destination content, including supported articles, media and site relationships, while preserving destination administrator credentials and infrastructure. Initial capture requires a trusted source and paused editing.')).'</p><p>'.esc_html(AdminText::text('Later Checkpoints use the S3 baseline and confirmed Markdown, Page and Post changes, including supported referenced images and trash/untrash operations. Later theme, menu, template and arbitrary plugin changes are not captured by these save adapters; they require a new trusted baseline. Mail transport and administrative plugin settings are not copied.')).'</p>';
        echo '<p>'.esc_html(AdminText::text('TablePress: include the active plugin in an initial snapshot. Complete-site recovery preserves table IDs, cells, display settings and confirmed add/update/delete operations. Pending S3 history is not a recovery candidate; use Resume history after a storage failure.')).'</p>';
        echo '<p>'.esc_html(AdminText::text('WP-Members core subscribers: create an initial snapshot with WP-Members active. Complete-site recovery restores confirmed member profiles, password hashes and restrictions; it does not overwrite unrelated destination accounts or send mail. Privileged/custom roles and paid extensions are excluded.')).'</p>';
        if(($this->config()['setup_role']??'source')!=='recovery') { $this->form('whole_initial');echo '<label><input type="checkbox" name="trust_initial" required>'.esc_html(AdminText::text('I trust the whole current site and have paused editing.')).'</label>';submit_button(AdminText::text('Create complete initial snapshot'));echo '</form>'; }
        try{
            $siteSnapshots=$this->store()->siteSnapshots();
            $ends=[];foreach($siteSnapshots as $item)$ends[(int)$item['through']]=AdminText::text('Checkpoint boundary');
            if($ends)foreach($this->store()->history(min(array_keys($ends))) as $row)$ends[(int)$row['sequence']]=($row['confirmed_at']??'').' / '.($row['attributes']['title']??$row['original']['asset']??'').' / '.($row['attributes']['status']??'');
            ksort($ends);
            foreach(['whole_checkpoint'=>AdminText::text('Create complete Checkpoint'),'whole_restore'=>AdminText::text('Restore complete site')] as $op=>$label){
                $this->form($op);echo '<label>'.esc_html(AdminText::text('Checkpoint')).' <select name="site_ref" required>';
                foreach($siteSnapshots as $item)echo '<option value="'.esc_attr(Store::json($item['ref'])).'">'.esc_html($item['origin'].' / '.gmdate('c',$item['created']).' / '.implode(', ',array_keys($item['gfs']??[])).AdminText::text(' / history ').$item['through'].' / '.$item['ref']['key']).'</option>';
                echo '</select></label>';
                if($op==='whole_restore'){
                    echo '<label>'.esc_html(AdminText::text('Formal history end')).' <select name="site_through" required>';
                    foreach($ends as $number=>$description)echo '<option value="'.(int)$number.'"'.($number===array_key_last($ends)?' selected':'').'>'.esc_html($number.' / '.$description).'</option>';
                    echo '</select></label><p>'.esc_html(AdminText::text('Choose an end at or after the selected Checkpoint. Only confirmed records through that number are applied; later changes are excluded. The displayed end is fixed for this request. History records are not necessarily complete user editing sessions.')).'</p><label><input type="checkbox" name="replace_site" required>'.esc_html(AdminText::text('Replace all destination content with this site (a private local rollback copy is retained).')).'</label>';
                }
                submit_button($label);echo '</form>';
            }
        }catch(\Throwable $e){echo '<p>'.esc_html($e->getMessage()).'</p>';}
        self::renderSiteResult((array)get_option('owr_site_restore_attempt',[]),(array)get_option('owr_site_restore_result',[]),(array)get_option('owr_site_snapshot_result',[]),$siteSnapshots??[]);
        $next=wp_next_scheduled('owr_m1_checkpoint');
        echo '<p>'.esc_html(AdminText::text('Next complete-site Checkpoint (UTC):')).' '.esc_html($next?gmdate('c',$next):AdminText::text('Disabled')).'</p><pre>'.esc_html(Store::json((array)get_option('owr_m1_checkpoint_status',[]))).'</pre>';
        self::renderSiteCleanup((array)get_option('owr_site_cleanup_preview',[]));
        $this->form('site_cleanup_preview');submit_button(AdminText::text('Preview complete-site retention'));echo '</form>';
        $sitePlan=(array)get_option('owr_site_cleanup_preview',[]);
        if(!empty($sitePlan['hash'])&&!empty($sitePlan['inventory_complete'])&&!empty($sitePlan['candidates'])){
            $this->form('site_cleanup_execute');
            echo '<input type="hidden" name="cleanup_hash" value="'.esc_attr($sitePlan['hash']).'"><label><input type="checkbox" required name="confirm_cleanup">'.esc_html(AdminText::text('Delete only the previewed expired Checkpoints and resources, preserving retained recovery points')).'</label>';
            submit_button(AdminText::text('Delete expired complete-site resources'));echo '</form>';
        }
        echo '<pre>'.esc_html(Store::json((array)get_option('owr_site_cleanup_status',[]))).'</pre>';

        echo '<h2>'.esc_html(AdminText::text('Legacy asset-only cleanup — not complete-site cleanup')).'</h2><p>'.esc_html(AdminText::text('This separate earlier path uses asset snapshots. It does not implement complete-site retention. Do not use it to clean a complete-site stream.')).'</p>';
        $this->form('cleanup_preview');submit_button(AdminText::text('Preview expired versions'));echo '</form>';
        $preview=(array)get_option('owr_m1_cleanup_preview',[]);
        if ($preview) {
            echo '<pre>'.esc_html(Store::json($preview)).'</pre>';
            $this->form('cleanup_execute');echo '<input type="hidden" name="cleanup_hash" value="'.esc_attr($preview['hash']).'"><label><input type="checkbox" required name="confirm_cleanup">'.esc_html(AdminText::text('Permanently delete only the previewed eligible versions')).'</label>';submit_button(AdminText::text('Delete previewed versions'));echo '</form>';
        }
        echo '<pre>'.esc_html(Store::json((array)get_option('owr_m1_cleanup_status',[]))).'</pre>';
        echo '<details><summary>'.esc_html(AdminText::text('Supplementary asset snapshots and recovery — not site-wide recovery')).'</summary><p>'.esc_html(AdminText::text('This earlier asset-level path restores recorded text and attributes from an asset snapshot and later formal history. It does not restore media files, themes, menus or all site relationships. It updates matching asset identities or creates missing records; unrelated destination content remains. Use the site-wide workflow above for a complete site recovery within supported coverage.')).'</p>';
        if(($this->config()['setup_role']??'source')!=='recovery') { $this->form('initial_snapshot');echo '<p><label><input type="checkbox" required name="trust_initial">'.esc_html(AdminText::text('I accept the current published Markdown documents as the trusted initial state and have paused editing during capture. Use an unused history stream.')).'</label></p>';submit_button(AdminText::text('Create initial snapshot'));echo '</form>'; }
        $next=wp_next_scheduled('owr_m1_checkpoint');
        echo '<p>'.esc_html(AdminText::text('Next scheduled check (UTC):')).' '.esc_html($next?gmdate('c',$next):AdminText::text('Disabled')).'</p><pre>'.esc_html(Store::json((array)get_option('owr_m1_checkpoint_status',[]))).'</pre>';
        $this->form('checkpoint');submit_button(AdminText::text('Create Checkpoint now'));echo '</form>';
        try {
            $keys=$this->store()->checkpoints();$this->form('restore_site');
            echo '<select name="checkpoint"><option value="">'.esc_html(AdminText::text('All formal history (no Checkpoint)')).'</option>';
            foreach (array_reverse($keys) as $i=>$key) echo '<option value="'.esc_attr($key).'" '.selected($i,0,false).'>'.esc_html($key).'</option>';
            echo '</select>';submit_button(AdminText::text('Restore assets from Checkpoint + later history'));echo '</form>';
        } catch (\Throwable $e) {echo '<p>'.esc_html($e->getMessage()).'</p>';}
        echo '</details>';
        if (get_option(self::PENDING)||get_option('owr_m1_comment_pending')) {$this->form('resume');submit_button(AdminText::text('Resume history'));echo '</form>';}
        if(get_option('owr_m1_comment_pending'))echo '<p role="alert">'.esc_html(AdminText::text('WordPress comment/form changes applied; S3 history pending. These operations are excluded from recovery until confirmed.')).'</p>';
        if($error=get_option('owr_m1_comment_error'))echo '<p role="alert">'.esc_html(AdminText::message($error)).'</p>';
        echo '<p>'.esc_html(AdminText::text('Comments use a frozen copy of the successful WordPress operation payload. WordPress persistence, S3 original storage and S3 formal history must all succeed before an operation is confirmed for recovery. Pending operations are not confirmed; Resume history retries the frozen payload, not the current comment. The core insert/status callbacks supply a persisted-result snapshot; this is not a pre-write interception. Use complete site recovery for comments.')).'</p>';
        echo '<h2>'.esc_html(AdminText::text('Contact Form 7 and Flamingo')).'</h2><p>'.esc_html(AdminText::text('Completed form definitions and received Flamingo messages use independent JSON originals and the shared pending-history queue. Use complete site recovery with the recorded versions of both plugins installed. Message storage and mail delivery are separate; recovery imports records without sending mail. Received-message edits, spam/ham, trash/restore and permanent deletion, and form deletion are recorded. Received-message changes are captured at request completion. Attachments and address-book entries are outside this adapter.')).'</p>';
        echo '<h2>'.esc_html(AdminText::text('Confirmed formal history / Individual recovery')).'</h2><p>'.esc_html(AdminText::text('This table lists operations confirmed in S3, not prepared originals or pending operations. Individual recovery is supplementary: select one version per asset to restore its text, recorded attributes and publication status. Matching asset identities are updated; missing ones are created. Media files, themes, menus and full site relationships are not restored by this action. Select related documents as needed; use site-wide recovery above for articles with images and site relationships.')).'</p>';
        try {
            if($history===null)throw new \RuntimeException($historyReadError);$this->form('restore');echo '<table class="widefat"><tr><th>'.esc_html(AdminText::text('Select')).'</th><th>'.esc_html(AdminText::text('Order')).'</th><th>'.esc_html(AdminText::text('Document')).'</th><th>'.esc_html(AdminText::text('Status')).'</th><th>'.esc_html(AdminText::text('Raw S3 original')).'</th></tr>';
            foreach (array_reverse($history) as $row) echo '<tr><td><input type="checkbox" name="sequences[]" value="'.(int)$row['sequence'].'"></td><td>'.(int)$row['sequence'].'</td><td>'.esc_html($row['attributes']['title']).'</td><td>'.esc_html($row['attributes']['status']).'</td><td><code>'.esc_html($row['original']['source']['key']).'</code></td></tr>';
            echo '</table>';submit_button(AdminText::text('Restore selected assets (text and attributes)'));echo '</form>';
        } catch (\Throwable $e) {echo '<p>'.esc_html($e->getMessage()).'</p>';}
        echo '<h2>'.esc_html(AdminText::text('Last asset recovery result')).'</h2><pre>'.esc_html(Store::json((array)get_option('owr_m1_restore_result',[]))).'</pre></div>';
    }
}
