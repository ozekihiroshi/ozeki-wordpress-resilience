<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionBlocks.php';

/** Source-time syntax classification. The follower only substitutes recorded spans. */
final class ConstructionEmbeds {
    public static function capture(string $text,array $path,array &$contract,string $format='html'): void {
        $rest=$format==='html'?ConstructionBlocks::capture($text,$path,$contract):$text;
        $pattern='~\[(ozeki_markdown_document|table|contact-form-7)\s+id=(?:"([A-Za-z0-9_-]+)"|\'([A-Za-z0-9_-]+)\'|([A-Za-z0-9_-]+))(?:\s+title="[^"\[\]]*")?\s*/?\]~';
        preg_match_all($pattern,$rest,$matches,PREG_SET_ORDER|PREG_OFFSET_CAPTURE);
        foreach($matches as $match){
            $tag=$match[1][0];$part=null;foreach([2,3,4] as $i)if(isset($match[$i])&&$match[$i][0]!==''){$part=$match[$i];break;}
            [$id,$offset]=$part;$type=$tag==='table'?'table':'post';
            // CF7 itself tries its hash identity before the numeric legacy ID.
            if($tag==='contact-form-7'&&function_exists('wpcf7_get_contact_form_by_hash')){
                $form=wpcf7_get_contact_form_by_hash($id);
                if($form&&$form->hash(strlen($id))===$id){
                    $contract['spans'][]=['path'=>$path,'offset'=>$offset,'length'=>strlen($id),'literal'=>$id,'type'=>'cf7-hash','id'=>$form->id(),'source_hash'=>$id];
                    $rest=substr_replace($rest,str_repeat(' ',strlen($match[0][0])),$match[0][1],strlen($match[0][0]));continue;
                }
            }
            if($type==='post'&&!ctype_digit($id)){$contract['reasons'][]='Non-numeric form/document alias needs a source identity contract';continue;}
            $contract['spans'][]=['path'=>$path,'offset'=>$offset,'length'=>strlen($id),'literal'=>$id,'type'=>$type,'id'=>$type==='post'?(int)$id:$id];
            $rest=substr_replace($rest,str_repeat(' ',strlen($match[0][0])),$match[0][1],strlen($match[0][0]));
        }
        if($format==='markdown'&&str_contains($text,'`')&&str_contains($text,'!['))$contract['reasons'][]='Code-bearing Markdown image syntax needs a source context contract';
        $patterns=$format==='markdown'?['~!\[[^\]\r\n]*\]\(([^\s)]+)\)~']:['~<img\b[^>]*?\bsrc="([^"\s]+)"[^>]*>~i',"~<img\\b[^>]*?\\bsrc='([^'\\s]+)'[^>]*>~i"];
        foreach($patterns as $pattern){
            preg_match_all($pattern,$rest,$images,PREG_SET_ORDER|PREG_OFFSET_CAPTURE);
            foreach($images as $image){
                [$url,$offset]=$image[1];$absolute=self::absolute($url);$ref=$absolute===null?null:self::image($absolute);
                if($ref)$contract['spans'][]=['path'=>$path,'offset'=>$offset,'length'=>strlen($url),'literal'=>$url]+$ref;
                elseif($absolute===null||self::local($absolute))$contract['reasons'][]='Unresolved source image: '.$url;
                else $contract['external_urls'][]=$url;
                if($format==='html'&&preg_match('~\bclass\s*=\s*(["\'])(.*?)\1~',$image[0][0],$classAttr,PREG_OFFSET_CAPTURE)&&preg_match_all('~(?:^|\s)wp-image-([1-9][0-9]*)(?=\s|$)~',$classAttr[2][0],$classes,PREG_OFFSET_CAPTURE))foreach($classes[1] as [$id,$position]){
                    if(!$ref||(int)$ref['id']!==(int)$id)$contract['reasons'][]='Image URL and attachment class disagree';
                    else $contract['spans'][]=['path'=>$path,'offset'=>$image[0][1]+$classAttr[2][1]+$position,'length'=>strlen($id),'literal'=>$id,'type'=>'post','id'=>(int)$id,'source_state'=>$ref['source_state']??'live'];
                }
                // Keep other HTML attributes visible to the unclassified-URL check.
                $mask=$format==='markdown'?$image[0]:$image[1];
                $rest=substr_replace($rest,str_repeat(' ',strlen($mask[0])),$mask[1],strlen($mask[0]));
            }
        }
        preg_match_all('~https?://[^\s<>"\')]+~',$rest,$urls,PREG_OFFSET_CAPTURE);
        foreach($urls[0] as [$url,$offset]){
            if(self::local($url))$contract['reasons'][]='Unclassified local URL context: '.$url;
            else $contract['external_urls'][]=$url;
            $rest=substr_replace($rest,str_repeat(' ',strlen($url)),$offset,strlen($url));
        }
        // These native member form commands have no object identity arguments.
        $rest=preg_replace('~\[(?:wpmem_form (?:login|register)|wpmem_profile)\]~','',$rest);
        $rest=preg_replace('~<!-- /?wp:(?:paragraph|heading|shortcode) -->~','',$rest);
        if(preg_match('~\[/?[A-Za-z_]|<!--\s*wp:|&#(?:0*91|x0*5b);|&lbrack;~i',$rest))$contract['reasons'][]='Unclassified content reference or execution syntax';
    }
    private static function local(string $url): bool {
        $a=parse_url($url);$b=parse_url(home_url());
        return strtolower($a['host']??'')===strtolower($b['host']??'')&&($a['port']??(($a['scheme']??'')==='https'?443:80))===($b['port']??(($b['scheme']??'')==='https'?443:80));
    }
    private static function absolute(string $url): ?string {
        if(preg_match('~^https?://~',$url))return $url;
        $base=parse_url(home_url());
        if(str_starts_with($url,'//'))return $base['scheme'].':'.$url;
        if(str_starts_with($url,'/'))return $base['scheme'].'://'.$base['host'].(isset($base['port'])?':'.$base['port']:'').$url;
        return null; // No guessed page-relative base, directory or filename.
    }
    private static function image(string $url): ?array {
        // Exact generated URLs from prior observed registration results, including sizes.
        $found=[];
        $entries=ConstructionOperations::read()['entries'];$deleted=[];
        foreach($entries as $e)if(($e['state']??'')==='registered'&&($e['contract']['endpoint']??'')==='wordpress.media-delete'&&!empty($e['result']['response']['deleted']))$deleted[(int)$e['contract']['target']['id']]=true;
        foreach($entries as $e){
            if(($e['state']??'')!=='registered')continue;
            $id=$e['result']['response']['id']??0;if(!$id)continue;
            foreach($e['result']['reference_values']??[] as $type=>$value)if(str_starts_with($type,'image-url:')&&$value===$url)$found[$type.':'.$id]=['type'=>$type,'id'=>$id,'source_state'=>isset($deleted[(int)$id])?'deleted':'live'];
        }
        // A full-size image already present at the initial-save boundary can also
        // be identified by core. Never strip filenames, dimensions or URL suffixes.
        if(!$found&&function_exists('attachment_url_to_postid')){
            $id=attachment_url_to_postid($url);
            if($id&&!isset($deleted[(int)$id])&&wp_get_attachment_url($id)===$url)$found['image-url:full:'.$id]=['type'=>'image-url:full','id'=>$id];
        }
        if(count($found)>1){
            // Core can expose the same full-size bytes as an uncropped size.
            $ids=array_unique(array_column($found,'id'));
            if(count($ids)===1&&isset($found['image-url:full:'.reset($ids)]))return $found['image-url:full:'.reset($ids)];
            return null;
        }
        return $found?reset($found):null;
    }
    public static function imageReference(string $url): ?array {$url=self::absolute($url);return $url===null?null:self::image($url);}
    public static function imageState(int $id): string {
        foreach(ConstructionOperations::read()['entries'] as $e)if(($e['state']??'')==='registered'&&($e['contract']['endpoint']??'')==='wordpress.media-delete'&&!empty($e['result']['response']['deleted'])&&(int)$e['contract']['target']['id']===$id)return 'deleted';
        return 'live';
    }
}
