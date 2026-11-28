<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;

/** Read the ordinary registration result; never manufacture URLs or plugin hashes. */
final class ConstructionResultReferences {
    public static function read(string $route,array $response): array {
        $values=[];$id=(int)($response['id']??0);if(!$id)return $values;
        if(preg_match('~^/wp/v2/media(?:/\d+(?:/edit)?)?$~D',$route)){
            if(isset($response['source_url']))$values['image-url:full']=$response['source_url'];
            foreach($response['media_details']['sizes']??[] as $size=>$data)if(isset($data['source_url']))$values['image-url:'.$size]=$data['source_url'];
        }
        if(preg_match('~^/contact-form-7/v1/contact-forms(?:/\d+)?$~D',$route)&&function_exists('wpcf7_contact_form')){
            $form=wpcf7_contact_form($id);if($form)$values['cf7-hash']=$form->hash();
        }
        return $values;
    }
}
