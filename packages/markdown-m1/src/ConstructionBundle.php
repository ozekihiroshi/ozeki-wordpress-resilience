<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Material projection only. No fixture recipe, source lookups or destination IDs. */
final class ConstructionBundle {
    private static function staticBlocks(array $blocks): bool {
        foreach($blocks as $b){
            if($b['attrs']||!in_array($b['blockName'],[null,'core/paragraph','core/heading','core/shortcode','core/quote'],true))return false;
            if(!self::staticBlocks($b['innerBlocks']))return false;
        }
        return true;
    }
    public static function plan(array $kit): array {
        $m=$kit['manifest'];$f=$kit['files'];$d=json_decode($f['content.json'],true,512,JSON_THROW_ON_ERROR);
        $meta=[];foreach($d['tables']['postmeta'] as $r){$v=$r['meta_value'];$meta[(string)$r['post_id']][$r['meta_key']]=is_serialized($v)?unserialize($v,['allowed_classes'=>false]):$v;}
        $out=['source'=>$m['source_url'],'uploads'=>$m['source_upload_url'],'anchor'=>$kit['anchor'],'posts'=>[],'meta'=>$meta,'options'=>$d['options'],'terms'=>$d['tables']['terms'],'taxonomies'=>$d['tables']['term_taxonomy'],'relationships'=>$d['tables']['term_relationships'],'files'=>[],'tail'=>$kit['tail'],'held'=>[]];
        foreach($d['tables']['posts'] as $p)if(in_array($p['post_status'],['publish','private','inherit'],true)&&in_array($p['post_type'],['post','page','attachment','nav_menu_item','ozmd_document'],true)){
            if(in_array($p['post_type'],['post','page'],true)){
                $norm=static fn($s)=>preg_replace('~\s*/>~',' />',serialize_blocks(parse_blocks($s)));
                if($norm(wp_kses_post($p['post_content']))!==$norm($p['post_content']))$out['held']['post:'.$p['ID']]='HTML needs a safe application decision';
            }
            $out['posts'][]=$p;
        }
        foreach($f as $path=>$bytes)if(str_starts_with($path,'uploads/')||str_starts_with($path,'markdown/'))$out['files'][$path]=base64_encode($bytes);
        $out['media_access']=$d['media_access']??[];
        $out['initial_references']=ConstructionInitialReferences::read($f);
        foreach($out['posts'] as $p)if(in_array($p['post_type'],['post','page','ozmd_document'],true)){
            $material=$out['initial_references']['contents'][(string)$p['ID']]??null;
            if(!$material||($material['contract']['coverage']??'')!=='complete')$out['held']['content-reference:'.$p['ID']]=['reason'=>'Initial content contract missing/incomplete','details'=>$material['contract']['reasons']??[]];
        }
        foreach($out['posts'] as $p)if($p['post_type']==='attachment'&&empty($out['initial_references']['media'][(string)$p['ID']]['image-url:full']))$out['held']['image-reference:'.$p['ID']]='Missing source baseline reference material; do not infer it at reconstruction';
        $out['tables']=array_key_exists('tablepress_tables',$d['options'])?TableReconstruction::plan($m,$f):['tables'=>[],'held'=>[]];
        $out['forms']=ContactFormReconstruction::plan($m,$f);
        $out['members']=isset($d['membership'])?MemberReconstruction::plan($m,$f):null;
        $out['acf']=isset($d['acf'])?AcfReconstruction::plan($m,$f):null;
        // Captured normal receipt inputs can accompany a baseline that predates
        // ReceiptInputs preservation. Never recreate input from stored output.
        $out['receipts']=[];
        foreach($kit['journal']['entries'] as $e)if($e['state']==='registered'&&$e['operation']==='flamingo-add'&&$e['sequence']<=$kit['anchor']['through'])$out['receipts'][]=$e;
        foreach($d['tables']['posts'] as $p)if($p['post_type']==='flamingo_inbound'&&!array_filter($out['receipts'],fn($e)=>(int)$e['result']['id']===(int)$p['ID']))$out['held']['receipt:'.$p['ID']]='No captured normal registration input';
        foreach($kit['tail'] as $e)if($e['state']==='registered'){
            foreach(['title','content','excerpt'] as $field)if(isset($e['input']['body'][$field])){
                $text=$e['input']['body'][$field];
                $norm=static fn($s)=>preg_replace('~\s*/>~',' />',serialize_blocks(parse_blocks($s)));
                if(!is_string($text)||$norm(wp_kses_post($text))!==$norm($text)||($e['contract']['coverage']??'')!=='complete')$out['held']['operation:'.$e['sequence']]='Recorded content needs a safe application decision';
            }
        }
        return $out;
    }
}
