<?php
declare(strict_types=1);
namespace Owr\M1;

/** Lossless content/metadata separation. This is a storage codec, not a new trust policy. */
final class AssetFormat
{
    public const SCHEMA='owr-separated-assets-1';

    /** Unknown fields stay in metadata unchanged; only explicitly identified content is extracted. */
    public static function split(array $value): array {
        $files=[];$slots=[];
        $walk=function(array &$node,array $path=[]) use (&$walk,&$files,&$slots): void {
            foreach($node as $key=>&$v){
                $p=[...$path,$key];$ext=null;$encoding='string';$body=null;
                if(is_string($v)){
                    if($key==='post_content')$ext=($node['post_type']??'')==='tablepress_table'?'json':'html';
                    elseif($key==='post_excerpt'||$key==='comment_content')$ext='txt';
                    elseif($key==='meta_value'&&($node['meta_key']??'')==='_ozmd_source')$ext='md';
                    elseif($key==='meta_value'&&($node['meta_key']??'')==='_fields'){
                        // Flamingo's named submitted fields are values, not executable configuration.
                        $decoded=@unserialize($v,['allowed_classes'=>false]);
                        if(is_array($decoded)&&self::plain($decoded)){
                            $ext='json';$encoding='serialized';$body=self::json($decoded);
                        }
                    }
                    elseif(in_array($key,['user_login','user_nicename','user_email','user_url','display_name'],true)&&isset($node['user_pass']))$ext='txt';
                }
                if($ext!==null){
                    $name='data/'.hash('sha256',self::json($p)).'.'.$ext;
                    $files[$name]=$body??$v;
                    $slot=['path'=>$p,'file'=>$name,'encoding'=>$encoding];
                    // Preserve noncanonical serialized bytes without discarding any original information.
                    if($encoding==='serialized'&&serialize($decoded)!==$v)$slot['original_serialization']=$v;
                    $slots[]=$slot;$v=null;
                }elseif(is_array($v))$walk($v,$p);
            }unset($v);
        };
        $walk($value);
        return ['schema'=>self::SCHEMA,'metadata'=>$value,'slots'=>$slots,'files'=>$files];
    }

    private static function plain(mixed $v): bool {
        if(is_array($v)){foreach($v as $item)if(!self::plain($item))return false;return true;}
        return is_scalar($v)||$v===null;
    }
    private static function json(array $v): string {return json_encode($v,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);}

    public static function join(array $layout,array $files): array {
        if(($layout['schema']??'')!==self::SCHEMA||!is_array($layout['metadata']??null)||!is_array($layout['slots']??null))throw new \RuntimeException('Invalid separated asset metadata.');
        $value=$layout['metadata'];$seen=[];
        foreach($layout['slots'] as $slot){
            $path=$slot['path']??null;$file=$slot['file']??'';
            if(!is_array($path)||!$path||!preg_match('~^data/[a-f0-9]{64}\.(md|html|txt|json)$~D',$file)||!isset($files[$file])||!is_string($files[$file]))throw new \RuntimeException('Missing or invalid independent original.');
            $id=self::json($path);if(isset($seen[$id]))throw new \RuntimeException('Duplicate original mapping.');$seen[$id]=true;
            $target=&$value;
            foreach($path as $key){if((!is_string($key)&&!is_int($key))||!is_array($target)||!array_key_exists($key,$target))throw new \RuntimeException('Invalid original mapping.');$target=&$target[$key];}
            if($target!==null)throw new \RuntimeException('Original mapping overwrites metadata.');
            if(($slot['encoding']??'')==='string')$target=$files[$file];
            elseif(($slot['encoding']??'')==='serialized'){
                $data=json_decode($files[$file],true,512,JSON_THROW_ON_ERROR);
                if(!is_array($data)||!self::plain($data))throw new \RuntimeException('Invalid submitted fields.');
                $target=serialize($data);
                if(isset($slot['original_serialization'])){
                    $original=$slot['original_serialization'];
                    if(!is_string($original)||@unserialize($original,['allowed_classes'=>false])!==$data)throw new \RuntimeException('Submitted field serialization mismatch.');
                    $target=$original;
                }
            }else throw new \RuntimeException('Unknown original encoding.');
            unset($target);
        }
        if(count($files)!==count($seen))throw new \RuntimeException('Unmapped independent original.');
        return $value;
    }
}
