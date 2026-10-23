<?php
declare(strict_types=1);
namespace Owr;
/** Native editor adapter. All content writes still pass through the material journal. */
final class NativeMaterialsEditor {
    public static function asset(int $id):string {
        $asset=(string)get_post_meta($id,'owr_material_id',true);
        if(!$asset)throw new \InvalidArgumentException('The referenced object is not S3 protected.');
        return $asset;
    }
    private static function portable(string $html):string {
        $doc=new \DOMDocument();$old=libxml_use_internal_errors(true);
        try{$doc->loadHTML('<?xml encoding="UTF-8"><div id="owr-root">'.$html.'</div>',LIBXML_HTML_NOIMPLIED|LIBXML_HTML_NODEFDTD|LIBXML_NONET);}finally{libxml_clear_errors();libxml_use_internal_errors($old);}
        $root=$doc->getElementById('owr-root');if(!$root)throw new \InvalidArgumentException('Invalid content');
        $allowed=['p','h1','h2','h3','h4','h5','h6','strong','b','em','i','s','del','br','a','ul','ol','li','blockquote','cite','figure','figcaption','img'];
        foreach(iterator_to_array($doc->getElementsByTagName('*')) as $el){
            if($el===$root)continue;
            $tag=strtolower($el->tagName);if(!in_array($tag,$allowed,true))throw new \InvalidArgumentException('Unsupported HTML: '.$tag);
            foreach(iterator_to_array($el->attributes) as $attr){
                $name=$attr->name;$value=$attr->value;
                if(in_array($name,['class','width','height','loading','decoding'],true)){$el->removeAttribute($name);continue;}
                if(($tag==='a'&&$name==='href')||($tag==='img'&&$name==='src')){
                    $id=$tag==='img'?attachment_url_to_postid($value):url_to_postid($value);
                    if(($id||str_starts_with($value,'#'))&&wp_parse_url($value,PHP_URL_FRAGMENT)!==null)throw new \InvalidArgumentException('Internal link fragments are not supported; remove the fragment before saving.');
                    if($id){$el->setAttribute($name,'asset:'.self::asset((int)$id));}
                    elseif(wp_parse_url($value,PHP_URL_HOST)===wp_parse_url(home_url(),PHP_URL_HOST)){throw new \InvalidArgumentException('Unresolved internal link');}
                    elseif($tag==='img'||!preg_match('~^(https?://|mailto:|tel:|#[a-zA-Z0-9_-]+$)~',$value)){throw new \InvalidArgumentException('Unsupported or unprotected URL');}
                }elseif(!(($tag==='img'&&$name==='alt')||($tag==='ol'&&$name==='start'&&ctype_digit($value)))){throw new \InvalidArgumentException('Unsupported attribute: '.$name);}
            }
            if($tag==='img'&&!$el->hasAttribute('src'))throw new \InvalidArgumentException('Image source required');
        }
        $out='';foreach($root->childNodes as $child){if($child instanceof \DOMComment)continue;$out.=$doc->saveHTML($child);}return trim($out);
    }
    public static function nodes(string $content):array {
        if(strlen($content)>2*1024*1024)throw new \InvalidArgumentException('Content size limit');
        $nodes=[];foreach(parse_blocks($content) as $block){
            if($block['blockName']===null&&trim($block['innerHTML'])==='')continue;
            $name=$block['blockName']??'core/freeform';
            if(!in_array($name,['core/paragraph','core/heading','core/list','core/quote','core/image','core/freeform'],true))throw new \InvalidArgumentException('Unsupported block: '.$name);
            $allowedAttrs=match($name){'core/heading'=>['level'],'core/image'=>['id','sizeSlug','linkDestination'],'core/list'=>['ordered','start'],'core/quote'=>[],default=>[]};
            foreach(array_keys($block['attrs']) as $key)if(!in_array($key,$allowedAttrs,true))throw new \InvalidArgumentException('Unsupported block setting: '.$key);
            if($name==='core/image'&&($block['attrs']['linkDestination']??'none')!=='none')throw new \InvalidArgumentException('Linked image blocks are not supported');
            // Render static serialized markup only; never run dynamic blocks or shortcodes.
            $html=preg_replace('/<!--.*?-->/s','',serialize_block($block));
            if(str_contains($html,'['))throw new \InvalidArgumentException('Shortcodes are not supported in protected content.');
            $attrs=$block['attrs'];unset($attrs['id']);$node=['type'=>'block','name'=>$name,'html'=>self::portable($html)];if($attrs)$node['attrs']=$attrs;$nodes[]=$node;
        }return $nodes;
    }
    private static function parent(\WP_REST_Request $request):array {
        $s=SiteMaterialsEditor::status();$current=hash('sha256',SiteMaterialsEditor::canonical($s['receipt']));
        if(!hash_equals($current,(string)$request->get_header('X-OWR-Parent')))throw new \RuntimeException('Stale editor. Reload before saving.');
        if(!$s['site'])throw new \RuntimeException('Explicit initial material enrollment required.');return $s;
    }
    public static function save(\WP_REST_Request $request,int $id,string $kind):array {
        if(!current_user_can('manage_options')||($id&&!current_user_can('edit_post',$id)))throw new \RuntimeException('Permission denied');
        $s=self::parent($request);$site=$s['site'];$params=$request->get_json_params()??[];
        $allowed=['id','title','content','status','slug','parent','excerpt','comment_status','ping_status','meta','categories','tags','featured_media','author','date','date_gmt','template','sticky','password','format'];
        foreach($params as $key=>$value){if(!in_array($key,$allowed,true))throw new \InvalidArgumentException('Unsupported field: '.$key);}
        // Reject unsupported state rather than silently discarding it.
        foreach(['excerpt','meta','tags','featured_media','template','sticky','password'] as $key){if(!empty($params[$key]))throw new \InvalidArgumentException('Unsupported field: '.$key);}
        if(!empty($params['categories'])&&$params['categories']!==[(int)get_option('default_category')])throw new \InvalidArgumentException('Custom categories not yet supported');
        foreach(['date','date_gmt'] as $key){if(!empty($params[$key]))throw new \InvalidArgumentException('Scheduled/custom dates are not yet supported');}
        if(isset($params['author'])&&(int)$params['author']!==get_current_user_id())throw new \InvalidArgumentException('Author reassignment not supported');
        if(!empty($params['format'])&&$params['format']!=='standard')throw new \InvalidArgumentException('Post format not supported');
        if(($params['comment_status']??'closed')!=='closed'||($params['ping_status']??'closed')!=='closed')throw new \InvalidArgumentException('Comments and pingbacks must remain closed');
        $post=$id?get_post($id):null;if($id&&(!$post||$post->post_type!==$kind))throw new \InvalidArgumentException('Wrong post');
        $asset=$post?(get_post_meta($id,'owr_material_id',true)?:'native-'.$id):'native-'.bin2hex(random_bytes(12));
        if($post&&!get_post_meta($id,'owr_material_id',true)&&in_array($asset,array_column($site['entries'],'id'),true))throw new \InvalidArgumentException('Reserved material ID already exists');
        if($post&&!get_post_meta($id,'owr_material_id',true)&&($post->post_status!=='auto-draft'||$post->post_content!==''))throw new \InvalidArgumentException('Existing content must be enrolled explicitly');
        $title=$params['title']??($post?$post->post_title:'');$content=$params['content']??($post?$post->post_content:'');$status=$params['status']??($post&&$post->post_status!=='auto-draft'?$post->post_status:'draft');
        if(!in_array($status,['draft','publish','private','pending'],true))throw new \InvalidArgumentException('Unsupported publication status');
        if(in_array($status,['publish','private'],true)&&!current_user_can($kind==='page'?'publish_pages':'publish_posts'))throw new \RuntimeException('Publication permission denied');
        $slug=$params['slug']??($post?$post->post_name:'');if($slug==='')$slug=$asset;
        $parent=(int)($params['parent']??($post?$post->post_parent:0));
        $row=['id'=>$asset,'kind'=>$kind,'title'=>$title,'slug'=>$slug,'parent'=>$parent?self::asset($parent):null,'nodes'=>self::nodes($content),'status'=>$status];
        $site['entries']=array_values(array_filter($site['entries'],fn($x)=>$x['id']!==$asset));$site['entries'][]=$row;
        $result=SiteMaterialsEditor::submit(['parent'=>$s['receipt'],'site'=>$site]);$result['asset']=$asset;return $result;
    }
    public static function upload(\WP_REST_Request $request):array {
        if(!current_user_can('manage_options')||!current_user_can('upload_files'))throw new \RuntimeException('Permission denied');
        $s=self::parent($request);$files=$request->get_file_params();$f=$files['file']??null;
        if(!$f||$f['error']!==UPLOAD_ERR_OK||$f['size']>4*1024*1024||!is_uploaded_file($f['tmp_name']))throw new \InvalidArgumentException('PNG/JPEG upload up to 4 MiB required');
        $raw=file_get_contents($f['tmp_name']);$info=getimagesizefromstring($raw);
        if(!$info||!in_array($info['mime'],['image/png','image/jpeg'],true)||$info[0]>10000||$info[1]>10000)throw new \InvalidArgumentException('Unsupported image');
        $asset='image-'.hash('sha256',$raw);$site=$s['site'];
        $site['entries']=array_values(array_filter($site['entries'],fn($x)=>$x['id']!==$asset));$site['entries'][]=['id'=>$asset,'kind'=>'image','mime'=>$info['mime'],'data'=>base64_encode($raw),'alt'=>''];
        $result=SiteMaterialsEditor::submit(['parent'=>$s['receipt'],'site'=>$site]);$result['asset']=$asset;return $result;
    }
    public static function dispatch($result,$server,\WP_REST_Request $request){
        if($result!==null)return $result;
        if(in_array($request->get_method(),['GET','HEAD','OPTIONS'],true))return $result;
        if(!preg_match('~^/wp/v2/(posts|pages|media)(?:/(\d+))?$~',$request->get_route(),$m))return $result;
        if(!current_user_can('manage_options'))return new \WP_Error('owr_native','Permission denied',['status'=>403]);
        if(!in_array($request->get_method(),['POST','PUT','PATCH'],true))return new \WP_Error('owr_native','Deletion not supported',['status'=>409]);
        try{$value=$m[1]==='media'?self::upload($request):self::save($request,(int)($m[2]??0),$m[1]==='pages'?'page':'post');$response=new \WP_REST_Response(['owr_pending'=>true]+$value,202);$response->header('Cache-Control','no-store');return $response;}
        catch(\Throwable $e){return new \WP_Error('owr_native',$e->getMessage(),['status'=>409]);}
    }

