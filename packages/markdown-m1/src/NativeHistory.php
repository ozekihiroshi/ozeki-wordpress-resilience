<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/SaveFailure.php';

/** Completed native article deletion and final thumbnail/category/tag state. */
final class NativeHistory {
    private array $dirty=[];
    private array $deleting=[];
    private function eligible(int $id): bool {
        $p=get_post($id);return $p&&in_array($p->post_type,['post','page'],true)&&($p->post_status==='publish'||get_post_meta($id,'_owr_m1_asset',true))&&!empty((new Plugin())->config()['protect']);
    }
    private function mark(int $id): void {if($this->eligible($id)&&!isset($this->deleting[$id]))$this->dirty[$id]=true;}
    public function boot(): void {
        add_action('wp_after_insert_post',fn($id)=>$this->mark((int)$id),PHP_INT_MAX,1);
        foreach(['added_post_meta','updated_post_meta','deleted_post_meta'] as $hook)
            add_action($hook,function($meta,$id,$key){if($key==='_thumbnail_id')$this->mark((int)$id);},PHP_INT_MAX,3);
        add_action('set_object_terms',function($id,$terms,$tt,$taxonomy){if(in_array($taxonomy,['category','post_tag'],true))$this->mark((int)$id);},PHP_INT_MAX,4);
        add_action('deleted_term_relationships',function($id,$tt,$taxonomy){if(in_array($taxonomy,['category','post_tag'],true))$this->mark((int)$id);},PHP_INT_MAX,3);
        add_action('before_delete_post',function($id){if($this->eligible((int)$id))$this->deleting[(int)$id]=true;},PHP_INT_MIN,1);
        add_action('deleted_post',function($id,$p){
            if(!isset($this->deleting[(int)$id]))return;
            unset($this->deleting[(int)$id],$this->dirty[(int)$id]);
            $this->record((int)$id,$p->post_type,true,[],0,[],[],[],(int)$p->post_parent);
        },PHP_INT_MAX,2);
        add_action('shutdown',[$this,'flush'],PHP_INT_MAX);
    }
    public function flush(): void {
        SaveFailure::run('Article details capture',fn()=>$this->flushOperation());
    }
    private function flushOperation(): void {
        foreach(array_keys($this->dirty) as $id){
            if(!$this->eligible($id)){unset($this->dirty[$id]);continue;}
            global $wpdb;
            $terms=$wpdb->get_results($wpdb->prepare("SELECT t.*,tt.term_taxonomy_id,tt.taxonomy,tt.description,tt.parent FROM {$wpdb->terms} t JOIN {$wpdb->term_taxonomy} tt ON t.term_id=tt.term_id JOIN {$wpdb->term_relationships} tr ON tr.term_taxonomy_id=tt.term_taxonomy_id WHERE tr.object_id=%d AND tt.taxonomy IN ('category','post_tag') ORDER BY tt.term_taxonomy_id",$id),ARRAY_A);
            if($wpdb->last_error)throw new \RuntimeException('Cannot freeze native taxonomy.');
            // Include category ancestors so newly created nested categories remain valid.
            $all=$terms;$seen=array_fill_keys(array_column($terms,'term_id'),true);
            foreach($terms as $t){$parent=(int)$t['parent'];while($parent){if(isset($seen[$parent]))break;$seen[$parent]=true;$p=get_term($parent,$t['taxonomy']);if(!$p||is_wp_error($p))throw new \RuntimeException('Missing category parent');$all[]=['term_id'=>(string)$p->term_id,'name'=>$p->name,'slug'=>$p->slug,'term_group'=>(string)$p->term_group,'term_taxonomy_id'=>(string)$p->term_taxonomy_id,'taxonomy'=>$p->taxonomy,'description'=>$p->description,'parent'=>(string)$p->parent];$parent=(int)$p->parent;}}
            $thumb=(int)get_post_thumbnail_id($id);$resources=[];$media=[];
            if($thumb)$media=(new Plugin())->mediaForBody('wp-image-'.$thumb,(new Plugin())->store(),'',$resources);
            $this->record($id,get_post_type($id),false,$all,$thumb,$media,$resources,array_column($terms,'term_taxonomy_id'));
            unset($this->dirty[$id]);
        }
    }
    private function record(int $id,string $type,bool $deleted,array $terms,int $thumbnail,array $media,array $resources,array $assigned=[],int $parent=0): void {
        SaveFailure::run('Article details / deletion capture',fn()=>$this->recordOperation($id,$type,$deleted,$terms,$thumbnail,$media,$resources,$assigned,$parent));
    }
    private function recordOperation(int $id,string $type,bool $deleted,array $terms,int $thumbnail,array $media,array $resources,array $assigned=[],int $parent=0): void {
        $v=['schema'=>'owr-native-state-1','id'=>$id,'type'=>$type,'deleted'=>$deleted,'thumbnail'=>$thumbnail,'terms'=>$terms,'assigned'=>$assigned,'parent'=>$parent];
        (new CommentHistory())->enqueue('native-state-'.$id,Store::json($v),['post_type'=>'owr_native','content_format'=>'native-state-json','origin_id'=>$id,'title'=>'Article details #'.$id,'status'=>$deleted?'deleted':'saved','media'=>$media],$resources);
    }
    public static function replay(array &$d,array &$files,string $raw,array $a): void {
        $v=json_decode($raw,true,512,JSON_THROW_ON_ERROR);$id=(string)($v['id']??0);
        if(($v['schema']??'')!=='owr-native-state-1'||(int)$id<=0||(int)$id!==(int)$a['origin_id']||!in_array($v['type']??'',['post','page'],true)||!is_bool($v['deleted']??null)||!is_array($v['terms']??null)||!is_array($v['assigned']??null))throw new \RuntimeException('Invalid native article history.');
        $found=false;foreach($d['tables']['posts'] as $p)if((string)$p['ID']===$id){if($p['post_type']!==$v['type'])throw new \RuntimeException('Native article identity conflict.');$found=true;}
        if(!$found&&!$v['deleted'])throw new \RuntimeException('Native article baseline/history missing.');
        if($v['deleted']){
            // Core deletion also removes revisions; child articles/media move to the deleted parent's parent.
            $revisions=array_column(array_filter($d['tables']['posts'],fn($p)=>$p['post_type']==='revision'&&(string)$p['post_parent']===$id),'ID');
            $d['tables']['posts']=array_values(array_filter($d['tables']['posts'],fn($p)=>!in_array($p['ID'],$revisions)));
            $d['tables']['postmeta']=array_values(array_filter($d['tables']['postmeta'],fn($p)=>!in_array($p['post_id'],$revisions)));
            $comments=array_column(array_filter($d['tables']['comments'],fn($c)=>(string)$c['comment_post_ID']===$id),'comment_ID');
            foreach(['posts'=>'ID','postmeta'=>'post_id','term_relationships'=>'object_id','comments'=>'comment_post_ID'] as $table=>$key)$d['tables'][$table]=array_values(array_filter($d['tables'][$table],fn($x)=>(string)$x[$key]!==$id));
            $d['tables']['commentmeta']=array_values(array_filter($d['tables']['commentmeta'],fn($x)=>!in_array($x['comment_id'],$comments)));
            foreach($d['tables']['posts'] as &$p)if((string)$p['post_parent']===$id)$p['post_parent']=(string)(int)($v['parent']??0);unset($p);
            unset($files['posts/'.$id.'.html']);
        }else{
            $thumb=(int)($v['thumbnail']??-1);if($thumb<0)throw new \RuntimeException('Invalid thumbnail.');
            if($thumb){$ok=false;foreach($d['tables']['posts'] as $p)if((int)$p['ID']===$thumb&&$p['post_type']==='attachment'&&str_starts_with($p['post_mime_type'],'image/'))$ok=true;if(!$ok)throw new \RuntimeException('Missing thumbnail image.');}
            $d['tables']['postmeta']=array_values(array_filter($d['tables']['postmeta'],fn($x)=>!((string)$x['post_id']===$id&&$x['meta_key']==='_thumbnail_id')));
            if($thumb){$next=max(array_merge([0],array_map('intval',array_column($d['tables']['postmeta'],'meta_id'))))+1;$d['tables']['postmeta'][]=['meta_id'=>(string)$next,'post_id'=>$id,'meta_key'=>'_thumbnail_id','meta_value'=>(string)$thumb];}
            $ttids=[];foreach($d['tables']['term_taxonomy'] as $t)if(in_array($t['taxonomy'],['category','post_tag'],true))$ttids[]=(string)$t['term_taxonomy_id'];
            $d['tables']['term_relationships']=array_values(array_filter($d['tables']['term_relationships'],fn($x)=>!((string)$x['object_id']===$id&&in_array((string)$x['term_taxonomy_id'],$ttids,true))));
            $available=[];
            foreach($v['terms'] as $t){
                if(!in_array($t['taxonomy']??'',['category','post_tag'],true)||(int)($t['term_id']??0)<=0||(int)($t['term_taxonomy_id']??0)<=0)throw new \RuntimeException('Invalid native term.');
                foreach($d['tables']['term_taxonomy'] as $old)if((string)$old['term_taxonomy_id']===(string)$t['term_taxonomy_id']&&($old['taxonomy']!==$t['taxonomy']||(string)$old['term_id']!==(string)$t['term_id']))throw new \RuntimeException('Taxonomy identity conflict.');
                $d['tables']['terms']=array_values(array_filter($d['tables']['terms'],fn($x)=>(string)$x['term_id']!==(string)$t['term_id']));$d['tables']['terms'][]=array_intersect_key($t,array_flip(['term_id','name','slug','term_group']));
                $d['tables']['term_taxonomy']=array_values(array_filter($d['tables']['term_taxonomy'],fn($x)=>(string)$x['term_taxonomy_id']!==(string)$t['term_taxonomy_id']));$d['tables']['term_taxonomy'][]=array_intersect_key($t,array_flip(['term_taxonomy_id','term_id','taxonomy','description','parent']))+['count'=>'0'];$available[]=(string)$t['term_taxonomy_id'];
            }
            foreach(array_unique($v['assigned']) as $tt){if(!in_array((string)$tt,$available,true))throw new \RuntimeException('Missing assigned term.');$d['tables']['term_relationships'][]=['object_id'=>$id,'term_taxonomy_id'=>(string)$tt,'term_order'=>'0'];}
        }
        foreach($d['tables']['term_taxonomy'] as &$t)if(in_array($t['taxonomy'],['category','post_tag'],true)){$published=[];foreach($d['tables']['posts'] as $p)if($p['post_status']==='publish'&&in_array($p['post_type'],['post','page'],true))$published[]=(string)$p['ID'];$t['count']=(string)count(array_filter($d['tables']['term_relationships'],fn($x)=>(string)$x['term_taxonomy_id']===(string)$t['term_taxonomy_id']&&in_array((string)$x['object_id'],$published,true)));}unset($t);
    }
}