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
    private static function formHtml(string $value,string $path,array &$report): string {
        // Only known HTML templates, never recursive structured-data transforms.
        $clean=wp_kses_post($value);
        if($clean!==$value)$report[]=['item'=>$path,'reason'=>'Unsafe form HTML omitted; original retained'];
        return $clean;
    }
    public static function tablePresentation(array $table): array {
        $mapping=get_option('tablepress_tables',[]);
        if(is_string($mapping))$mapping=json_decode($mapping,true);
        $postId=$mapping['table_post'][(string)($table['id']??'')]??0;
        if(!$postId||!get_post_meta($postId,'_ozeki_resilience_m1_origin_url',true))return $table;
        $notes=[];
        // This hook precedes TablePress shortcode execution. Only change the render
        // copy; cell values, options and later exports remain unchanged.
        foreach($table['data']??[] as $r=>$row)foreach($row as $c=>$cell)
            if(is_string($cell))$table['data'][$r][$c]=self::html($cell,'table.cell',$notes);
        foreach(['name','description'] as $key)if(isset($table[$key]))$table[$key]=self::html($table[$key],'table.'.$key,$notes);
        return $table;
    }
    public static function project(array $data,array &$report): array {
        $types=[];foreach($data['tables']['posts']??[] as $p)$types[(string)$p['ID']]=$p['post_type'];
        foreach($data['tables']['posts']??[] as $i=>$post){
            if(in_array($post['post_type'],['tablepress_table','wpcf7_contact_form','flamingo_inbound'],true))continue;
            foreach(['post_content','post_excerpt','post_title'] as $key){
                if(!isset($post[$key]))continue;$path='posts.'.$post['ID'].'.'.$key;
                $data['tables']['posts'][$i][$key]=self::html($post[$key],$path,$report);
            }
        }
        foreach(['comments'=>['comment_content','comment_author'],'terms'=>['name'],'term_taxonomy'=>['description']] as $table=>$keys)
            foreach($data['tables'][$table]??[] as $i=>$row)foreach($keys as $key)if(isset($row[$key]))$data['tables'][$table][$i][$key]=self::html($row[$key],$table.'.'.$i.'.'.$key,$report);
        foreach($data['tables']['postmeta']??[] as $i=>$row){
            $key=$row['meta_key'];$type=$types[(string)$row['post_id']]??'';
            if($key!=='_menu_item_url'&&($type!=='wpcf7_contact_form'||!in_array($key,['_form','_mail','_mail_2'],true)))continue;
            // Flamingo receipt fields are plain correspondence data, escaped by
            // Flamingo's own UI. A sender's <address> is not an HTML element.
            if(($types[(string)$row['post_id']]??'')==='flamingo_inbound')continue;
            $raw=$row['meta_value'];$path='postmeta.'.$row['post_id'].'.'.$key;
            $serialized=is_serialized($raw);$value=$serialized?unserialize($raw,['allowed_classes'=>false]):$raw;
            if($key==='_menu_item_url'&&is_string($value)){
                $url=esc_url_raw($value);
                if($url!==$value)$report[]=['item'=>$path,'reason'=>'Unsafe navigation URL omitted'];
                $value=$url;
            }
            // CF7 form tags are a separate, recognised input grammar, not WordPress shortcodes.
            if(($types[(string)$row['post_id']]??'')==='wpcf7_contact_form'){
                if(in_array($key,['_mail','_mail_2'],true)&&is_array($value)){
                    if(!empty($value['use_html'])&&isset($value['body']))$value['body']=self::formHtml($value['body'],$path.'.body',$report);
                    foreach(['sender','recipient','subject'] as $header)if(isset($value[$header])&&strpbrk($value[$header],"\r\n")!==false){$value[$header]=str_replace(["\r","\n"],'',$value[$header]);$report[]=['item'=>$path.'.'.$header,'reason'=>'Unexpected mail header line breaks omitted'];}
                    if(!empty($value['attachments'])){$value['attachments']='';$report[]=['item'=>$path.'.attachments','reason'=>'Archived local mail attachment paths require destination review'];}
                }elseif($key==='_form'&&is_string($value))$value=self::formHtml($value,$path,$report);
            }
            $data['tables']['postmeta'][$i]['meta_value']=$serialized?serialize($value):$value;
        }
        // Member values/definitions and ACF values/definitions are typed data.
        // Only explicit member HTML messages and terms are presentation fields.
        foreach(['options','membership'] as $section){
            if($section==='membership'){
                if(!isset($data['membership']['settings']))continue;
                $settings=&$data['membership']['settings'];
            }else{
                if(!isset($data['options']))continue;
                $settings=&$data['options'];
            }
            foreach($settings['wpmembers_dialogs']??[] as $key=>$value)if(is_string($value))$settings['wpmembers_dialogs'][$key]=self::html($value,'member.dialog.'.$key,$report);
            if(isset($settings['wpmembers_tos'])&&is_string($settings['wpmembers_tos']))$settings['wpmembers_tos']=self::html($settings['wpmembers_tos'],'member.terms',$report);
            unset($settings);
        }
        return $data;
    }
}
