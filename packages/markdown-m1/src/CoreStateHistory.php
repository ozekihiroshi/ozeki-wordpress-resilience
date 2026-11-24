<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Completed core changes that do not necessarily save an article body. */
final class CoreStateHistory {
    public const PENDING='ozeki_resilience_core_state_pending';
    private static function enabled(): bool {
        $c=(new Plugin())->config();return !empty($c['protect'])&&($c['setup_role']??'source')==='source';
    }
    public function boot(): void {
        foreach(['created_term','edited_term','delete_term'] as $hook)add_action($hook,function($id,$tt,$tax){if(in_array($tax,['category','post_tag'],true))self::mark('taxonomy');},PHP_INT_MAX,3);
        add_action('set_object_terms',function($id,$terms,$tt,$tax){if(in_array($tax,['category','post_tag'],true))self::mark('taxonomy');},PHP_INT_MAX,4);
        add_action('deleted_term_relationships',function($id,$tt,$tax){if(in_array($tax,['category','post_tag'],true))self::mark('taxonomy');},PHP_INT_MAX,3);
        foreach(['added_option','updated_option','deleted_option'] as $hook)add_action($hook,function($key){if(in_array($key,UpdateContract::OPTIONS,true))self::mark('options');},PHP_INT_MAX,1);
        foreach(['trashed_post_comments','untrashed_post_comments'] as $hook)add_action($hook,fn($id)=>self::mark('comments:'.(int)$id),PHP_INT_MAX,1);
        add_action('shutdown',static function(){SaveFailure::run('Core settings capture',fn()=>self::flush());},PHP_INT_MAX);
        add_action('admin_notices',static function(){
            if(get_option(self::PENDING)&&current_user_can('manage_options'))echo '<div class="notice notice-warning"><p>'.esc_html(SetupReadiness::text('Core content changes are awaiting preservation. Use Resume history in Tools → Resilience.','記事・分類・基本設定の変更の保全が未完了です。ツール → Resilienceで「履歴を再開」を実行してください。')).'</p></div>';
        });
    }
    private static function lock(): string {
        global $wpdb;$name='ozeki-resilience-'.$wpdb->prefix;
        if((int)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 30)',$name))!==1)throw new \RuntimeException('Core changes are busy; retry preservation.');
        wp_cache_delete(self::PENDING,'options');return $name;
    }
    private static function unlock(string $name): void {global $wpdb;$wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$name));}
    private static function mark(string $kind): void {
        if(!self::enabled())return;
        SaveFailure::run('Core change registration',static function()use($kind){
            $lock=self::lock();try{
                $pending=(array)get_option(self::PENDING,[]);$pending[$kind]=true;
                update_option(self::PENDING,$pending,false);
                if(get_option(self::PENDING)!==$pending)throw new \RuntimeException('Cannot persist core capture pending state.');
            }finally{self::unlock($lock);}
        });
    }
    public static function flush(): void {
        if(!self::enabled()||!get_option(self::PENDING))return;
        $lock=self::lock();try{
            foreach(array_keys((array)get_option(self::PENDING,[])) as $kind){
                (new CommentHistory())->enqueueCurrent('core-'.$kind,fn()=>Store::json(self::capture($kind)),['post_type'=>'owr_core','content_format'=>'core-state-json','update_contract'=>UpdateContract::SCHEMA,'origin_id'=>0,'title'=>'Core '.$kind,'status'=>'saved']);
                // enqueueCurrent durably freezes the payload before returning, even if S3 is unavailable.
                $pending=(array)get_option(self::PENDING,[]);unset($pending[$kind]);
                if($pending)update_option(self::PENDING,$pending,false);else delete_option(self::PENDING);
            }
        }finally{self::unlock($lock);}
    }
    private static function rows(string $sql): array {
        global $wpdb;$rows=$wpdb->get_results($sql,ARRAY_A);
        if($wpdb->last_error)throw new \RuntimeException('Cannot capture core information.');
        return $rows;
    }
    private static function capture(string $kind): array {
        global $wpdb;$v=['schema'=>UpdateContract::SCHEMA,'kind'=>$kind];
        if($kind==='options'){
            $v['options']=UpdateContract::options();
        }elseif($kind==='taxonomy'){
            // One read view: definitions and assignments must not come from separate queries.
            $rows=self::rows("SELECT t.term_id,t.name,t.slug,t.term_group,tt.term_taxonomy_id,tt.taxonomy,tt.description,tt.parent,tt.count,tr.object_id,tr.term_order FROM {$wpdb->terms} t JOIN {$wpdb->term_taxonomy} tt ON t.term_id=tt.term_id LEFT JOIN {$wpdb->term_relationships} tr ON tr.term_taxonomy_id=tt.term_taxonomy_id WHERE tt.taxonomy IN ('category','post_tag') ORDER BY t.term_id,tt.term_taxonomy_id,tr.object_id");
            $terms=[];$taxonomies=[];$links=[];
            foreach($rows as $row){
                $terms[$row['term_id']]=array_intersect_key($row,array_flip(['term_id','name','slug','term_group']));
                $taxonomies[$row['term_taxonomy_id']]=array_intersect_key($row,array_flip(['term_taxonomy_id','term_id','taxonomy','description','parent','count']));
                if($row['object_id']!==null)$links[]=array_intersect_key($row,array_flip(['object_id','term_taxonomy_id','term_order']));
            }
            $v['terms']=array_values($terms);$v['term_taxonomy']=array_values($taxonomies);$v['term_relationships']=$links;
        }elseif(preg_match('/^comments:([1-9][0-9]*)$/D',$kind,$m)){
            $id=(int)$m[1];$post=get_post($id);
            $v['post_id']=$id;$v['comments']=[];$v['postmeta']=[];
            if($post&&in_array($post->post_type,['post','page','ozmd_document'],true)&&get_post_meta($id,'_ozeki_resilience_m1_asset',true)){
                $v['comments']=self::rows($wpdb->prepare("SELECT * FROM {$wpdb->comments} WHERE comment_post_ID=%d ORDER BY comment_ID",$id));
                $v['postmeta']=self::rows($wpdb->prepare("SELECT * FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key IN ('_wp_trash_meta_status','_wp_trash_meta_time','_wp_trash_meta_comments_status','_wp_desired_post_slug') ORDER BY meta_id",$id));
            }
        }else throw new \RuntimeException('Unknown core update.');
        return $v;
    }
    public static function replay(array &$d,string $raw): void {
        $v=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
        if(($v['schema']??'')!==UpdateContract::SCHEMA)throw new \RuntimeException('Unknown core update contract.');
        if(($v['kind']??'')==='options'){
            if(!is_array($v['options']??null)||array_keys($v['options'])!==UpdateContract::OPTIONS)throw new \RuntimeException('Incomplete core settings.');
            foreach($v['options'] as $key=>$value){if(!is_scalar($value))throw new \RuntimeException('Invalid core setting.');$d['options'][$key]=$value;}
        }elseif(($v['kind']??'')==='taxonomy'){
            foreach(['terms','term_taxonomy','term_relationships'] as $table)if(!is_array($v[$table]??null))throw new \RuntimeException('Incomplete core taxonomy.');
            $ids=[];$ttids=[];
            foreach($v['terms'] as $term){if((int)($term['term_id']??0)<=0||array_diff(array_keys($term),['term_id','name','slug','term_group']))throw new \RuntimeException('Invalid term definition.');$ids[(string)$term['term_id']]=true;}
            foreach($v['term_taxonomy'] as $t){if(!in_array($t['taxonomy']??'',['category','post_tag'],true)||!isset($ids[(string)($t['term_id']??0)])||(int)($t['term_taxonomy_id']??0)<=0||((int)$t['parent']&&!isset($ids[(string)$t['parent']])))throw new \RuntimeException('Invalid term relationship.');$ttids[(string)$t['term_taxonomy_id']]=true;}
            $oldIds=[];$oldTt=[];
            foreach($d['tables']['term_taxonomy'] as $t)if(in_array($t['taxonomy'],['category','post_tag'],true)){$oldIds[(string)$t['term_id']]=true;$oldTt[(string)$t['term_taxonomy_id']]=true;}
            $other=array_values(array_filter($d['tables']['term_taxonomy'],fn($t)=>!isset($oldTt[(string)$t['term_taxonomy_id']])));
            $otherIds=[];foreach($other as $t){
                if(isset($ttids[(string)$t['term_taxonomy_id']]))throw new \RuntimeException('Core taxonomy identity conflicts with another taxonomy.');
                $otherIds[(string)$t['term_id']]=true;
            }
            $d['tables']['term_taxonomy']=array_merge($other,$v['term_taxonomy']);
            $d['tables']['terms']=array_merge(array_values(array_filter($d['tables']['terms'],fn($t)=>(!isset($oldIds[(string)$t['term_id']])||isset($otherIds[(string)$t['term_id']]))&&!isset($ids[(string)$t['term_id']]))),$v['terms']);
            $d['tables']['termmeta']=array_values(array_filter($d['tables']['termmeta'],fn($t)=>!isset($oldIds[(string)$t['term_id']])||isset($ids[(string)$t['term_id']])||isset($otherIds[(string)$t['term_id']])));
            $posts=array_fill_keys(array_map('strval',array_column($d['tables']['posts'],'ID')),true);
            $links=[];foreach($v['term_relationships'] as $link){if(!isset($ttids[(string)($link['term_taxonomy_id']??0)]))throw new \RuntimeException('Missing taxonomy definition.');if(isset($posts[(string)$link['object_id']]))$links[]=$link;}
            $d['tables']['term_relationships']=array_merge(array_values(array_filter($d['tables']['term_relationships'],fn($t)=>!isset($oldTt[(string)$t['term_taxonomy_id']])&&!isset($ttids[(string)$t['term_taxonomy_id']]))),$links);
        }elseif(preg_match('/^comments:([1-9][0-9]*)$/D',(string)($v['kind']??''),$m)){
            $id=(string)$m[1];
            if((string)($v['post_id']??'')!==$id||!is_array($v['comments']??null)||!is_array($v['postmeta']??null))throw new \RuntimeException('Invalid post comment transition.');
            foreach($v['comments'] as $c){
                if((string)($c['comment_post_ID']??'')!==$id)throw new \RuntimeException('Comment transition parent mismatch.');
                CommentHistory::replay($d,Store::json(['schema'=>'owr-comment-1','deleted'=>false,'comment'=>$c]),['origin_id'=>(int)$c['comment_ID'],'post_id'=>(int)$id]);
            }
            $keys=['_wp_trash_meta_status','_wp_trash_meta_time','_wp_trash_meta_comments_status','_wp_desired_post_slug'];
            $d['tables']['postmeta']=array_values(array_filter($d['tables']['postmeta'],fn($r)=>!((string)$r['post_id']===$id&&in_array($r['meta_key'],$keys,true))));
            $next=max(array_merge([0],array_map('intval',array_column($d['tables']['postmeta'],'meta_id'))))+1;
            foreach($v['postmeta'] as $r){if((string)($r['post_id']??'')!==$id||!in_array($r['meta_key']??'',$keys,true))throw new \RuntimeException('Invalid comment transition metadata.');$r['meta_id']=(string)$next++;$d['tables']['postmeta'][]=$r;}
        }else throw new \RuntimeException('Unsupported core history.');
    }
}
