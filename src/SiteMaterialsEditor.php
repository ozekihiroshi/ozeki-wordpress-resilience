<?php
declare(strict_types=1);
namespace Owr;
/** Explicit lab enrollment only. No automatic takeover of an existing site. */
final class SiteMaterialsEditor {
    private static string $dir;
    private static bool $applying=false;
    public static function canonical($v):string {
        $sort=function($x)use(&$sort){if(!is_array($x)){return $x;}if(!array_is_list($x)){ksort($x,SORT_STRING);}return array_map($sort,$x);};
        return json_encode($sort($v),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_LINE_TERMINATORS|JSON_THROW_ON_ERROR)."\n";
    }
    private static function state():array {wp_cache_delete('owr_site_editor','options');return get_option('owr_site_editor',[]);}
    private static function locked(\Closure $fn){global $wpdb;if((int)$wpdb->get_var("SELECT GET_LOCK('owr_site_materials_editor',2)")!==1){throw new \RuntimeException('Busy');}try{return $fn();}finally{$wpdb->query("SELECT RELEASE_LOCK('owr_site_materials_editor')");}}
    private static function enqueueFile(array $pending):void {
        $path=self::$dir.'/requests/'.$pending['operation'].'-'.$pending['attempt'].'.json';$raw=self::canonical($pending);
        if(is_file($path)){if(file_get_contents($path)!==$raw){throw new \RuntimeException('Queue identity conflict');}return;}
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Local worker queue protocol; no installation or remote filesystem writes.
        $tmp=$path.'.tmp-'.bin2hex(random_bytes(8));$f=fopen($tmp,'xb');if(!$f){throw new \RuntimeException('Queue unavailable');}
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod,WordPress.WP.AlternativeFunctions.file_system_operations_fclose,WordPress.WP.AlternativeFunctions.file_system_operations_fwrite,WordPress.WP.AlternativeFunctions.rename_rename -- Local worker queue protocol; no installation or remote filesystem writes.
        try{chmod($tmp,0600);if(fwrite($f,$raw)!==strlen($raw)||!fflush($f)){throw new \RuntimeException('Queue write failed');}if(function_exists('fsync')){fsync($f);}}finally{fclose($f);}if(!rename($tmp,$path)){throw new \RuntimeException('Queue publish failed');}
    }
    private static function report(array $pending):array {
        $path=self::$dir.'/reports/'.$pending['operation'].'.json';if(!is_file($path)){return ['state'=>'queued'];}
        $v=json_decode(file_get_contents($path),true,64,JSON_THROW_ON_ERROR);
        if(($v['operation']??null)!==$pending['operation']||($v['attempt']??null)!==$pending['attempt']||($v['request_sha256']??null)!==$pending['request_sha256']){return ['state'=>'queued'];}
        return $v;
    }
    public static function status():array {
        $s=self::state();$p=$s['pending']??null;$r=$p?self::report($p):['state'=>'ready'];
        return ['site'=>$p['site']??($s['site']??null),'receipt'=>$s['receipt']??null,'pending'=>$p?['operation'=>$p['operation'],'attempt'=>$p['attempt']]:null,'state'=>$r['state'],'reason'=>$r['reason']??null];
    }
    public static function submit(array $input):array {return self::locked(function()use($input){
        $s=self::state();if(!isset($input['site'])||!array_key_exists('parent',$input)){throw new \InvalidArgumentException('Invalid request');}
        if(self::canonical($input['parent'])!==self::canonical($s['receipt']??null)){throw new \RuntimeException('Stale generation');}
        $site=$input['site'];if(($site['schema']??null)!=='owr-site-materials-v1'||!is_array($site['entries']??null)||count($site['entries'])>1000){throw new \InvalidArgumentException('Material schema');}
        $hash=hash('sha256',self::canonical(['parent'=>$input['parent'],'site'=>$site]));
        if(isset($s['pending'])){if($s['pending']['request_sha256']!==$hash){throw new \RuntimeException('Different pending save');}self::enqueueFile($s['pending']);return self::status();}
        $s['pending']=['operation'=>'editor-'.bin2hex(random_bytes(16)),'attempt'=>1,'parent'=>$input['parent'],'site'=>$site,'request_sha256'=>$hash];update_option('owr_site_editor',$s,false);self::enqueueFile($s['pending']);return self::status();
    });}
    public static function resume():array {return self::locked(function(){
        $s=self::state();if(!isset($s['pending'])){return self::status();}$r=self::report($s['pending']);
        if($r['state']==='failed'){$s['pending']['attempt']++;update_option('owr_site_editor',$s,false);}
        elseif($r['state']==='blocked'){throw new \RuntimeException('Unknown storage outcome; operator reconciliation required');}
        self::enqueueFile($s['pending']);return self::status();
    });}
    public static function apply():array {return self::locked(function(){
        $s=self::state();if(!isset($s['pending'])){return self::status();}$p=$s['pending'];$r=self::report($p);
        if($r['state']!=='stored'){throw new \RuntimeException('S3 save not confirmed');}$received=$r['received'];
        $wanted=$p['site'];usort($wanted['entries'],fn($a,$b)=>strcmp($a['id'],$b['id']));
        if(self::canonical($received['site']??null)!==self::canonical($wanted)||self::canonical($received['parent']??null)!==self::canonical($p['parent'])){throw new \RuntimeException('Stored material mismatch');}
        require_once __DIR__.'/SiteMaterialsProjection.php';self::$applying=true;
        try{$result=\owr_site_materials_apply($received,true,true);}finally{self::$applying=false;}
        // If interrupted here, the projection replays the same receipt without duplicate rows.
        update_option('owr_site_editor',['site'=>$received['site'],'receipt'=>$received['receipt'],'last_operation'=>$p['operation'],'result'=>$result],false);return self::status();
    });}
    public static function boot(string $dir):void {
        add_action('admin_enqueue_scripts',[self::class,'enqueue']);
        if(getenv('OWR_RBR_DISPOSABLE')!=='1'||!is_dir($dir.'/requests')||!is_dir($dir.'/reports')){throw new \RuntimeException('Explicit dedicated enrollment required');}self::$dir=$dir;
        require_once __DIR__.'/NativeMaterialsEditor.php';NativeMaterialsEditor::boot();
        require_once __DIR__.'/SiteReconstructionAdmin.php';SiteReconstructionAdmin::boot($dir);
        add_action('rest_api_init',function(){foreach(['state'=>'GET','save'=>'POST','resume'=>'POST','apply'=>'POST'] as $action=>$method){register_rest_route('owr-materials/v1','/'.$action,['methods'=>$method,'permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function($request)use($action){
            try{if(strlen($request->get_body())>16*1024*1024){throw new \InvalidArgumentException('Input bound');}
                $value=match($action){'state'=>self::status(),'save'=>self::submit($request->get_json_params()??[]),'resume'=>self::resume(),'apply'=>self::apply()};$response=new \WP_REST_Response($value);$response->header('Cache-Control','no-store');return $response;
            }catch(\Throwable $e){return new \WP_Error('owr_materials_stopped',$e instanceof \InvalidArgumentException?'Unsupported input':'Save stopped; preserve and resume the same request.',['status'=>409]);}
        }]);}});
        add_action('rest_api_init',function(){register_rest_route('owr-materials/v1','/native-result',['methods'=>'GET','permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function($q){$s=self::status();$map=get_option('owr_site_projection',[])['map']??[];$asset=(string)$q['asset'];if(!isset($map[$asset]))return new \WP_Error('missing','Material is not applied',['status'=>409]);$id=$map[$asset];$p=get_post($id);$response=new \WP_REST_Response(['attachment'=>$p->post_type==='attachment'?wp_prepare_attachment_for_js($id):null,'id'=>$id,'route'=>$p->post_type==='attachment'?'media':($p->post_type==='page'?'pages':'posts'),'parent'=>hash('sha256',self::canonical($s['receipt']))]);$response->header('Cache-Control','no-store');return $response;}]);});
        add_filter('login_redirect',fn($redirect)=>admin_url('admin.php?page=owr-site-materials'));
        add_action('wp_dashboard_setup',function(){remove_meta_box('dashboard_quick_press','dashboard','side');},99);
        add_action('admin_menu',function(){add_menu_page('S3先行編集','S3先行編集','manage_options','owr-site-materials',[self::class,'screen'],'dashicons-cloud');});
        // S3-first must not be bypassed by another UI or REST endpoint.
        add_filter('rest_pre_dispatch',function($result,$server,$request){if($result!==null)return $result;if(!in_array($request->get_method(),['GET','HEAD','OPTIONS'],true)&&preg_match('~^/wp/v2/(posts|pages|media)(/|$)~',$request->get_route())){return new \WP_Error('owr_materials_entry','Use the S3-first editor',['status'=>409]);}return $result;},10,3);
        add_filter('wp_insert_post_data',function($data,$postarr){if(!self::$applying&&in_array($data['post_type'],['post','page','attachment'],true)&&!(empty($postarr['ID'])&&$data['post_status']==='auto-draft'&&$data['post_content']===''&&$data['post_excerpt']==='')){throw new \RuntimeException('S3-first editor required');}return $data;},1,2);
        add_filter('pre_delete_post',fn($delete)=>self::$applying?$delete:false,1);add_filter('pre_delete_attachment',fn($delete)=>self::$applying?$delete:false,1);
        add_filter('wp_handle_upload_prefilter',function($file){$file['error']='Use S3-first image registration';return $file;});
    }
    public static function enqueue(string $hook):void {
        if($hook !== 'toplevel_page_owr-site-materials' || !current_user_can('manage_options'))return;
        wp_enqueue_script('owr-site-materials',plugins_url('../assets/site-materials-editor.js',__FILE__),[], '0.2.0',true);
        wp_add_inline_script('owr-site-materials','window.owrMaterialsConfig='.wp_json_encode(['url'=>rest_url('owr-materials/v1/'),'nonce'=>wp_create_nonce('wp_rest')]).';','before');
    }
    public static function screen():void {
        if(!current_user_can('manage_options')){wp_die('Forbidden');}
        echo '<div class="wrap"><h1>S3先行編集：投稿・固定ページ・画像</h1><p>保存した素材をS3で確定してから、この専用WordPressへ保存済みの投稿状態で反映します。</p><p id="owr-material-status" role="status"></p><select id="owr-material-select"></select> <button id="owr-add-post">投稿を追加</button> <button id="owr-add-page">固定ページを追加</button> <button id="owr-add-image">画像を登録</button><fieldset id="owr-material-fields"><p>タイトル／画像の代替文字<br><input id="owr-material-title" class="regular-text"></p><p>スラッグ<br><input id="owr-material-slug"></p><p>親ページID（任意）<br><input id="owr-material-parent"></p><p>本文：段落、## 見出し、[文字](asset:ID)、![画像](asset:ID)<br><textarea id="owr-material-body" rows="12" cols="85"></textarea></p><p>PNG/JPEG画像<br><input id="owr-material-file" type="file" accept="image/png,image/jpeg"></p></fieldset><p><button id="owr-material-save" class="button button-primary">S3へ保存して反映</button> <button id="owr-material-resume" class="button">同じ要求を再開</button></p></div>';
    }
}
