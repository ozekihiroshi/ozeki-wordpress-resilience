<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Preserve prepared presentation records, never activate archived templates. */
final class RecoveryTemplates {
    public const TYPES=['wp_template','wp_template_part','wp_navigation'];
    public static function plan(array $after,array $before,string $theme): array {
        $report=[];$keep=[];$map=[];$next=1;$terms=[];$tax=[];
        foreach(array_merge($after['posts'],$before['posts']) as $p)$next=max($next,(int)$p['ID']+1);
        foreach($before['terms'] as $t)$terms[(int)$t['term_id']]=$t;
        foreach($before['term_taxonomy'] as $t)$tax[(int)$t['term_taxonomy_id']]=$t;
        $meta=[];foreach($before['postmeta'] as $m)$meta[(int)$m['post_id']][$m['meta_key']]=$m['meta_value'];
        foreach($before['posts'] as $p){
            $id=(int)$p['ID'];if(!in_array($p['post_type'],self::TYPES,true)||$p['post_status']!=='publish')continue;
            if(!empty($meta[$id]['_ozeki_resilience_m1_origin_url'])||!empty($meta[$id]['_owr_m1_origin_url'])){
                $report[]=['item'=>'posts.'.$id,'reason'=>'Previously recovered template is not prepared software configuration','origin'=>'destination'];continue;
            }
            $matches=$p['post_type']==='wp_navigation';
            foreach($before['term_relationships'] as $r)if((int)$r['object_id']===$id){
                $tt=$tax[(int)$r['term_taxonomy_id']]??[];
                if(($tt['taxonomy']??'')==='wp_theme'&&($terms[(int)$tt['term_id']]['slug']??'')===$theme)$matches=true;
            }
            if($matches){$keep[$id]=$p;$map[$id]=$next++;}
        }
        $newTerms=[];$newTax=[];$nextTerm=1;$nextTax=1;
        foreach(array_merge($after['terms'],$before['terms']) as $t)$nextTerm=max($nextTerm,(int)$t['term_id']+1);
        foreach(array_merge($after['term_taxonomy'],$before['term_taxonomy']) as $t)$nextTax=max($nextTax,(int)$t['term_taxonomy_id']+1);
        foreach($keep as $id=>$p){
            $p['ID']=$map[$id];$p['post_parent']=$map[(int)$p['post_parent']]??0;
            $p['post_content']=serialize_blocks(self::references(parse_blocks($p['post_content']),$map,$keep,$after,$before,$report,$id));
            $after['posts'][]=$p;
            foreach($before['postmeta'] as $m)if((int)$m['post_id']===$id&&!in_array($m['meta_key'],['_edit_lock','_edit_last'],true)){
                unset($m['meta_id']);$m['post_id']=$map[$id];$after['postmeta'][]=$m;
            }
            foreach($before['term_relationships'] as $r)if((int)$r['object_id']===$id){
                $old=(int)$r['term_taxonomy_id'];$tt=$tax[$old]??null;
                if(!$tt||!in_array($tt['taxonomy'],['wp_theme','wp_template_part_area'],true))continue;
                if(!isset($newTax[$old])){
                    $termId=(int)$tt['term_id'];$t=$terms[$termId];
                    // Core resolves template taxonomy terms by slug. Duplicate terms
                    // would make the preserved DB template invisible behind theme files.
                    foreach($after['term_taxonomy'] as $existing)if($existing['taxonomy']===$tt['taxonomy']){
                        foreach($after['terms'] as $et)if((int)$et['term_id']===(int)$existing['term_id']&&$et['slug']===$t['slug']){
                            $newTerms[$termId]=(int)$et['term_id'];$newTax[$old]=(int)$existing['term_taxonomy_id'];break 2;
                        }
                    }
                    if(!isset($newTerms[$termId])){
                        $newTerms[$termId]=$nextTerm++;$t['term_id']=$newTerms[$termId];$after['terms'][]=$t;
                        foreach($before['termmeta'] as $m)if((int)$m['term_id']===$termId){unset($m['meta_id']);$m['term_id']=$newTerms[$termId];$after['termmeta'][]=$m;}
                    }
                    if(!isset($newTax[$old])){$newTax[$old]=$nextTax++;$tt['term_id']=$newTerms[$termId];$tt['term_taxonomy_id']=$newTax[$old];$tt['parent']=0;$tt['count']=0;$after['term_taxonomy'][]=$tt;}
                }
                $r['object_id']=$map[$id];$r['term_taxonomy_id']=$newTax[$old];$after['term_relationships'][]=$r;
            }
            $report[]=['item'=>'posts.'.$map[$id],'reason'=>'Prepared template/navigation retained with destination identity','origin'=>'destination'];
        }
        foreach($after['term_taxonomy'] as &$tt)if(in_array((int)$tt['term_taxonomy_id'],$newTax,true)){
            $tt['count']=count(array_filter($after['term_relationships'],fn($r)=>(int)$r['term_taxonomy_id']===(int)$tt['term_taxonomy_id']));
        }unset($tt);
        // A missing source-selected page template must not hide recovered content.
        $available=['','default'];
        foreach(get_block_templates([],'wp_template') as $t)if($t->source==='theme')$available[]=$t->slug;
        foreach(wp_get_theme()->get_page_templates() as $file=>$label)$available[]=$file;
        foreach($keep as $p)if($p['post_type']==='wp_template')$available[]=$p['post_name'];
        foreach($after['postmeta'] as &$m)if($m['meta_key']==='_wp_page_template'&&!in_array($m['meta_value'],$available,true)&&!in_array((int)$m['post_id'],$map,true)){
            $report[]=['item'=>'postmeta.'.$m['post_id'].'._wp_page_template','reason'=>'Archived page template is unavailable; prepared default template used','origin'=>'source'];$m['meta_value']='default';
        }unset($m);
        return ['tables'=>$after,'ids'=>array_values($map),'report'=>$report];
    }
    private static function references(array $blocks,array $map,array $kept,array $after,array $before,array &$report,int $owner): array {
        foreach($blocks as &$b){
            $attrs=&$b['attrs'];$reason=null;
            if(isset($attrs['ref'])){
                $id=(int)$attrs['ref'];
                if($b['blockName']==='core/navigation'&&isset($map[$id])&&$kept[$id]['post_type']==='wp_navigation')$attrs['ref']=$map[$id];
                else $reason='Prepared block reference cannot be mapped to the same content';
            }
            foreach(['id','mediaId'] as $key)if(!empty($attrs[$key])){
                $id=(int)$attrs[$key];$old=null;$new=null;
                foreach($before['posts'] as $p)if((int)$p['ID']===$id)$old=$p;
                foreach($after['posts'] as $p)if((int)$p['ID']===$id)$new=$p;
                if(!$old||!$new||$old['post_type']!==$new['post_type']||empty($old['guid'])||$old['guid']!==$new['guid'])$reason='Prepared content reference changed identity; select the target again';
            }
            if($reason){$report[]=['item'=>'posts.'.$owner.'.block','reason'=>$reason,'origin'=>'destination'];$b=['blockName'=>null,'attrs'=>[],'innerBlocks'=>[],'innerHTML'=>'','innerContent'=>['']];continue;}
            $b['innerBlocks']=self::references($b['innerBlocks'],$map,$kept,$after,$before,$report,$owner);
        }unset($b);return $blocks;
    }
}
