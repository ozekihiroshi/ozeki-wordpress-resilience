<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Non-mutating application checks. Structured values are not HTML documents. */
final class ConstructionSafety {
    private const ENDPOINTS=['/wp/v2/posts','/wp/v2/pages','/wp/v2/media','/contact-form-7/v1/contact-forms','wordpress.media-upload','wordpress.media-edit','wordpress.media-delete','wordpress.edit','markdown.import','tablepress.import','tablepress.save','members.settings','members.create','members.profile','acf.import','flamingo.add'];
    public static function html(string $text): bool {return wp_kses_post($text)===$text;}
    public static function form(array $input): array {
        $issues=[];
        if(isset($input['form'])&&(!is_string($input['form'])||!self::html($input['form'])))$issues[]='form_html_requires_review';
        if(isset($input['additional_settings'])){
            if(!is_string($input['additional_settings']))$issues[]='form_settings_type';
            else foreach(preg_split('/\R/',$input['additional_settings']) as $line)if(trim($line)!==''&&!preg_match('/^\s*(?:subscribers_only|demo_mode|skip_mail|do_not_store)\s*:\s*(?:on|off|true|false)\s*$/D',$line))$issues[]='form_setting_requires_review';
        }
        foreach(['mail','mail_2'] as $key)if(!empty($input[$key]['attachments']))$issues[]='form_attachment_reference_required';
        return array_values(array_unique($issues));
    }
    public static function inspect(array $plan): array {
        $issues=[];
        foreach($plan['forms']['forms']??[] as $form){$why=self::form($form['input']);if($why)$issues['form:'.$form['origin_id']]=$why;}
        foreach($plan['tail']??[] as $e){
            if($e['state']==='rejected')continue;
            $c=$e['contract'];
            if(($c['coverage']??'')!=='complete'){$issues['operation:'.$e['sequence']]=['incomplete_contract'];continue;}
            if(!in_array($c['endpoint']??'',self::ENDPOINTS,true)){$issues['operation:'.$e['sequence']]=['unrecognized_registration_entry'];continue;}
            $a=$c['arguments']??[];
            $allowed=match($c['endpoint']){
                '/wp/v2/posts','/wp/v2/pages'=>['title','content','excerpt','status','slug','date','date_gmt','password','author','parent','featured_media','categories','tags','comment_status','ping_status','menu_order'],
                '/wp/v2/media'=>['title','caption','description','alt_text','post','author'],
                '/contact-form-7/v1/contact-forms'=>['title','locale','form','mail','mail_2','messages','additional_settings','context'],
                default=>null,
            };
            if($allowed!==null&&array_diff(array_keys($a),$allowed))$issues['operation:'.$e['sequence']][]='unrecognized_registration_field';
            if(in_array($c['endpoint'],['members.create','members.profile'],true)){
                $body=$a['body']??[];
                if(isset($body['role'])&&$body['role']!=='subscriber')$issues['operation:'.$e['sequence']][]='privilege_transfer_refused';
                foreach(array_keys($body) as $key)if(preg_match('/(?:capabilities|user_level|user_pass|session_tokens|^pass[12]$|^pwd$)/i',$key))$issues['operation:'.$e['sequence']][]='credential_or_privilege_transfer_refused';
            }
            if($c['endpoint']==='/contact-form-7/v1/contact-forms'){
                $why=self::form($c['arguments']);if($why)$issues['operation:'.$e['sequence']]=$why;
            }
            // Never apply wp_kses_post to receipt values, member fields, table
            // cells, ACF definitions, or the preserved Markdown source.
        }
        return $issues;
    }
}
