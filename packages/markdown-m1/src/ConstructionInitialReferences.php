<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Observe baseline media references on the source, not from destination filenames. */
final class ConstructionInitialReferences {
    public const PATH='construction/initial-references.json';
    public static function capture(array $files): array {
        $d=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);$media=[];
        foreach($d['tables']['posts'] as $p){
            if($p['post_type']!=='attachment'||$p['post_status']!=='inherit')continue;
            $id=(int)$p['ID'];$url=wp_get_attachment_url($id);
            if(!$url)throw new \RuntimeException('Initial attachment URL unavailable');
            $values=['image-url:full'=>$url];$metadata=wp_get_attachment_metadata($id);
            foreach($metadata['sizes']??[] as $size=>$unused){
                $r=wp_get_attachment_image_src($id,$size);
                if(!$r)throw new \RuntimeException('Initial image size URL unavailable');
                $values['image-url:'.$size]=$r[0];
            }
            $media[(string)$id]=$values;
        }
        $contents=[];
        foreach($d['tables']['posts'] as $p){
            if(!in_array($p['post_status'],['publish','private'],true)||!in_array($p['post_type'],['post','page','ozmd_document'],true))continue;
            $id=(string)$p['ID'];$markdown=$p['post_type']==='ozmd_document';
            if($markdown&&!isset($files['markdown/'.$id.'.md']))throw new \RuntimeException('Initial Markdown original missing');
            $input=$markdown?['source_text'=>$files['markdown/'.$id.'.md']]:['content'=>$p['post_content'],'excerpt'=>$p['post_excerpt']];
            $c=['schema'=>ConstructionContract::SCHEMA,'coverage'=>'complete','reasons'=>[],'endpoint'=>'initial-content','target'=>null,'arguments'=>$input,'references'=>[],'spans'=>[],'output_type'=>null];
            foreach($input as $field=>$text)ConstructionEmbeds::capture($text,[$field],$c,$markdown?'markdown':'html');
            if($c['reasons'])$c['coverage']='incomplete';
            $contents[$id]=['input'=>$input,'input_sha256'=>ConstructionContract::hash($input),'contract'=>$c,'contract_sha256'=>ConstructionContract::hash($c)];
        }
        $files[self::PATH]=wp_json_encode(['schema'=>'owr-construction-initial-references-2','media'=>$media,'contents'=>$contents]);
        return $files;
    }
    public static function read(array $files): array {
        if(!isset($files[self::PATH]))return ['media'=>[],'contents'=>[]];
        $r=json_decode($files[self::PATH],true,512,JSON_THROW_ON_ERROR);
        if(!in_array($r['schema']??'',['owr-construction-initial-references-1','owr-construction-initial-references-2'],true)||!is_array($r['media']??null))throw new \RuntimeException('Invalid initial reference material');
        $r['contents']=$r['contents']??[];
        return $r;
    }
}
