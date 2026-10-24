<?php
declare(strict_types=1);
namespace Owr\M1;

/** Core successful-comment callbacks, immutable complete records, shared history order. */
final class CommentHistory
{
    public const PENDING='owr_m1_comment_pending';
    private array $statusOperations=[];
    public function boot(): void {
        // Freeze the successful operation payload, never re-fetch the comment by ID.
        add_action('wp_insert_comment',fn($id,$comment)=>$this->capture((array)$comment),PHP_INT_MIN,2);
        add_action('edit_comment',fn($id,$data)=>$this->capture(['comment_ID'=>$id]+$data),PHP_INT_MIN,2);
        // The status hook itself supplies only an ID. Core already holds the result
        // object and passes it to transition_comment_status; consume that snapshot.
        add_action('wp_set_comment_status',function($id,$status){if($status!=='delete')$this->statusOperations[(int)$id]=true;},PHP_INT_MIN,2);
        add_action('transition_comment_status',function($new,$old,$comment){
            $id=(int)$comment->comment_ID;
            if(!isset($this->statusOperations[$id]))return; // edit_comment already captured edits.
            unset($this->statusOperations[$id]);$this->capture((array)$comment);
        },PHP_INT_MIN,3);
        add_action('deleted_comment',fn($id,$old)=>$this->capture((array)$old,true),PHP_INT_MIN,2);
        add_action('admin_notices',function(){if(current_user_can('manage_options')&&get_option(self::PENDING))echo '<div class="notice notice-warning"><p>Resilience: comment/form/member/table/article-detail changes are awaiting S3 formal history. They are not yet recovery candidates. Use Resume history in Tools → Resilience.</p></div>';});
    }
    private function lock(): string {
        global $wpdb;$name='owr-m1-'.$wpdb->prefix;
        if((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 30)',$name))!==1)throw new \RuntimeException('Comment history is busy; inspect pending history.');
        return $name;
    }
    private function unlock(string $name): void {global $wpdb;$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$name));}
    public function capture(array $operation,bool $deleted=false): void {
        $plugin=new Plugin();if(empty($plugin->config()['protect']))return;
        $id=(int)$operation['comment_ID'];
        // Strings make an immutable value copy before invoking storage or other hooks.
        $data=[];foreach(['comment_ID','comment_post_ID','comment_author','comment_author_email','comment_author_url','comment_author_IP','comment_date','comment_date_gmt','comment_content','comment_karma','comment_approved','comment_agent','comment_type','comment_parent','user_id'] as $k)$data[$k]=(string)$operation[$k];
        $post=get_post((int)$data['comment_post_ID']);
        if(!$post||!in_array($post->post_type,['post','page','ozmd_document'],true)||($post->post_status!=='publish'&&!get_post_meta($post->ID,'_owr_m1_asset',true)))return;
        $source=Store::json(['schema'=>'owr-comment-1','deleted'=>$deleted,'comment'=>$data]);
        $attrs=['post_type'=>'owr_comment','content_format'=>'comment-json','origin_id'=>$id,'origin_url'=>get_permalink($post),'title'=>'Comment #'.$id.' — '.$post->post_title,'status'=>$deleted?'deleted':$data['comment_approved'],'post_id'=>(int)$post->ID];
        $this->enqueue('comment-'.$id,$source,$attrs);
    }
    /** Shared durable queue for successful comment and form operations. */
    public function enqueue(string $asset,string $source,array $attrs,array $resources=[]): void {
        if(strlen($source)>5*1024*1024)throw new \RuntimeException('Operation record exceeds 5 MiB; not confirmed.');
        if($resources && ($attrs['post_type']??'')!=='owr_native')throw new \RuntimeException('Unexpected operation resources.');
        if(strlen(Store::json($resources))>128*1024*1024)throw new \RuntimeException('Operation resources exceed 128 MiB encoded.');
        $name=$this->lock();$operation=wp_generate_uuid4();
        try {
            $queue=(array)get_option(self::PENDING,[]);
            $queue[$operation]=['asset'=>$asset,'operation'=>$operation,'source'=>$source,'attributes'=>$attrs,'resources'=>$resources];
            if(!update_option(self::PENDING,$queue,false))throw new \RuntimeException('Cannot persist comment history pending state.');
            try{$this->flushLocked();}catch(\Throwable $e){update_option('owr_m1_comment_error',$e->getMessage(),false);}
        } finally {$this->unlock($name);}
    }
    public function resume(): void {$name=$this->lock();try{$this->flushLocked();}finally{$this->unlock($name);}}
    private function flushLocked(): void {
        if(get_option('owr_m1_pending'))throw new \RuntimeException('Resume pending article history first.');
        $queue=(array)get_option(self::PENDING,[]);if(!$queue)return;
        $store=(new Plugin())->store();
        foreach($queue as $key=>$entry){
            if(!isset($entry['record'])){
                foreach($entry['resources']??[] as $path=>$resource){
                    SiteSnapshot::safePath($path);$body=base64_decode($resource['body'],true);if($body===false||strlen($body)>32*1024*1024)throw new \RuntimeException('Invalid frozen image.');
                    $ref=$store->put('originals/'.$entry['asset'].'/'.$entry['operation'].'/media/'.hash('sha256',$path),$body,$resource['type']);
                    foreach($entry['attributes']['media'] as &$media)if(array_key_exists($path,$media['files']))$media['files'][$path]=$ref;unset($media);
                }
                $original=$store->prepare($entry['asset'],$entry['operation'],$entry['source'],$entry['attributes']);
                $entry['record']=['schema'=>'owr-md-history-1','sequence'=>$store->latestState()['through']+1,'original'=>$original,'attributes'=>$entry['attributes'],'confirmed_at'=>gmdate('c')];
                $queue[$key]=$entry;if(!update_option(self::PENDING,$queue,false))throw new \RuntimeException('Cannot persist comment confirmation.');
            }
            $store->commit($entry['record']);unset($queue[$key]);
            if($queue)update_option(self::PENDING,$queue,false);else delete_option(self::PENDING);
        }
        delete_option('owr_m1_comment_error');
    }
    public static function replay(array &$data,string $source,array $attributes): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);$c=$v['comment']??[];
        if(($v['schema']??'')!=='owr-comment-1'||!is_bool($v['deleted']??null)||(int)($c['comment_ID']??0)!==(int)$attributes['origin_id']||(int)($c['comment_post_ID']??0)!==(int)$attributes['post_id'])throw new \RuntimeException('Invalid comment history.');
        if((int)$c['comment_ID']<=0||!in_array((string)($c['comment_approved']??''),['0','1','spam','trash','post-trashed'],true)||array_diff(array_keys($c),['comment_ID','comment_post_ID','comment_author','comment_author_email','comment_author_url','comment_author_IP','comment_date','comment_date_gmt','comment_content','comment_karma','comment_approved','comment_agent','comment_type','comment_parent','user_id']))throw new \RuntimeException('Invalid comment fields or state.');
        $id=(string)$c['comment_ID'];$parent=(string)$c['comment_post_ID'];$found=false;
        foreach($data['tables']['posts'] as $p)if((string)$p['ID']===$parent)$found=true;
        if(!$found)throw new \RuntimeException('Comment parent article is absent from recovery state.');
        $data['tables']['comments']=array_values(array_filter($data['tables']['comments'],fn($r)=>(string)$r['comment_ID']!==$id));
        if(!$v['deleted'])$data['tables']['comments'][]=$c;
        else {
            $data['tables']['commentmeta']=array_values(array_filter($data['tables']['commentmeta'],fn($r)=>(string)$r['comment_id']!==$id));
            foreach($data['tables']['comments'] as &$r)if((string)$r['comment_parent']===$id)$r['comment_parent']=$c['comment_parent'];unset($r);
        }
        foreach($data['tables']['posts'] as &$p)if((string)$p['ID']===$parent)$p['comment_count']=(string)count(array_filter($data['tables']['comments'],fn($r)=>(string)$r['comment_post_ID']===$parent&&(string)$r['comment_approved']==='1'));unset($p);
    }
}
