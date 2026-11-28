<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Classify only declared core attributes at capture time, never infer numeric IDs. */
final class ConstructionBlocks {
    public static function capture(string $text,array $path,array &$c): string {
        $rest=$text;
        $schemas=[
            'image'=>['id','url','alt','caption','sizeSlug','linkDestination','align','width','height','aspectRatio','scale','className','anchor'],
            'gallery'=>['ids','columns','imageCrop','linkTo','sizeSlug','align','className','caption'],
            'paragraph'=>['align','className','dropCap','fontSize','anchor'],
            'heading'=>['level','textAlign','className','fontSize','anchor'],
            'quote'=>['textAlign','className','anchor'],
            'group'=>['tagName','className','align','layout'],
            'columns'=>['verticalAlignment','isStackedOnMobile','className','align'],
            'column'=>['verticalAlignment','width','className'],
            'shortcode'=>[],
        ];
        preg_match_all('~<!--\s+wp:([a-z0-9/-]+)(?:\s+(\{.*?\}))?\s*(/)?-->~s',$text,$matches,PREG_SET_ORDER|PREG_OFFSET_CAPTURE);
        foreach($matches as $m){
            $name=$m[1][0];if(str_starts_with($name,'core/'))$name=substr($name,5);
            if(!isset($schemas[$name])){$c['reasons'][]='No source block contract: '.$name;continue;}
            $raw=$m[2][0]??'';$attrs=$raw===''?[]:json_decode($raw,true);
            if(!is_array($attrs)){$c['reasons'][]='Invalid block attributes';continue;}
            $refs=[];
            foreach($attrs as $key=>$value){
                if(!in_array($key,$schemas[$name],true)){$c['reasons'][]='No source attribute contract: '.$name.'.'.$key;continue;}
                if($name==='image'&&$key==='id'){
                    if(!is_int($value)||$value<1)$c['reasons'][]='Invalid image block identity';else $refs[]=['path'=>['id'],'type'=>'post','id'=>$value,'source_state'=>ConstructionEmbeds::imageState($value)];
                }elseif($name==='gallery'&&$key==='ids'){
                    if(!is_array($value)){$c['reasons'][]='Invalid gallery identities';continue;}
                    foreach($value as $i=>$id)if(!is_int($id)||$id<1)$c['reasons'][]='Invalid gallery identity';else $refs[]=['path'=>['ids',$i],'type'=>'post','id'=>$id,'source_state'=>ConstructionEmbeds::imageState($id)];
                }elseif($name==='image'&&$key==='url'){
                    $ref=is_string($value)?ConstructionEmbeds::imageReference($value):null;
                    if(!$ref||isset($attrs['id'])&&(int)$attrs['id']!==(int)$ref['id'])$c['reasons'][]='Unresolved/disagreeing block image URL';else $refs[]=['path'=>['url']]+$ref;
                }elseif($key==='layout'){
                    if(!is_array($value)||array_diff(array_keys($value),['type','orientation','justifyContent','flexWrap']))$c['reasons'][]='Unknown layout behavior';
                }elseif(is_array($value)||is_object($value))$c['reasons'][]='Unknown structured block attribute: '.$key;
            }
            if($refs)$c['json_spans'][]=['path'=>$path,'offset'=>$m[2][1],'length'=>strlen($raw),'literal'=>$raw,'value'=>$attrs,'references'=>$refs];
            $rest=substr_replace($rest,str_repeat(' ',strlen($m[0][0])),$m[0][1],strlen($m[0][0]));
        }
        // Closing comments carry no argument. Their type must still be known.
        $rest=preg_replace_callback('~<!--\s+/wp:([a-z0-9/-]+)\s*-->~',function($m)use($schemas){$name=str_starts_with($m[1],'core/')?substr($m[1],5):$m[1];return isset($schemas[$name])?str_repeat(' ',strlen($m[0])):$m[0];},$rest);
        return $rest;
    }
}
