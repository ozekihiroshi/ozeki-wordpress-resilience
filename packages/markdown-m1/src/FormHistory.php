<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/SaveFailure.php';

/** CF7 definition and Flamingo receipt snapshots at their completed-save boundaries. */
final class FormHistory
{
    /** Recovery keys, not a filter on preserved S3 originals. */
    public static function recoveryMeta(string $type): array {
        if($type==='wpcf7_contact_form')return ['_form'=>'text','_mail'=>['active'=>'bool','subject'=>'text','sender'=>'text','recipient'=>'text','body'=>'text','additional_headers'=>'text','attachments'=>'text','use_html'=>'bool','exclude_blank'=>'bool'], '_mail_2'=>['active'=>'bool','subject'=>'text','sender'=>'text','recipient'=>'text','body'=>'text','additional_headers'=>'text','attachments'=>'text','use_html'=>'bool','exclude_blank'=>'bool'],'_messages'=>'text-map','_additional_settings'=>'cf7-lines','_locale'=>'text','_hash'=>'text'];
        return ['_fields'=>'plain','_subject'=>'text','_from'=>'text','_from_name'=>'text','_from_email'=>'text','_submission_status'=>'text','_spam_meta_time'=>'number','_hash'=>'text','_consent'=>'plain'];
    }

    public const DEPENDENCIES=['contact-form-7/wp-contact-form-7.php','flamingo/flamingo.php'];
    private array $dirty=[];
    public function boot(): void {
        // Flamingo writes metadata after wp_insert_post; freeze only the completed
        // request state, not the intermediate core save. One final state per ID.
        add_action('wp_after_insert_post',fn($id,$post)=>$this->mark((int)$id),PHP_INT_MAX,2);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)
            add_action($hook,fn($meta,$id)=>$this->mark((int)$id),PHP_INT_MAX,2);
        add_action('deleted_post',function($id,$post){
            unset($this->dirty[(int)$id]);
            if(!in_array($post->post_type,['wpcf7_contact_form','flamingo_inbound'],true)||empty((new Plugin())->config()['protect']))return;
            $item=['post'=>(array)$post,'meta'=>[],'channels'=>[],'deleted'=>true];
            $this->enqueue([$item]);
        },PHP_INT_MIN,2);
        add_action('shutdown',[$this,'flush'],PHP_INT_MAX);

