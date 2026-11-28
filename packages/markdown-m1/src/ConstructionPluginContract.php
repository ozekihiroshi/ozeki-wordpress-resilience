<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Only source-observed arguments. Unknown semantics remain incomplete. */
final class ConstructionPluginContract {
    public static function describe(string $op,array $i,array $c): array {
        $b=$i['body']??[];$a=$b['action']??'';$path=$i['path']??'';
        $c['arguments']=['body'=>$b,'files'=>$i['files']??[],'nonce_fields'=>$i['nonce_fields']??null];
        if($op==='admin'&&!isset($i['nonce_fields']))$c['reasons'][]='Missing normal form participant contract (nonce field names)';
        if($op==='rest'&&preg_match('~^/wp/v2/media/([1-9][0-9]*)(/edit)?$~D',$i['route']??'',$m)){
            $id=(int)$m[1];$c['target']=['type'=>'post','id'=>$id];$c['arguments']=$b;
            if(($i['method']??'POST')==='DELETE'){
                $c['endpoint']='wordpress.media-delete';$c['completion']='media-delete';$c['arguments']=['force'=>$i['query']['force']??null];
                if(!in_array($c['arguments']['force'],[true,1,'true','1'],true)||$b)$c['reasons'][]='Only explicit ordinary permanent media deletion is defined';
            }elseif(!empty($m[2])){
                $c['endpoint']='wordpress.media-edit';$c['output_type']='post';$c['result_mode']='create';
                self::keys($b,['src','modifiers','rotation','x','y','width','height','flip','title','caption','description','alt_text'],$c);
                $ref=is_string($b['src']??null)?ConstructionEmbeds::imageReference($b['src']):null;
                if(!$ref||(int)$ref['id']!==$id)$c['reasons'][]='Image edit source URL/identity not captured';else $c['references'][]=['path'=>['src']]+$ref;
            }else{
                $c['endpoint']='/wp/v2/media';$c['output_type']='post';
                self::keys($b,['title','caption','description','alt_text','author','post'],$c);
                foreach(['author'=>'user','post'=>'post'] as $key=>$type)if(!empty($b[$key]))self::ref($c,[$key],$type,$b[$key]);
            }
        }elseif($op==='rest'&&($i['route']??'')==='/wp/v2/media'){
            $c['endpoint']='wordpress.media-upload';$c['output_type']='post';$c['arguments']=$i['upload']??[];
            if($b)$c['reasons'][]='Media upload fields require a separate typed contract';
            if(!preg_match('~^image/(?:png|jpeg|gif|webp)$~D',$c['arguments']['content_type']??'')||!preg_match('~^attachment; filename="[A-Za-z0-9_.-]+"$~D',$c['arguments']['content_disposition']??'')||base64_decode($c['arguments']['base64']??'',true)==='')$c['reasons'][]='Unclassified media upload';
        }elseif($op==='rest'&&preg_match('~^/contact-form-7/v1/contact-forms(?:/([1-9][0-9]*))?$~D',$i['route']??'',$m)){
            $c['endpoint']='/contact-form-7/v1/contact-forms';$c['arguments']=$b;$c['output_type']='post';
            if(isset($m[1]))$c['target']=['type'=>'post','id'=>(int)$m[1]];
            self::keys($b,['title','locale','form','mail','mail_2','messages','additional_settings','context'],$c);
            if(($b['context']??'')!=='save')$c['reasons'][]='CF7 request does not commit a save';
            // Tags in the form are CF7 input definitions, NOT WordPress embeds.
            preg_match_all('~\[(/?[A-Za-z][\w-]*\*?)[^\]]*\]~',$b['form']??'',$tags);
            foreach($tags[1] as $tag)if(!in_array(trim($tag,'/*'),['text','email','url','tel','number','date','textarea','select','checkbox','radio','acceptance','quiz','submit','hidden'],true))$c['reasons'][]='CF7 tag needs a source input/reference contract: '.$tag;
            foreach(['mail','mail_2'] as $key)if(!empty($b[$key]['attachments']))$c['reasons'][]='CF7 attachment path needs a source file reference';
        }elseif($op==='flamingo-add'){
            $c['endpoint']='flamingo.add';$c['arguments']=$i;$c['output_type']='post';
            self::ref($c,['form_id'],'post',$i['form_id']??null);
            // Channel is selected by the normal CF7 channel API from that form.
            // Its source literal is preserved in input; no string-value compensation.
            if(!is_array($i['arguments']??null)||!isset($i['arguments']['channel']))$c['reasons'][]='Missing normal receipt channel/input';
        }elseif($op==='admin'&&$a==='ozmd_import_document'){
            $c['endpoint']='markdown.import';$c['output_type']='post';
            self::keys($b,['action'],$c);$f=$i['files']['ozmd_file']??null;
            if(!$f||base64_decode($f['base64']??'',true)===false)$c['reasons'][]='Missing document upload';
            else {
                $c['arguments']['source_text']=base64_decode($f['base64']);
                $c['text_upload']=['path'=>['files','ozmd_file','base64'],'text_path'=>['source_text']];
                ConstructionEmbeds::capture($c['arguments']['source_text'],['source_text'],$c,'markdown');
            }
        }elseif($op==='admin'&&$a==='tablepress_import'){
            $c['endpoint']='tablepress.import';$c['output_type']='table';
            if(($b['import']['source']??'')!=='form-field'||($b['import']['type']??'')!=='add')$c['reasons'][]='Only normal single-table JSON add has a capture contract';
            $t=json_decode($b['import']['form-field']??'',true);
            if(!is_array($t))$c['reasons'][]='Missing table JSON';
            else self::table($t,$c);
            self::keys($b,['action','import'],$c);
        }elseif($op==='admin'&&$a==='tablepress_save_table'){
            $c['endpoint']='tablepress.save';$c['output_type']='table';
            $id=$b['tablepress']['id']??null;$c['target']=['type'=>'table','id'=>(string)$id];self::ref($c,['body','tablepress','id'],'table',$id);
            self::keys($b,['action','tablepress'],$c);
            $t=$b['tablepress']??[];$t['data']=json_decode($t['data']??'',true);self::table($t,$c);
        }elseif($op==='admin'&&($i['query']['page']??'')==='acf-tools'&&($b['import_type']??'')==='json'){
            $c['endpoint']='acf.import';$c['completion']='acf-import';
            $groups=json_decode(base64_decode($i['files']['acf_import_file']['base64']??'',true)?:'',true);
            $c['expected_keys']=[];
            if(!is_array($groups)||!$groups)$c['reasons'][]='Missing ACF definitions';
            else foreach($groups as $g){
                if(empty($g['key']))$c['reasons'][]='Missing ACF group key';else $c['expected_keys'][]=$g['key'];
                // ID-bearing locations cannot be guessed from numeric-looking values.
                foreach($g['location']??[] as $rules)foreach($rules as $rule)if(!in_array($rule['param']??'',['post_type','post_status'],true))$c['reasons'][]='ACF location needs a source typed reference';
            }
            self::keys($b,['import_type'],$c);
        }elseif($op==='admin'&&($i['query']['page']??'')==='wpmem-settings'&&isset($b['wpmem_admin_a'])){
            $c['endpoint']='members.settings';$c['completion']='option';
            foreach(['wpmem_settings_mspage','wpmem_settings_regpage','wpmem_settings_logpage'] as $k)if(!empty($b[$k]))self::ref($c,['body',$k],'post',$b[$k]);
            if(!in_array($b['wpmem_admin_a'],['update_settings','add_field','edit_field'],true))$c['reasons'][]='Unclassified member settings action: '.$b['wpmem_admin_a'];
            if($b['wpmem_admin_a']==='update_settings'){
                foreach(array_keys($b) as $key)if(!preg_match('~^(?:wpmem_admin_a|wpmem_(?:block|show_login|show_reg)_(?:post|page)|wpmem_autoex_(?:post|page)(?:_len|_text)?|wpmem_settings_(?:captcha|logpage|logurl|regpage|regurl|mspage|msurl|cssurl|moderate|act_link|products))$~D',$key))$c['reasons'][]='Unclassified member setting: '.$key;
                foreach(['logurl','regurl','msurl','cssurl'] as $key)if(!empty($b['wpmem_settings_'.$key]))$c['reasons'][]='Member URL requires a source URL contract: '.$key;
            }else{
                self::keys($b,['wpmem_admin_a','add_name','add_option','add_type','add_placeholder','add_pattern','add_title','add_timestamp_display','add_min','add_max','add_rows','add_cols','add_file_value','add_checkbox_label','add_checked_value','add_delimiter_value','add_dropdown_value','add_radio_value','add_hidden_value','add_terms_check_href','add_order_id','add_display','add_required','add_profile','add_checked_default','field_arr'],$c);
                if($b['wpmem_admin_a']==='edit_field'){
                    // The ordinary form emits meta_key, not a database/array index.
                    $c['definition_target']=['type'=>'member-field-key','key'=>$b['field_arr']??null];
                    if(empty($b['field_arr'])||($b['field_arr']!==($b['add_option']??null)))$c['reasons'][]='Member definition rename needs a separate input contract';
                }
                if(!in_array($b['add_type']??'',['text','textarea','email','url','number','select','radio','checkbox'],true))$c['reasons'][]='Member definition needs a source type contract';
            }
        }elseif($op==='admin'&&in_array($path,['user-new.php','user-edit.php'],true)){
            $c['endpoint']=$path==='user-new.php'?'members.create':'members.profile';$c['output_type']='user';
            if($path==='user-edit.php'){$c['target']=['type'=>'user','id'=>(int)($b['user_id']??0)];self::ref($c,['body','user_id'],'user',$b['user_id']??null);}
            $c['password_policy']='new-account-reset';
            if(isset($b['checkuser_id']))$c['destination_actor_paths']=[['body','checkuser_id']];
            $allowed=['action','from','checkuser_id','admin_color','admin_bar_front','locale','user_login','role','first_name','last_name','nickname','display_name','email','url','description','user_id','pw_weak'];
            foreach($i['member_fields']??[] as $key=>$f){if(in_array($f['type'],['text','textarea','email','url','number','select','radio','checkbox'],true))$allowed[]=$key;else $c['reasons'][]='Member value needs a source type contract: '.$key;}
            self::keys($b,$allowed,$c);
            if(($b['role']??'subscriber')!=='subscriber')$c['reasons'][]='Account role outside member registration contract';
        }elseif($op==='admin'&&$path==='post.php'&&$a==='editpost'){
            $c['endpoint']='wordpress.edit';$c['output_type']='post';$c['target']=['type'=>'post','id'=>(int)($b['post_ID']??0)];
            self::ref($c,['body','post_ID'],'post',$b['post_ID']??null);
            foreach(['post_parent'=>'post','post_author_override'=>'user','_acf_post_id'=>'post'] as $key=>$type)if(!empty($b[$key]))self::ref($c,['body',$key],$type,$b[$key]);
            // user_ID is the executing administrator, not the content's author.
            $c['destination_actor_paths']=[['body','user_ID']];
            self::keys($b,['action','post_ID','post_type','post_title','post_name','post_status','post_password','post_author_override','post_parent','content','post_content','excerpt','comment_status','ping_status','user_ID','original_post_status','edit_date','aa','mm','jj','hh','mn','ss','ozmd_source','acf','_acf_screen','_acf_post_id','wpmem_block'],$c);
            foreach(['content','post_content','excerpt','ozmd_source'] as $key)if(isset($b[$key]))ConstructionEmbeds::capture((string)$b[$key],['body',$key],$c,$key==='ozmd_source'?'markdown':'html');
            if(isset($b['acf']))foreach($b['acf'] as $key=>$value){
                $field=$i['field_contracts'][$key]??null;
                if(!$field){$c['reasons'][]='Missing source ACF field type: '.$key;continue;}
                $type=$field['type'];$reference=['image'=>'post','file'=>'post','post_object'=>'post','relationship'=>'post','user'=>'user'][$type]??null;
                if($reference){foreach(is_array($value)?$value:[$value] as $n=>$id)if($id!==''&&$id!==null)self::ref($c,is_array($value)?['body','acf',$key,$n]:['body','acf',$key],$reference,$id);}
                elseif(!in_array($type,['text','textarea','number','email','url','password','select','checkbox','radio','button_group','true_false','date_picker','date_time_picker','time_picker','color_picker'],true))$c['reasons'][]='Unclassified ACF value type: '.$type;
            }
        }else $c['reasons'][]='No source contract for this operation';
        if(!$c['reasons'])$c['coverage']='complete';return $c;
    }
    private static function keys(array $b,array $allowed,array &$c): void {foreach(array_keys($b) as $k)if(!in_array($k,$allowed,true))$c['reasons'][]='Unclassified input field: '.$k;}
    private static function table(array $t,array &$c): void {
        if(!is_array($t['data']??null)){$c['reasons'][]='Missing structured table cells';return;}
        foreach($t['data'] as $row){if(!is_array($row)){$c['reasons'][]='Invalid table row';continue;}foreach($row as $cell)if(!is_string($cell)||preg_match('~\[/?[A-Za-z_]|https?://|<[/!?A-Za-z]~',$cell))$c['reasons'][]='Table cell needs a source reference/execution contract';}
    }
    private static function ref(array &$c,array $path,string $type,mixed $id): void {
        if(!is_scalar($id)||(string)$id===''||($type!=='table'&&(!ctype_digit((string)$id)||(int)$id<1))){$c['reasons'][]='Invalid typed reference';return;}
        $c['references'][]=['path'=>$path,'type'=>$type,'id'=>$type==='table'?(string)$id:(int)$id];
    }
}
