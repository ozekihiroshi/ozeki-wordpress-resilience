<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Select materials only. The destination plugin is used through its ordinary forms. */
final class MarkdownReconstruction {
    public static function plan(array $manifest,array $files): array {
        $data=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);
        if(($data['update_contract']??'')!==UpdateContract::SCHEMA||!empty($manifest['legacy_incomplete_article_conditions']))throw new \RuntimeException('Complete publication conditions required');
        $out=['schema'=>'owr-normal-markdown-registration-1','source_url'=>$manifest['source_url'],'through'=>$manifest['through'],'documents'=>[],'images'=>[],'pages'=>[],'held'=>[],'excluded'=>[]];
        $out['timezone']=['name'=>(string)($data['options']['timezone_string']??''),'offset'=>(float)($data['options']['gmt_offset']??0)];
        $meta=[];foreach($data['tables']['postmeta'] as $m)$meta[(int)$m['post_id']][$m['meta_key']]=$m['meta_value'];
        foreach($data['tables']['posts'] as $p){
            $id=(int)$p['ID'];$type=$p['post_type'];$m=$meta[$id]??[];
            if($type==='attachment'){
                $relative=(string)($m['_wp_attached_file']??'');$path='uploads/'.$relative;SiteSnapshot::safePath($path);
                if(!str_starts_with($p['post_mime_type'],'image/')||!isset($files[$path])||($data['media_access'][$path]['state']??'')!=='public')continue;
                $metadata=$m['_wp_attachment_metadata']??'';$metadata=is_serialized($metadata)?unserialize($metadata,['allowed_classes'=>false]):[];
                $aliases=[rtrim($manifest['source_upload_url'],'/').'/'.$relative];$public=true;
                foreach($metadata['sizes']??[] as $size){$derived=dirname($path).'/'.$size['file'];if(($data['media_access'][$derived]['state']??'')!=='public')$public=false;}
                if(!$public)continue;
                // Only the original path is promised here, not silently substituting a differently sized derivative.
                $out['images'][]=['origin_id'=>$id,'urls'=>$aliases,'filename'=>basename($relative),'mime'=>$p['post_mime_type'],'body_base64'=>base64_encode($files[$path]),'sha256'=>hash('sha256',$files[$path]),'title'=>$p['post_title'],'alt'=>(string)($m['_wp_attachment_image_alt']??'')];continue;
            }
            $embedding=in_array($type,['page','post'],true)&&str_contains($p['post_content'],'[ozeki_markdown_document');
            if($type!=='ozmd_document'&&!$embedding)continue;
            if(!in_array($p['post_status'],['publish','private'],true)){$out['excluded'][(string)$id]='Not a formal current publication';continue;}
            if(isset($data['membership'])||in_array((string)($m['_wpmem_block']??''),['1','2'],true)){$out['held'][(string)$id]='Membership conditions require the member registration stage';continue;}
            if((int)$p['post_parent']){$out['held'][(string)$id]='Parent registration must be connected in a later combined stage';continue;}
            $item=['origin_id'=>$id,'title'=>$p['post_title'],'slug'=>$p['post_name'],'status'=>$p['post_status'],'password'=>$p['post_password'],'excerpt'=>$p['post_excerpt'],'date'=>$p['post_date'],'date_gmt'=>$p['post_date_gmt'],'author_origin'=>(int)$p['post_author'],'comment_status'=>$p['comment_status'],'ping_status'=>$p['ping_status'],'menu_order'=>(int)$p['menu_order']];
            if($type==='ozmd_document'){
                if($p['post_excerpt']!==''||(int)$p['menu_order']!==0){$out['held'][(string)$id]='Saved fields have no corresponding normal Markdown editor controls';continue;}
                $raw=$files['markdown/'.$id.'.md']??($m['_ozmd_source']??null);
                if(!is_string($raw)||isset($m['_ozmd_source'])&&$raw!==$m['_ozmd_source']){$out['held'][(string)$id]='Missing or conflicting Markdown original';continue;}
                $filename=(string)($m['_ozmd_original_filename']??'');
                if($filename===''){$out['held'][(string)$id]='Original filename is missing; choose an import filename explicitly';continue;}
                $out['documents'][]=$item+['filename'=>$filename,'source_base64'=>base64_encode($raw),'source_sha256'=>hash('sha256',$raw)];
            }else{
                $safe=wp_kses_post($p['post_content'])===$p['post_content'];
                foreach(parse_blocks($p['post_content']) as $block)if($block['attrs']||$block['innerBlocks']||!in_array($block['blockName'],[null,'core/paragraph','core/heading','core/shortcode'],true))$safe=false;
                $rest=preg_replace('~\[ozeki_markdown_document\s+id=["\']?[1-9][0-9]*["\']?\s*/?\]~','',$p['post_content']);
                if(!$safe||preg_match('~\[/?[A-Za-z_][^\]]*\]~',html_entity_decode($rest,ENT_QUOTES|ENT_HTML5,'UTF-8'))){$out['held'][(string)$id]='Embedding page contains unsupported instructions';continue;}
                $out['pages'][]=$item+['type'=>$type,'content'=>$p['post_content']];
            }
        }
        return $out;
    }
}