        add_action('wpcf7_after_save',fn($form)=>$this->capture([$form->id()]),PHP_INT_MIN,1);
        add_action('wpcf7_after_flamingo',function($result){
            $id=(int)($result['flamingo_inbound_id']??0);if(!$id)return;
            $form=\WPCF7_ContactForm::get_current();
            if(!$form)SaveFailure::run('Receipt identity',static function(){throw new \RuntimeException('Missing received form identity.');});
            $this->capture([$form->id(),$id]);
        },PHP_INT_MIN,1);
    }
    private function mark(int $id): void {
        if(get_post_type($id)==='flamingo_inbound'&&!empty((new Plugin())->config()['protect']))$this->dirty[$id]=true;
    }
    public function flush(): void {
        foreach(array_keys($this->dirty) as $id){
            if(get_post_type($id)==='flamingo_inbound')$this->capture([$id]);
            else unset($this->dirty[$id]);
        }
    }
    public static function checkDependency(string $plugin,string $version): void {
        if(!in_array($plugin,self::DEPENDENCIES,true))throw new \RuntimeException('Unsupported form dependency.');
        $path=WP_PLUGIN_DIR.'/'.$plugin;
        $data=is_file($path)?get_file_data($path,['Version'=>'Version']):[];
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal exception text is stored as data; admin renderers escape it and REST responses encode it.
        if(($data['Version']??'')!==$version)throw new \RuntimeException('Install recorded form dependency before recovery: '.$plugin.' '.$version);
    }
    public function capture(array $ids): void {
        SaveFailure::run('Form / receipt capture',fn()=>$this->captureOperation($ids));
    }
    private function captureOperation(array $ids): void {
        if(empty((new Plugin())->config()['protect']))return;
        global $wpdb;$items=[];
        foreach($ids as $id){
            $post=$wpdb->get_row($wpdb->prepare('SELECT * FROM '.$wpdb->posts.' WHERE ID=%d',$id),ARRAY_A);
            if(!$post||!in_array($post['post_type'],['wpcf7_contact_form','flamingo_inbound'],true))throw new \RuntimeException('Invalid completed form asset.');
            $meta=$wpdb->get_results($wpdb->prepare('SELECT meta_key,meta_value FROM '.$wpdb->postmeta.' WHERE post_id=%d ORDER BY meta_id',$id),ARRAY_A);
            $meta=array_values(array_filter($meta,fn($r)=>!in_array($r['meta_key'],['_edit_lock','_edit_last'],true)));
            $terms=$wpdb->get_results($wpdb->prepare('SELECT t.*,tt.term_taxonomy_id,tt.taxonomy,tt.description,tt.parent FROM '.$wpdb->terms.' t JOIN '.$wpdb->term_taxonomy.' tt ON t.term_id=tt.term_id JOIN '.$wpdb->term_relationships.' tr ON tr.term_taxonomy_id=tt.term_taxonomy_id WHERE tr.object_id=%d AND tt.taxonomy=%s',$id,'flamingo_inbound_channel'),ARRAY_A);
            if($wpdb->last_error)throw new \RuntimeException('Cannot capture completed form.');
            $items[]=['post'=>$post,'meta'=>$meta,'channels'=>$terms];
        }
        $this->enqueue($items);
        foreach($ids as $id)unset($this->dirty[(int)$id]);
    }
    private function enqueue(array $items): void {
        SaveFailure::run('Form queue preparation',fn()=>$this->enqueueOperation($items));
    }
    private function enqueueOperation(array $items): void {
        $dependencies=[];
        foreach(self::DEPENDENCIES as $plugin){
            $path=WP_PLUGIN_DIR.'/'.$plugin;
            if(!is_file($path))throw new \RuntimeException('Install Contact Form 7 and Flamingo for form protection.');
            $dependencies[$plugin]=get_file_data($path,['Version'=>'Version'])['Version'];
        }
        $last=end($items);$id=(int)$last['post']['ID'];
        $attrs=['post_type'=>'owr_form','content_format'=>'form-json','origin_id'=>$id,'title'=>$last['post']['post_title'],'status'=>!empty($last['deleted'])?'deleted':$last['post']['post_status'],'dependencies'=>$dependencies];
        (new CommentHistory())->enqueue('form-'.$id,Store::json(['schema'=>'owr-form-1','items'=>$items]),$attrs);
    }
    public static function replay(array &$data,string $source,array $attributes): void {
        $v=json_decode($source,true,512,JSON_THROW_ON_ERROR);
        if(($v['schema']??'')!=='owr-form-1'||!is_array($v['items']??null)||!count($v['items'])||count($v['items'])>2)throw new \RuntimeException('Invalid form original.');
        $last=end($v['items']);if((int)($last['post']['ID']??0)!==(int)$attributes['origin_id'])throw new \RuntimeException('Form identity mismatch.');
        foreach($v['items'] as $item){
            $post=$item['post'];$id=(string)$post['ID'];
            if((int)$id<=0||!in_array($post['post_type'],['wpcf7_contact_form','flamingo_inbound'],true)||!is_array($item['meta'])||!is_array($item['channels']))throw new \RuntimeException('Invalid form record.');
            foreach($data['tables']['posts'] as $p)if((string)$p['ID']===$id&&$p['post_type']!==$post['post_type'])throw new \RuntimeException('Form identity conflicts with baseline.');
            if(isset($item['deleted'])&&!is_bool($item['deleted']))throw new \RuntimeException('Invalid deletion marker.');
            if(!empty($item['deleted'])){
                $data['tables']['posts']=array_values(array_filter($data['tables']['posts'],fn($p)=>(string)$p['ID']!==$id));
                $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($m)=>(string)$m['post_id']!==$id));
                $data['tables']['term_relationships']=array_values(array_filter($data['tables']['term_relationships'],fn($r)=>(string)$r['object_id']!==$id));
                continue;
            }
            $data['tables']['posts']=array_values(array_filter($data['tables']['posts'],fn($p)=>(string)$p['ID']!==$id));$data['tables']['posts'][]=$post;
            $data['tables']['postmeta']=array_values(array_filter($data['tables']['postmeta'],fn($m)=>(string)$m['post_id']!==$id));
            $next=max(array_merge([0],array_map('intval',array_column($data['tables']['postmeta'],'meta_id'))))+1;
            foreach($item['meta'] as $meta)$data['tables']['postmeta'][]=['meta_id'=>(string)$next++,'post_id'=>$id,'meta_key'=>$meta['meta_key'],'meta_value'=>$meta['meta_value']];
            $channelIds=[];
            foreach($data['tables']['term_taxonomy'] as $tt)if($tt['taxonomy']==='flamingo_inbound_channel')$channelIds[]=(string)$tt['term_taxonomy_id'];
            $data['tables']['term_relationships']=array_values(array_filter($data['tables']['term_relationships'],fn($r)=>!((string)$r['object_id']===$id&&in_array((string)$r['term_taxonomy_id'],$channelIds,true))));
            foreach($item['channels'] as $t){
                if($t['taxonomy']!=='flamingo_inbound_channel')throw new \RuntimeException('Invalid form channel.');
                foreach($data['tables']['terms'] as $old)if((string)$old['term_id']===(string)$t['term_id']&&$old['slug']!==$t['slug'])throw new \RuntimeException('Channel identity conflict.');
                foreach($data['tables']['term_taxonomy'] as $old)if((string)$old['term_taxonomy_id']===(string)$t['term_taxonomy_id']&&($old['taxonomy']!==$t['taxonomy']||(string)$old['term_id']!==(string)$t['term_id']))throw new \RuntimeException('Channel taxonomy conflict.');
                $data['tables']['terms']=array_values(array_filter($data['tables']['terms'],fn($r)=>(string)$r['term_id']!==(string)$t['term_id']));
                $data['tables']['terms'][]=array_intersect_key($t,array_flip(['term_id','name','slug','term_group']));
                $data['tables']['term_taxonomy']=array_values(array_filter($data['tables']['term_taxonomy'],fn($r)=>(string)$r['term_taxonomy_id']!==(string)$t['term_taxonomy_id']));
                $data['tables']['term_taxonomy'][]=array_intersect_key($t,array_flip(['term_taxonomy_id','term_id','taxonomy','description','parent']))+['count'=>'0'];
                $data['tables']['term_relationships'][]=['object_id'=>$id,'term_taxonomy_id'=>$t['term_taxonomy_id'],'term_order'=>'0'];
            }
        }
        foreach($data['tables']['term_taxonomy'] as &$t)if($t['taxonomy']==='flamingo_inbound_channel')$t['count']=(string)count(array_filter($data['tables']['term_relationships'],fn($r)=>(string)$r['term_taxonomy_id']===(string)$t['term_taxonomy_id']));unset($t);
    }
}
