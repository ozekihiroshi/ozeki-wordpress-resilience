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
            $tmp=$path.'.tmp';$f=fopen($tmp,'xb');if(!$f)throw new \RuntimeException('Queue unavailable');
            try{chmod($tmp,0600);if(fwrite($f,$raw)!==strlen($raw)||!fflush($f))throw new \RuntimeException('Queue write failed');if(function_exists('fsync'))fsync($f);}finally{fclose($f);}
            if(!rename($tmp,$path))throw new \RuntimeException('Queue publish failed');return ['job'=>$job];
        }finally{flock($lock,LOCK_UN);fclose($lock);}
    }
    public static function boot(string $bridge):void {
        if(getenv('OWR_RBR_DISPOSABLE')!=='1')throw new \RuntimeException('Dedicated environment required');self::$dir=$bridge.'/reconstruction';
        add_action('rest_api_init',function(){foreach(['state'=>'GET','request'=>'POST'] as $action=>$method){register_rest_route('owr-materials-recovery/v1','/'.$action,['methods'=>$method,'permission_callback'=>fn()=>current_user_can('manage_options'),'callback'=>function($request)use($action){try{
            if(strlen($request->get_body())>2048)throw new \RuntimeException('Request too large');
            $value=$action==='state'?self::status(self::$dir):self::request(self::$dir,$request->get_json_params()??[]);$r=new \WP_REST_Response($value);$r->header('Cache-Control','no-store');return $r;
        }catch(\Throwable $e){return new \WP_Error('owr_recovery_stopped','Selection unavailable or report stale; preserve existing jobs.',['status'=>409]);}}]);}});
        add_action('admin_menu',function(){add_submenu_page('owr-site-materials','素材世代から再構築','素材世代から再構築','manage_options','owr-site-reconstruction',[self::class,'screen']);},20);
    }
    public static function screen():void {
        if(!current_user_can('manage_options'))wp_die('Forbidden');
        echo '<div class="wrap"><h1>素材世代から再構築</h1><p>選択したS3固定世代から、新しい専用WordPressを非公開で作成します。元サイトのDBは使用しません。公開・既存サイトへの上書きは行いません。</p><p id="owr-recovery-status" role="status"></p><p id="owr-recovery-target"></p><select id="owr-recovery-generation"></select><pre id="owr-recovery-details"></pre><button class="button button-primary" id="owr-recovery-start">選択世代を専用復旧先へ再構築</button><h2>再構築結果</h2><pre id="owr-recovery-jobs"></pre></div>';
        echo '<script>window.owrRecoveryConfig='.wp_json_encode(['url'=>rest_url('owr-materials-recovery/v1/'),'nonce'=>wp_create_nonce('wp_rest')]).';</script><script>'.file_get_contents(__DIR__.'/../assets/site-reconstruction.js').'</script>';
    }
}
