<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** First-stage native registration. No SQL placement, source IDs, or plugin initialization. */
final class NativeReconstruction {
    private array $posts=[],$meta=[],$map=[],$terms=[],$menus=[],$urls=[],$report=[],$dependencies=[];
    private array $taxonomyIndex=[],$assignments=[];
    private string $origin='';
    private const JOURNAL='ozeki_resilience_native_reconstruction';
    private static function checked(mixed $value): mixed {
        if(is_wp_error($value))throw new \RuntimeException($value->get_error_message());
        return $value;
    }
    private function hold(int $id,string $reason): void {$this->report[$id]=$reason;}
    private function reference(int $id,int $owner): int {
        if(!$id)return 0;
        $this->dependencies[$owner][$id]=true;
        if(!isset($this->map[$id])||isset($this->report[$id]))throw new \RuntimeException('Required reference unavailable: '.$id);
        return $this->map[$id];
    }
    private function url(string $url,int $owner): string {
        $parts=explode('#',html_entity_decode($url,ENT_QUOTES|ENT_HTML5,'UTF-8'),2);
        if(isset($this->urls[$parts[0]])){
            [$id,$replacement]=$this->urls[$parts[0]];$this->reference($id,$owner);
            return $replacement.(isset($parts[1])?'#'.$parts[1]:'');
        }
        $source=wp_parse_url($this->origin);$parsed=wp_parse_url($parts[0]);
        if($parts[0]!==''&&$parts[0][0]==='/'&&!str_starts_with($parts[0],'//'))return $this->url(rtrim($this->origin,'/').$url,$owner);
        if(($parsed['host']??null)===($source['host']??null)&&($parsed['port']??null)===($source['port']??null))throw new \RuntimeException('Unresolved source URL: '.$parts[0]);
        if($url!==''&&esc_url_raw($url)!==$url)throw new \RuntimeException('Unsupported URL');
        return $url;
    }
    private function html(string $html,int $owner): string {
        // KSES inserts a space before a void tag's closing slash. That is not a
        // removed value or execution instruction; compare this syntax uniformly.
        $normalise=static fn($s)=>implode('',array_map(static fn($part)=>str_starts_with($part,'<')?preg_replace('~\s*/>$~',' />',$part):$part,wp_html_split($s)));
        if($normalise(wp_kses_post($html))!==$normalise($html))throw new \RuntimeException('HTML needs review; original is unchanged');
        $processor=new \WP_HTML_Tag_Processor($html);
        while($processor->next_tag()){
            foreach(['href','src'] as $attr){$url=$processor->get_attribute($attr);if(is_string($url))$processor->set_attribute($attr,$this->url($url,$owner));}
            if($processor->get_attribute('srcset')!==null)throw new \RuntimeException('Stored srcset needs an explicit image reference mapping');
            $class=$processor->get_attribute('class');
            if(is_string($class))$processor->set_attribute('class',preg_replace_callback('/\bwp-image-([1-9][0-9]*)\b/',fn($m)=>'wp-image-'.$this->reference((int)$m[1],$owner),$class));
        }
        return $processor->get_updated_html();
    }
    private function blocks(array $blocks,int $owner): array {
        $allowed=['core/paragraph','core/heading','core/list','core/list-item','core/quote','core/image','core/table','core/code','core/preformatted','core/separator','core/navigation','core/navigation-link','core/navigation-submenu'];
        foreach($blocks as &$block){
            if($block['blockName']!==null&&!in_array($block['blockName'],$allowed,true))throw new \RuntimeException('Block outside native first-stage scope: '.$block['blockName']);
            foreach($block['attrs'] as $key=>$value){
                $valid=match($key){
                    'id'=>in_array($block['blockName'],['core/image','core/navigation-link','core/navigation-submenu'],true)&&is_int($value)&&$value>0,
                    'ref'=>$block['blockName']==='core/navigation'&&is_int($value)&&($this->posts[$value]['post_type']??'')==='wp_navigation',
                    'label'=>in_array($block['blockName'],['core/navigation-link','core/navigation-submenu'],true)&&is_string($value)&&wp_strip_all_tags($value)===$value,
                    'type'=>in_array($value,['page','post'],true),
                    'kind'=>$value==='post-type',
                    'url'=>is_string($value),
                    'overlayMenu'=>in_array($value,['never','mobile','always'],true),
                    'sizeSlug'=>is_string($value)&&in_array($value,['thumbnail','medium','large','full'],true),
                    'linkDestination'=>in_array($value,['none','media','attachment'],true),
                    'align'=>in_array($value,['left','center','right','wide','full'],true),
                    'level'=>is_int($value)&&$value>=1&&$value<=6,
                    'ordered','reversed','hasFixedLayout'=>is_bool($value),
                    'start'=>is_int($value)&&$value>=0,
                    'className'=>is_string($value)&&(bool)preg_match('/^[A-Za-z0-9_ -]*$/D',$value),
                    default=>false,
                };
                if(!$valid)throw new \RuntimeException('Block attribute needs review: '.$key);
                if(in_array($key,['id','ref'],true))$block['attrs'][$key]=$this->reference((int)$value,$owner);
                if($key==='url')$block['attrs'][$key]=$this->url($value,$owner);
            }
            $block['innerHTML']=$this->html($block['innerHTML'],$owner);
            foreach($block['innerContent'] as &$part)if(is_string($part))$part=$this->html($part,$owner);unset($part);
            $block['innerBlocks']=$this->blocks($block['innerBlocks'],$owner);
        }unset($block);return $blocks;
    }
    private function content(string $body,int $owner): string {
        if(preg_match('/\[\/?[a-zA-Z_][^\]]*\]/',html_entity_decode($body,ENT_QUOTES|ENT_HTML5,'UTF-8')))throw new \RuntimeException('Shortcode requires its own registration stage');
        return serialize_blocks($this->blocks(parse_blocks($body),$owner));
    }
    private function journal(string $state,array $extra=[]): void {
        $value=['state'=>$state,'posts'=>$this->map,'terms'=>$this->terms,'menus'=>$this->menus,'held'=>$this->report]+$extra;
        update_option(self::JOURNAL,$value,false);
        if(get_option(self::JOURNAL)!==$value)throw new \RuntimeException('Cannot persist registration progress');
    }
    private function created(int $old,int $new): void {
        $this->map[$old]=$new;
        if(!add_option(self::JOURNAL.'_item_'.$old,['destination'=>$new],'',false))throw new \RuntimeException('Cannot record created item');
    }
    private function sourceUrls(array $manifest,array $data,bool $planning=false): void {
        $this->urls=[];
        foreach($this->map as $old=>$new){
            if($this->posts[$old]['post_type']==='wp_navigation')continue;
            $post=$this->posts[$old];$url=$planning?home_url('/?p='.$new):($post['post_type']==='attachment'?wp_get_attachment_url($new):get_permalink($new));
            foreach(array_filter([$post['guid']??'',rtrim($this->origin,'/').'/?p='.$old,rtrim($this->origin,'/').'/?page_id='.$old]) as $source)$this->urls[$source]=[$old,$url];
            if($post['post_type']==='attachment'){
                $path=$this->meta[$old]['_wp_attached_file']??'';
                $this->urls[rtrim($manifest['source_upload_url'],'/').'/'.$path]=[$old,$url];
                $metadata=$this->imageMetadata($old);
                foreach($metadata['sizes']??[] as $size=>$definition){
                    $relative=(dirname($path)==='.'?'':dirname($path).'/').$definition['file'];
                    $this->urls[rtrim($manifest['source_upload_url'],'/').'/'.$relative]=[$old,$planning?$url:wp_get_attachment_image_url($new,$size)];
                }
            }else{
                $slug=$post['post_name'];$parent=(int)$post['post_parent'];$seen=[$old=>true];
                while($parent&&isset($this->posts[$parent])){if(isset($seen[$parent]))throw new \RuntimeException('Source parent cycle');$seen[$parent]=true;$slug=$this->posts[$parent]['post_name'].'/'.$slug;$parent=(int)$this->posts[$parent]['post_parent'];}
                if(($data['options']['permalink_structure']??'')==='/%postname%/'||$post['post_type']==='page')$this->urls[rtrim($this->origin,'/').'/'.$slug.'/']=[$old,$url];
            }
        }
    }
    private function imageMetadata(int $id): array {
        $value=$this->meta[$id]['_wp_attachment_metadata']??'';
        $value=is_string($value)&&is_serialized($value)?unserialize($value,['allowed_classes'=>false]):$value;
        return is_array($value)?$value:[];
    }
    public function run(array $manifest,array $files,array $destination): array {
        if(!defined('WP_CLI')||!WP_CLI||($destination['isolated']??false)!==true||!current_user_can('manage_options'))throw new \RuntimeException('Native first-stage registration requires an explicitly isolated CLI destination');
        if(!empty((new Plugin())->config()['protect']))throw new \RuntimeException('Destination protection must be disabled');
        $this->origin=rtrim($manifest['source_url'],'/');
        if($this->origin===rtrim(home_url(),'/'))throw new \RuntimeException('Source and destination must differ');
        $data=json_decode($files['content.json'],true,512,JSON_THROW_ON_ERROR);$authors=$destination['author_map']??[];
        if(($data['update_contract']??'')!==UpdateContract::SCHEMA||!empty($manifest['legacy_incomplete_article_conditions']))throw new \RuntimeException('Complete current publication conditions are required for native registration');
        foreach($data['tables']['term_taxonomy'] as $t)$this->taxonomyIndex[(int)$t['term_taxonomy_id']]=$t['taxonomy'].':'.$t['term_id'];
        foreach($data['tables']['term_relationships'] as $r){$key=$this->taxonomyIndex[(int)$r['term_taxonomy_id']]??throw new \RuntimeException('Missing taxonomy definition');$this->assignments[(int)$r['object_id']][]=$key;}
        foreach($data['tables']['postmeta'] as $r)$this->meta[(int)$r['post_id']][$r['meta_key']]=$r['meta_value'];
        $excluded=[];
        foreach($data['tables']['posts'] as $p){
            $id=(int)$p['ID'];$this->posts[$id]=$p;
            if(!in_array($p['post_type'],['post','page','attachment','nav_menu_item','wp_navigation'],true)){$excluded[$id]='Outside native first-stage scope';continue;}
            if(!in_array($p['post_status'],$p['post_type']==='attachment'?['inherit','publish','private']:['publish','private'],true)){$excluded[$id]='Not a formal current publication';continue;}
            if($p['post_type']==='nav_menu_item')continue;
            if(isset($data['membership'])||in_array((string)($this->meta[$id]['_wpmem_block']??''),['1','2'],true)){$this->hold($id,'Membership conditions require the member registration stage');continue;}
            $author=(int)($authors[(int)$p['post_author']]??0);
            if(!$author||!get_userdata($author)){$this->hold($id,'Explicit destination author mapping required');continue;}
            if($p['post_type']==='attachment'){
                $path='uploads/'.($this->meta[$id]['_wp_attached_file']??'');
                SiteSnapshot::safePath($path);
                if(!str_starts_with($p['post_mime_type'],'image/')||!isset($files[$path])||($data['media_access'][$path]['state']??'unknown')!=='public'){$this->hold($id,'Public image original and explicit file viewing condition required');continue;}
                if(!@getimagesizefromstring($files[$path])){$this->hold($id,'Invalid image original');continue;}
                foreach($this->imageMetadata($id)['sizes']??[] as $definition){$derived=dirname($path).'/'.$definition['file'];SiteSnapshot::safePath($derived);if(($data['media_access'][$derived]['state']??'unknown')!=='public')$this->hold($id,'Image variants have unresolved viewing conditions');}
            }
            $this->map[$id]=$id; // Validation only; never passed as a destination ID.
        }
        if(!add_option(self::JOURNAL,['state'=>'planning'],'',false))throw new \RuntimeException('Previous registration exists; review it before another run');
        $start=microtime(true);$timing=[];
        try {
            // Validate source references before any content is made public.
            $this->sourceUrls($manifest,$data,true);
            foreach($this->map as $id=>$_){
                try {
                    $p=$this->posts[$id];if((int)$p['post_parent'])$this->reference((int)$p['post_parent'],$id);
                    $this->html((string)$p['post_title'],$id);
                    if(!empty($this->meta[$id]['_thumbnail_id']))$this->reference((int)$this->meta[$id]['_thumbnail_id'],$id);
                    foreach(['post_content','post_excerpt'] as $field)$this->content((string)$p[$field],$id);
                }catch(\RuntimeException $e){$this->hold($id,$e->getMessage());}
            }
            // Dependants of a held item must not become publicly usable with a broken reference.
            do{$changed=false;foreach($this->dependencies as $id=>$deps)if(!isset($this->report[$id]))foreach($deps as $dep=>$_)if(isset($this->report[$dep])){$this->hold($id,'Required item held: '.$dep);$changed=true;break;}}while($changed);
            $selected=array_keys(array_diff_key($this->map,$this->report));$this->map=[];$this->journal('registering',['excluded'=>$excluded]);
            foreach(['page_on_front','page_for_posts'] as $key){$old=(int)($data['options'][$key]??0);if($old&&!in_array($old,$selected,true))throw new \RuntimeException('Reading setting references an unavailable page: '.$key);}
            if(isset($data['options']['show_on_front'])&&!in_array($data['options']['show_on_front'],['posts','page'],true))throw new \RuntimeException('Invalid reading setting');
            require_once ABSPATH.'wp-admin/includes/file.php';require_once ABSPATH.'wp-admin/includes/media.php';require_once ABSPATH.'wp-admin/includes/image.php';
            $imageStart=microtime(true);
            foreach($selected as $id){$p=$this->posts[$id];if($p['post_type']!=='attachment')continue;
                $relative=$this->meta[$id]['_wp_attached_file'];$tmp=wp_tempnam(basename($relative));
                if(!$tmp||file_put_contents($tmp,$files['uploads/'.$relative])!==strlen($files['uploads/'.$relative]))throw new \RuntimeException('Cannot stage image');
                try{$new=self::checked(media_handle_sideload(['name'=>basename($relative),'tmp_name'=>$tmp],0,null,wp_slash(['post_title'=>$p['post_title'],'post_content'=>$p['post_content'],'post_excerpt'=>$p['post_excerpt'],'post_author'=>(int)$authors[(int)$p['post_author']]])));}
                finally{if(is_file($tmp))unlink($tmp);}
                $this->created($id,(int)$new);
                update_post_meta($new,'_wp_attachment_image_alt',wp_slash($this->meta[$id]['_wp_attachment_image_alt']??''));
            }$timing['images']=microtime(true)-$imageStart;
            $registrationStart=microtime(true);
            foreach($selected as $id){$p=$this->posts[$id];if($p['post_type']==='attachment')continue;
                $this->created($id,(int)self::checked(wp_insert_post(wp_slash(['post_type'=>$p['post_type'],'post_status'=>'draft','post_title'=>$p['post_title'],'post_name'=>$p['post_name'],'post_date'=>$p['post_date'],'post_date_gmt'=>$p['post_date_gmt'],'post_author'=>(int)$authors[(int)$p['post_author']],'post_password'=>$p['post_password'],'comment_status'=>$p['comment_status'],'ping_status'=>$p['ping_status'],'menu_order'=>(int)$p['menu_order']]),true)));
            }$timing['registration']=microtime(true)-$registrationStart;
            $relationsStart=microtime(true);
            $this->registerTerms($data);
            // Set parent relations before asking WordPress for destination permalinks.
            foreach($this->map as $id=>$new){$parent=(int)$this->posts[$id]['post_parent'];if($parent)self::checked(wp_update_post(['ID'=>$new,'post_parent'=>$this->reference($parent,$id)],true));}
            $this->sourceUrls($manifest,$data);
            $finalValues=[];
            foreach($this->map as $id=>$new){
                $p=$this->posts[$id];$body=$this->content($p['post_content'],$id);$excerpt=$this->content($p['post_excerpt'],$id);
                $finalValues[$id]=['ID'=>$new,'post_content'=>$body,'post_excerpt'=>$excerpt,'post_status'=>$p['post_status'],'post_password'=>$p['post_password']];
                if(!empty($this->meta[$id]['_thumbnail_id'])&&!set_post_thumbnail($new,$this->reference((int)$this->meta[$id]['_thumbnail_id'],$id)))throw new \RuntimeException('Cannot set featured image');
                if(in_array($p['post_type'],['post','page'],true))foreach(['category','post_tag'] as $tax){$assigned=[];foreach($this->assignments[$id]??[] as $key)if(str_starts_with($key,$tax.':'))$assigned[]=$this->terms[$key];self::checked(wp_set_object_terms($new,$assigned,$tax));}
            }
            $this->registerMenus($data);
            $timing['relations']=microtime(true)-$relationsStart;
            // Relations are ready. Save final content and publication together,
            // avoiding an extra complete save/hook cycle per article.
            foreach($finalValues as $values)self::checked(wp_update_post(wp_slash($values),true));
            // Read through WordPress's normal API; differences are failures, not
            // an invitation to patch the generated rows or caches afterwards.
            foreach($this->map as $id=>$new){
                $actual=get_post($new);$source=$this->posts[$id];
                if(!$actual||$actual->post_title!==$source['post_title']||$actual->post_content!==$this->content($source['post_content'],$id)||$actual->post_excerpt!==$this->content($source['post_excerpt'],$id)||(int)$actual->post_parent!==((int)$source['post_parent']?$this->map[(int)$source['post_parent']]:0))throw new \RuntimeException('Normal registration readback differs: '.$id);
                if($actual->post_status!==$source['post_status']||$actual->post_password!==$source['post_password'])throw new \RuntimeException('Publication conditions differ after normal registration: '.$id);
            }
            foreach(['page_on_front','page_for_posts'] as $key){$old=(int)($data['options'][$key]??0);if($old&&!isset($this->map[$old]))throw new \RuntimeException('Reading setting references an unavailable page');if(isset($data['options'][$key]))update_option($key,$old?$this->map[$old]:0);}
            if(isset($data['options']['show_on_front']))update_option('show_on_front',$data['options']['show_on_front']);
            $timing['total']=microtime(true)-$start;
            $result=['posts'=>$this->map,'terms'=>$this->terms,'menus'=>$this->menus,'held'=>$this->report,'excluded'=>$excluded,'through'=>$manifest['through'],'timing'=>$timing,'complete'=>!$this->report];
            $this->journal('completed',$result);return $result;
        }catch(\Throwable $e){$this->journal('failed',['error'=>$e->getMessage()]);throw $e;}
    }
    private function registerTerms(array $data): void {
        $definitions=[];$prepared=[];foreach($data['tables']['terms'] as $t)$definitions[(int)$t['term_id']]=$t;
        foreach($data['tables']['term_taxonomy'] as $t){if(!in_array($t['taxonomy'],['category','post_tag'],true))continue;$d=$definitions[(int)$t['term_id']]??throw new \RuntimeException('Missing term');
            $existing=term_exists($d['slug'],$t['taxonomy']);
            if($existing){$term=get_term((int)$existing['term_id'],$t['taxonomy']);if($term->name!==$d['name']||$term->description!==$t['description'])throw new \RuntimeException('Prepared term conflicts with source definition');$id=(int)$term->term_id;$prepared[$t['taxonomy'].':'.$t['term_id']]=(int)$term->parent;}
            else $id=(int)self::checked(wp_insert_term($d['name'],$t['taxonomy'],['slug'=>$d['slug'],'description'=>$t['description']]))['term_id'];
            $this->terms[$t['taxonomy'].':'.$t['term_id']]=$id;
        }
        foreach($data['tables']['term_taxonomy'] as $t)if($t['taxonomy']==='category'){ $key='category:'.$t['term_id'];$parent=(int)$t['parent']?($this->terms['category:'.$t['parent']]??throw new \RuntimeException('Missing category parent')):0;if(isset($prepared[$key])){if($prepared[$key]!==$parent)throw new \RuntimeException('Prepared category parent conflicts with source');}elseif($parent)self::checked(wp_update_term($this->terms[$key],'category',['parent'=>$parent]));}
    }
    private function registerMenus(array $data): void {
        $names=[];foreach($data['tables']['terms'] as $t)$names[(int)$t['term_id']]=$t['name'];
        foreach($data['tables']['term_taxonomy'] as $t){if($t['taxonomy']!=='nav_menu')continue;
            $old=(int)$t['term_id'];$new=(int)self::checked(wp_create_nav_menu($names[$old]));$this->menus[$old]=$new;$items=[];$pending=[];
            foreach($data['tables']['term_relationships'] as $r)if((int)$r['term_taxonomy_id']===(int)$t['term_taxonomy_id'])$pending[(int)$r['object_id']]=true;
            while($pending){$progress=false;foreach(array_keys($pending) as $id){$p=$this->posts[$id];$m=$this->meta[$id];$parent=(int)($m['_menu_item_menu_item_parent']??0);if($parent&&!isset($items[$parent]))continue;
                $kind=$m['_menu_item_type']??'';$object=$m['_menu_item_object']??'';$objectId=(int)($m['_menu_item_object_id']??0);
                if($kind==='post_type'&&isset($this->map[$objectId]))$objectId=$this->map[$objectId];
                elseif($kind==='taxonomy'&&isset($this->terms[$object.':'.$objectId]))$objectId=$this->terms[$object.':'.$objectId];
                elseif($kind!=='custom')throw new \RuntimeException('Menu reference unavailable: '.$id);
                $classes=$m['_menu_item_classes']??[];if(is_string($classes)&&is_serialized($classes))$classes=unserialize($classes,['allowed_classes'=>false]);if(!is_array($classes))throw new \RuntimeException('Invalid menu classes');
                $items[$id]=(int)self::checked(wp_update_nav_menu_item($new,0,['menu-item-title'=>$p['post_title'],'menu-item-description'=>$p['post_content'],'menu-item-attr-title'=>$p['post_excerpt'],'menu-item-target'=>$m['_menu_item_target']??'','menu-item-classes'=>implode(' ',array_map('sanitize_html_class',$classes)),'menu-item-xfn'=>$m['_menu_item_xfn']??'','menu-item-type'=>$kind,'menu-item-object'=>$object,'menu-item-object-id'=>$objectId,'menu-item-parent-id'=>$parent?$items[$parent]:0,'menu-item-position'=>(int)$p['menu_order'],'menu-item-url'=>$kind==='custom'?$this->url((string)($m['_menu_item_url']??''),$id):'','menu-item-status'=>'publish']));unset($pending[$id]);$progress=true;
            }if(!$progress)throw new \RuntimeException('Menu parent cycle or missing parent');}
        }
    }
}
