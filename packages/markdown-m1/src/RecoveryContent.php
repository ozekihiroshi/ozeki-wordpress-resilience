<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Application policy, never a transformation of the archived original. */
final class RecoveryContent {
    public static function html(string $input,string $path,array &$report): string {
        $text=$input;
        // A restored block must not invoke an arbitrary server-side render callback.
        if(preg_match('/<!--\s+wp:/',$text))$text=self::blocks(parse_blocks($text),$path,$report);
        // Code examples remain text, including otherwise supported shortcodes.
        $text=preg_replace_callback('~<(pre|code)\b[^>]*>.*?</\1\s*>~is',static fn($m)=>str_replace(['[',']'],['&#91;','&#93;'],$m[0]),$text);
        // Preserve only supported references, not arbitrary executable shortcodes.
        $text=preg_replace_callback('~\[(/?)([^\s<>&/\[\]=]+)([^\]]*)\]~',static function($m)use($path,&$report){
            $allowed=false;
            if(!$m[1]&&in_array($m[2],['table','contact-form-7'],true)){
                $attrs=shortcode_parse_atts(trim($m[3]));
                $allowed=is_array($attrs)&&isset($attrs['id'])&&preg_match('/^[A-Za-z0-9_-]+$/D',(string)$attrs['id']);
                foreach((array)$attrs as $key=>$v)if(!in_array($key,['id','title'],true)||!is_string($v)||strpbrk($v,'<>[]')!==false)$allowed=false;
            }
            if(!$m[1]&&$m[2]==='wpmem_form'&&preg_match('/^\s+(login|user_edit|password)\s*\/?$/D',$m[3]))$allowed=true;
            if(!$m[1]&&$m[2]==='wpmem_profile'&&trim($m[3])==='')$allowed=true;
            if($allowed)return $m[0];
            $report[]=['item'=>$path,'reason'=>'Unrecognized shortcode retained as readable text, not executed'];
            return str_replace(['[',']'],['&#91;','&#93;'],$m[0]);
        },$text);
        $safe=wp_kses_post($text);
        if($safe!==$text)$report[]=['item'=>$path,'reason'=>'Unsafe HTML omitted from application; original retained'];
        return $safe;
    }
    private static function blocks(array $blocks,string $path,array &$report): string {
        $out='';
        foreach($blocks as $b){
            if($b['blockName']===null){$out.=$b['innerHTML'];continue;}
            // Keep the editor structure of a small, explicit set of static core
            // blocks. No bindings, reusable-block references or dynamic instructions.
            $static=['core/paragraph','core/heading','core/code','core/preformatted','core/list','core/list-item','core/quote','core/table','core/separator'];
            if(in_array($b['blockName'],$static,true)){
                $attrs=[];
                foreach($b['attrs'] as $key=>$value){
                    $valid=($key==='level'&&$b['blockName']==='core/heading'&&is_int($value)&&$value>=1&&$value<=6)
                        ||($key==='align'&&in_array($value,['left','center','right','wide','full'],true))
                        ||($key==='className'&&is_string($value)&&preg_match('/^[A-Za-z0-9_ -]*$/D',$value))
                        ||(in_array($key,['ordered','reversed'],true)&&$b['blockName']==='core/list'&&is_bool($value))
                        ||($key==='start'&&$b['blockName']==='core/list'&&is_int($value)&&$value>=0)
                        ||($key==='hasFixedLayout'&&$b['blockName']==='core/table'&&is_bool($value));
                    if($valid)$attrs[$key]=$value;
                    else $report[]=['item'=>$path.'.block.'.$key,'reason'=>'Block instruction outside static editing rules omitted'];
                }
                $body='';$children=$b['innerBlocks'];
                foreach($b['innerContent'] as $part)$body.=$part===null?self::blocks([array_shift($children)],$path,$report):$part;
                $out.=get_comment_delimited_block_content($b['blockName'],$attrs,$body);
                continue;
            }
            // Keep stored presentation HTML, without reactivating archived block instructions.
            if($b['innerContent']){foreach($b['innerContent'] as $part)$out.=$part===null?self::blocks([array_shift($b['innerBlocks'])],$path,$report):$part;}
            else {$out.=esc_html(serialize_block($b));$report[]=['item'=>$path,'reason'=>'Dynamic block requires review; archived instructions not executed'];}
        }
        return $out;
    }
    public static function tree(mixed $value,string $path,array &$report): mixed {
        if(is_array($value)){foreach($value as $k=>&$v)$v=self::tree($v,$path.'.'.$k,$report);unset($v);return $value;}
        return is_string($value)?self::html($value,$path,$report):$value;
    }
    private static function formValue(mixed $value,string $path,array &$report): mixed {
        if(is_array($value)){foreach($value as $k=>&$v)$v=self::formValue($v,$path.'.'.$k,$report);unset($v);return $value;}
        if(!is_string($value))return $value;
        // Plain field values (for example "current < 5 A") are not HTML.
        // Do not entity-encode ordinary data merely because it contains '<'.
        if(!preg_match('/<\/?[a-zA-Z][^>]*>/s',$value))return $value;
        $clean=wp_kses_post($value);
        if($clean!==$value)$report[]=['item'=>$path,'reason'=>'Unsafe form HTML omitted; original retained'];
        return $clean;
    }
    public static function project(array $data,array &$report): array {
        $types=[];foreach($data['tables']['posts']??[] as $p)$types[(string)$p['ID']]=$p['post_type'];
        foreach($data['tables']['posts']??[] as $i=>$post){
            foreach(['post_content','post_excerpt','post_title'] as $key){
                if(!isset($post[$key]))continue;$path='posts.'.$post['ID'].'.'.$key;
                // TablePress stores structured cell data in post_content, not a HTML document.
                if($key==='post_content'&&$post['post_type']==='tablepress_table'){
                    $json=json_decode($post[$key],true);
                    if(is_array($json))$data['tables']['posts'][$i][$key]=Store::json(self::tree($json,$path,$report));
                    else $data['tables']['posts'][$i][$key]=self::html($post[$key],$path,$report);
                }elseif($key==='post_content'&&$post['post_type']==='wpcf7_contact_form'){
                    // CF7 keeps a flattened search copy of its properties here.
                    // Input/mail tags are not WordPress executable shortcodes.
                    // This non-public search text is not a rendered form template.
                    // The actual _form property is filtered separately below.
                    $data['tables']['posts'][$i][$key]=$post[$key];
                }else $data['tables']['posts'][$i][$key]=self::html($post[$key],$path,$report);
            }
        }
        foreach(['comments'=>['comment_content','comment_author'],'terms'=>['name'],'term_taxonomy'=>['description']] as $table=>$keys)
            foreach($data['tables'][$table]??[] as $i=>$row)foreach($keys as $key)if(isset($row[$key]))$data['tables'][$table][$i][$key]=self::html($row[$key],$table.'.'.$i.'.'.$key,$report);
        foreach($data['tables']['postmeta']??[] as $i=>$row){
            $key=$row['meta_key'];if($key==='_ozmd_source')continue;
            // Flamingo receipt fields are plain correspondence data, escaped by
            // Flamingo's own UI. A sender's <address> is not an HTML element.
            if(($types[(string)$row['post_id']]??'')==='flamingo_inbound')continue;
            $raw=$row['meta_value'];$path='postmeta.'.$row['post_id'].'.'.$key;
            $serialized=is_serialized($raw);$value=$serialized?unserialize($raw,['allowed_classes'=>false]):$raw;
            $json=($types[(string)$row['post_id']]??'')==='tablepress_table'&&str_starts_with($key,'_tablepress_');
            if($json)$value=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
            if($key==='_menu_item_url'&&is_string($value)){
                $url=esc_url_raw($value);
                if($url!==$value)$report[]=['item'=>$path,'reason'=>'Unsafe navigation URL omitted'];
                $value=$url;
            }
            // CF7 form tags are a separate, recognised input grammar, not WordPress shortcodes.
            if(($types[(string)$row['post_id']]??'')==='wpcf7_contact_form'){
                if(in_array($key,['_mail','_mail_2'],true)&&is_array($value)){
                    if(!empty($value['use_html'])&&isset($value['body']))$value['body']=self::formValue($value['body'],$path.'.body',$report);
                    foreach(['sender','recipient','subject'] as $header)if(isset($value[$header])&&strpbrk($value[$header],"\r\n")!==false){$value[$header]=str_replace(["\r","\n"],'',$value[$header]);$report[]=['item'=>$path.'.'.$header,'reason'=>'Unexpected mail header line breaks omitted'];}
                    if(!empty($value['attachments'])){$value['attachments']='';$report[]=['item'=>$path.'.attachments','reason'=>'Archived local mail attachment paths require destination review'];}
                }else $value=self::formValue($value,$path,$report);
            }
            elseif(($types[(string)$row['post_id']]??'')==='tablepress_table')$value=self::tree($value,$path,$report);
            else $value=self::formValue($value,$path,$report);
            $data['tables']['postmeta'][$i]['meta_value']=$json?Store::json($value):($serialized?serialize($value):$value);
        }
        if(isset($data['membership']))$data['membership']=self::formValue($data['membership'],'membership',$report);
        if(isset($data['acf_restore_groups']))$data['acf_restore_groups']=self::formValue($data['acf_restore_groups'],'acf.definitions',$report);
        return $data;
    }
}