    public static function ajaxUpload():void {
        check_ajax_referer('media-form');
        try {
            $q=new \WP_REST_Request('POST','/wp/v2/media');$q->set_header('X-OWR-Parent',sanitize_text_field(wp_unslash($_POST['_owr_parent']??'')));
            $q->set_file_params(['file'=>$_FILES['async-upload']??null]);$result=self::upload($q);$asset=$result['asset'];$operation=$result['pending']['operation'];
            // Acknowledge queue acceptance, never an attachment before S3 commitment.
            wp_send_json_success(['owr_pending'=>true,'asset'=>$asset,'operation'=>$operation]);
        }catch(\Throwable $e){wp_send_json_error(['message'=>$e->getMessage()]);}
    }
    public static function boot():void {

        add_action('wp_ajax_upload-attachment',[self::class,'ajaxUpload'],0);
        add_action('admin_init',function(){global $pagenow;if($pagenow==='async-upload.php'&&($_SERVER['REQUEST_METHOD']??'GET')==='POST'&&($_REQUEST['action']??'')==='upload-attachment')self::ajaxUpload();});
        add_action('admin_enqueue_scripts',function(){
            if(!current_user_can('manage_options'))return;
            wp_enqueue_script('wp-api-fetch');wp_enqueue_script('wp-plupload');$s=SiteMaterialsEditor::status();
            wp_add_inline_script('wp-plupload','window.owrNative=window.owrNative||'.wp_json_encode(['parent'=>hash('sha256',SiteMaterialsEditor::canonical($s['receipt']))]).';'.file_get_contents(__DIR__.'/../assets/native-materials-upload.js'));
        });

        add_filter('get_default_comment_status',fn()=>'closed');
        add_filter('default_post_to_edit',function($post){$post->comment_status='closed';$post->ping_status='closed';return $post;});

        add_filter('rest_pre_dispatch',[self::class,'dispatch'],9,3);
        add_action('enqueue_block_editor_assets',function(){
            $s=SiteMaterialsEditor::status();
            wp_register_script('owr-native-editor',false,['wp-api-fetch','wp-data','wp-notices','wp-edit-post'],'0.2.0',true);wp_enqueue_script('owr-native-editor');wp_add_inline_script('owr-native-editor',file_get_contents(__DIR__.'/../assets/native-materials-editor.js'));
            wp_add_inline_script('owr-native-editor','window.owrNative='.wp_json_encode(['parent'=>hash('sha256',SiteMaterialsEditor::canonical($s['receipt']))]).';','before');
        });
        add_action('admin_notices',function(){if(!current_user_can('manage_options'))return;echo '<div class="notice notice-info"><p>S3先行保存：標準ブロックエディターの段落・見出し・リスト・引用・画像に対応。保存失敗時は公開内容を保持します。<a href="'.esc_url(admin_url('admin.php?page=owr-site-materials')).'">保存状態・同じ要求の再開</a>。予約投稿・フォーム・独自ブロック・分類等は未対応です。</p></div>';});
    }
}
