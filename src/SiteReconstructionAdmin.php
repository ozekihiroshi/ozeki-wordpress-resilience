<?php
declare(strict_types=1);
namespace Owr;
/** Read and queue the multi-material schema only; never invokes a shell in WordPress. */
final class SiteReconstructionAdmin {
    private static string $dir;
    public static function status(string $dir):array {
        $path=$dir.'/status.json';
        if(!is_file($path))return ['available'=>false,'stale'=>true,'items'=>[],'jobs'=>[]];
        $v=json_decode(file_get_contents($path),true,64,JSON_THROW_ON_ERROR);
        if(($v['schema']??null)!=='owr-site-reconstruction-v1')throw new \RuntimeException('Wrong report schema');
        $v['available']=true;$v['stale']=($v['updated_at']??0)<time()-120||($v['updated_at']??0)>time()+30;return $v;
    }
    public static function request(string $dir,array $input):array {
        if(!is_dir($dir.'/requests'))throw new \RuntimeException('Worker not configured');
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Local worker queue protocol; no installation or remote filesystem writes.
        $lock=fopen($dir.'/request.lock','c');if(!$lock||!flock($lock,LOCK_EX|LOCK_NB))throw new \RuntimeException('Busy');
        try {
            $v=self::status($dir);if(!$v['available']||$v['stale'])throw new \RuntimeException('Report stale');
            if(count($input)!==3||array_diff(['generation','q','profile'],array_keys($input)))throw new \RuntimeException('Explicit selection required');
            $found=false;foreach($v['items'] as $item){if(($item['id']??null)===$input['generation']&&($item['eligible']??false)&&($item['q']??null)===$input['q'])$found=true;}
            if(!$found||$v['profile']!==$input['profile'])throw new \RuntimeException('Selection changed');
            foreach(['generation','q','profile'] as $key)if(!preg_match('/^[a-f0-9]{64}$/D',$input[$key]))throw new \RuntimeException('Invalid identifier');
            $job=hash('sha256',SiteMaterialsEditor::canonical($input));$request=['job'=>$job]+$input;
            $path=$dir.'/requests/'.$job.'.json';$raw=SiteMaterialsEditor::canonical($request);
            if(is_file($path)){if(file_get_contents($path)!==$raw)throw new \RuntimeException('Queue conflict');return ['job'=>$job];}
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Local worker queue protocol; no installation or remote filesystem writes.
            $tmp=$path.'.tmp';$f=fopen($tmp,'xb');if(!$f)throw new \RuntimeException('Queue unavailable');
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod,WordPress.WP.AlternativeFunctions.file_system_operations_fclose,WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- Local worker queue protocol; no installation or remote filesystem writes.
            try{chmod($tmp,0600);if(fwrite($f,$raw)!==strlen($raw)||!fflush($f))throw new \RuntimeException('Queue write failed');if(function_exists('fsync'))fsync($f);}finally{fclose($f);}
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.rename_rename -- Local worker queue protocol; no installation or remote filesystem writes.
            if(!rename($tmp,$path))throw new \RuntimeException('Queue publish failed');return ['job'=>$job];
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Local worker queue protocol; no installation or remote filesystem writes.
        }finally{flock($lock,LOCK_UN);fclose($lock);}
    }
    public static function preview(string $dir,string $job):array {
        if(!preg_match('/^[a-f0-9]{64}$/D',$job))throw new \RuntimeException('Invalid preview');
        $state=self::status($dir);$record=null;
        foreach($state['jobs'] as $item)if(($item['job']??null)===$job&&($item['state']??null)==='verified'&&($item['preview_ready']??false))$record=$item;
        if(!$record)throw new \RuntimeException('Preview unavailable');
        $path=$dir.'/previews/'.$job.'.json';if(!is_file($path)||filesize($path)>128*1024*1024)throw new \RuntimeException('Preview unavailable');
        $v=json_decode(file_get_contents($path),true,64,JSON_THROW_ON_ERROR);
        if(($v['schema']??null)!=='owr-private-preview-v1'||$v['job']!==$job||$v['generation']!==$record['generation']||$v['q']!==$record['q'])throw new \RuntimeException('Preview mismatch');
        return $v;
    }
    public static function boot(string $bridge):void {
        add_action('admin_enqueue_scripts',[self::class,'enqueue']);
        if(getenv('OWR_RBR_DISPOSABLE')!=='1')throw new \RuntimeException('Dedicated environment required');self::$dir=$bridge.'/reconstruction';
        add_action('rest_api_init',function(){foreach(['state'=>'GET','request'=>'POST'] as $action=>$method){register_rest_route('owr-materials-recovery/v1','/'.$action,['methods'=>$method,'permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function($request)use($action){try{
            if(strlen($request->get_body())>2048)throw new \RuntimeException('Request too large');
            $value=$action==='state'?self::status(self::$dir):self::request(self::$dir,$request->get_json_params()??[]);$r=new \WP_REST_Response($value);$r->header('Cache-Control','no-store');return $r;
        }catch(\Throwable $e){return new \WP_Error('owr_recovery_stopped','Selection unavailable or report stale; preserve existing jobs.',['status'=>409]);}}]);}});
        add_action('rest_api_init',function(){register_rest_route('owr-materials-recovery/v1','/preview/(?P<job>[a-f0-9]{64})',['methods'=>'GET','permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function($request){try{$r=new \WP_REST_Response(self::preview(self::$dir,$request['job']));$r->header('Cache-Control','no-store');return $r;}catch(\Throwable $e){return new \WP_Error('owr_preview_unavailable','Preview unavailable.',['status'=>404]);}}]);});
        add_action('admin_menu',function(){add_submenu_page('owr-site-materials','素材世代から再構築','素材世代から再構築','manage_options','owr-site-reconstruction',[self::class,'screen']);},20);
    }
    public static function enqueue(string $hook):void {
        if(!str_ends_with($hook, '_page_owr-site-reconstruction') || !current_user_can('manage_options'))return;
        wp_enqueue_script('owr-site-reconstruction',plugins_url('../assets/site-reconstruction.js',__FILE__),[], '0.2.0',true);
        wp_add_inline_script('owr-site-reconstruction','window.owrRecoveryConfig='.wp_json_encode(['url'=>rest_url('owr-materials-recovery/v1/'),'nonce'=>wp_create_nonce('wp_rest')]).';','before');
    }
    public static function screen():void {
        if(!current_user_can('manage_options'))wp_die('Forbidden');
        echo '<div class="wrap"><h1>素材世代から再構築</h1><p>選択したS3固定世代を、設定済みの復旧先WordPressへ投稿状態も含めて再構築します。元サイトのDBは使用しません。外部公開の設定はシステム管理者が管理します。</p><p id="owr-recovery-status" role="status"></p><p id="owr-recovery-target"></p><select id="owr-recovery-generation"></select><pre id="owr-recovery-details"></pre><button class="button button-primary" id="owr-recovery-start">選択世代を専用復旧先へ再構築</button><h2>再構築結果</h2><pre id="owr-recovery-jobs"></pre><h2>任意の内容プレビュー（研究経路）</h2><div id="owr-preview-links"></div><p id="owr-preview-status"></p><iframe id="owr-private-preview" title="再構築内容の非公開プレビュー" sandbox="" referrerpolicy="no-referrer" style="width:100%;height:650px;border:1px solid #ccd" hidden></iframe></div>';
    }
}
