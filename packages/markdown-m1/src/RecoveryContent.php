<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Application policy, never a transformation of the archived original. */
final class RecoveryContent {
    public const EDITED_BLOCK_TYPES=['wp_block','wp_template','wp_template_part','wp_navigation'];
    public static function editedBlock(array $data,array $postarr): array {
        $id=(int)($postarr['ID']??0);$type=$data['post_type']??'';
        if($type==='revision'){$id=(int)($data['post_parent']??0);$type=get_post_type($id);}
        if(!$id||!in_array($type,self::EDITED_BLOCK_TYPES,true)||!get_post_meta($id,'_ozeki_resilience_m1_origin_url',true))return $data;
        // Standard block/template rendering can bypass the_content. Keep the
        // already-applied boundary when the editor normalizes the restored text.
        $notes=[];$data['post_content']=wp_slash(self::html(wp_unslash($data['post_content']),'edited.block',$notes));
        return $data;
    }
    public static function html(string $input,string $path,array &$report,bool $references=true): string {
        $text=$input;
        // A restored block must not invoke an arbitrary server-side render callback.
        if(preg_match('/<!--\s+wp:/',$text))$text=self::blocks(parse_blocks($text),$path,$report);
        // Code examples remain text, including otherwise supported shortcodes.
        $text=preg_replace_callback('~<(pre|code)\b[^>]*>.*?</\1\s*>~is',static fn($m)=>str_replace(['[',']'],['&#91;','&#93;'],$m[0]),$text);
        // Preserve only supported references, not arbitrary executable shortcodes.
        $text=preg_replace_callback('~\[(/?)([^\s<>&/\[\]=]+)([^\]]*)\]~',static function($m)use($path,&$report,$references){
            $allowed=false;
            // WordPress consumes a final slash as self-closing syntax before
            // parsing attributes. Apply the same boundary; retain the original
            // reference and continue rejecting unknown attributes and commands.
            $attributeText=$m[3];
            if(str_ends_with($attributeText,'/'))$attributeText=substr($attributeText,0,-1);
            $attributeText=trim($attributeText);
            if(!$m[1]&&in_array($m[2],['table','contact-form-7'],true)){
                $attrs=shortcode_parse_atts($attributeText);
                $allowed=is_array($attrs)&&isset($attrs['id'])&&preg_match('/^[A-Za-z0-9_-]+$/D',(string)$attrs['id']);
                foreach((array)$attrs as $key=>$v)if(!in_array($key,['id','title'],true)||!is_string($v)||strpbrk($v,'<>[]')!==false)$allowed=false;
            }
            if(!$m[1]&&$m[2]==='wpmem_form'&&preg_match('/^\s+(login|user_edit|password)\s*\/?$/D',$m[3]))$allowed=true;
            if(!$m[1]&&$m[2]==='wpmem_profile'&&trim($m[3])==='')$allowed=true;
            if(!$m[1]&&$m[2]==='ozeki_markdown_document'){
                $attrs=shortcode_parse_atts($attributeText);
                $allowed=is_array($attrs)&&array_keys($attrs)===['id']&&preg_match('/^[1-9][0-9]*$/D',(string)$attrs['id']);
            }
            if(!$references)$allowed=false;
            if($allowed)return $m[0];
            $report[]=['item'=>$path,'reason'=>'Unrecognized shortcode retained as readable text, not executed'];
            return str_replace(['[',']'],['&#91;','&#93;'],$m[0]);
        },$text);
        $safe=wp_kses_post($text);
        if($safe!==$text)$report[]=['item'=>$path,'reason'=>'Unsafe HTML omitted from application; original retained'];
        return $safe;
    }
    /** A recovered document reference is not permission to bypass its own viewing rules. */
    public static function markdownEmbed($output,string $tag,$attrs,array $match): mixed {
        if($tag!=='ozeki_markdown_document')return $output;
        $context=get_post();$id=is_array($attrs)?($attrs['id']??null):null;
        $doc=is_scalar($id)&&preg_match('/^[1-9][0-9]*$/D',(string)$id)?get_post((int)$id):null;
        $recovered=get_option('ozeki_resilience_site_origin_url')
            ||($context&&get_post_meta($context->ID,'_ozeki_resilience_m1_origin_url',true))
            ||($doc&&get_post_meta($doc->ID,'_ozeki_resilience_m1_origin_url',true));
        if(!$recovered)return $output;
        if(!is_array($attrs)||array_keys($attrs)!==['id'])return '';
        if(!$doc||$doc->post_type!=='ozmd_document')return self::missingDocument((int)$id);
        if(in_array($doc->post_status,['trash','auto-draft'],true)||($doc->post_status!=='publish'&&!current_user_can('read_post',$doc->ID))||post_password_required($doc))return '';
        global $shortcode_tags,$post;
        $callback=$shortcode_tags[$tag]??null;
        if(!is_array($callback)||!($callback[0] instanceof \OzekiMarkdownDocuments\Frontend\DocumentShortcode)||$callback[1]!=='render')return self::missingDocument((int)$id);
        $old=$post;$post=$doc;
        try {
            $restriction=(string)get_post_meta($doc->ID,'_wpmem_block',true);
            $blocked=function_exists('wpmem_is_blocked')?wpmem_is_blocked($doc->ID):in_array($restriction,['1','2'],true);
            if(($blocked||$restriction==='2')&&!is_user_logged_in())return '';
            // Unknown membership extensions must not silently grant a document read.
            if(($blocked||$restriction==='2')&&(!empty($GLOBALS['wpmem']->use_exp)
                ||(function_exists('wpmem_get_post_memberships')&&wpmem_get_post_memberships($doc->ID))))return '';
            $html=$output===false?call_user_func($callback,$attrs):$output;$notes=[];
            if(!is_string($html))return '';
            // Never recursively execute commands contained in the referenced document.
            return self::html($html,'markdown.embed.'.$doc->ID,$notes,false);
        } finally {$post=$old;}
    }
    private static function missingDocument(int $id): string {
        if(!current_user_can('manage_options'))return '';
        return '<p>'.esc_html(sprintf(SetupReadiness::text('Markdown document %d is unavailable. Check the document reference and activate Markdown Documents.','Markdown文書 %d を表示できません。参照先の文書とMarkdown Documentsの有効化を確認してください。'),$id)).'</p>';
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
    private static function formTemplate(string $value,string $path,array &$report): string {
        // Use CF7's grammar rather than interpreting quoted input values as HTML.
        $manager=clone \WPCF7_FormTagsManager::get_instance();
        $masked=$manager->replace_with_placeholders($value);
        $tags=[];$nonce=bin2hex(random_bytes(16));
        $masked=preg_replace_callback('~<('.preg_quote(\WPCF7_HTMLFormatter::placeholder_block,'~').'|'.preg_quote(\WPCF7_HTMLFormatter::placeholder_inline,'~').')\b[^>]*>~',static function($m)use($manager,$path,&$report,&$tags,$nonce){
            $original=$manager->restore_from_placeholders($m[0]);
            // CF7's grammar separates the opening tag at the first closing bracket.
            // Acceptance-style body HTML must still be filtered, not hidden by masking.
            $end=strpos($original,']');
            if($end===false)return '';
            $token='owrcf7'.$nonce.count($tags);
            $tags[$token]=substr($original,0,$end+1).self::formHtml(substr($original,$end+1),$path.'.body',$report);
            return $token;
        },$masked);
        $literalTags=array_map(static fn($tag)=>str_replace(['[',']'],['&#91;','&#93;'],esc_attr($tag)),$tags);
        $parts=wp_html_split(wp_kses_post($masked));
        foreach($parts as &$part)$part=strtr($part,str_starts_with($part,'<')?$literalTags:$tags);
        unset($part);$clean=implode('',$parts);
        if($clean!==$value)$report[]=['item'=>$path,'reason'=>'Unsafe form HTML omitted; recognized input values retained'];
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
        // Instructions are displayed as HTML by ACF; field values and the rest
        // of the definition remain typed data, not HTML input.
        foreach($data['acf_restore_groups']??[] as $g=>$group)foreach($group['fields']??[] as $f=>$field)
            if(isset($field['instructions']))$data['acf_restore_groups'][$g]['fields'][$f]['instructions']=self::html($field['instructions'],'acf.instructions.'.$field['key'],$report,false);
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
                }elseif($key==='_form'&&is_string($value))$value=self::formTemplate($value,$path,$report);
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
