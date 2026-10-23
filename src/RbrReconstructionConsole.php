<?php
declare(strict_types=1);
namespace Owr;
/** Explicit external-kit opt-in. Report must be mounted read-only to WordPress. */
final class RbrReconstructionConsole {
    public static function report(string $path): array {
        if(is_link($path)||!is_file($path)||filesize($path)>1048576)throw new \RuntimeException('Report unavailable');
        $r=json_decode(file_get_contents($path),true,32,JSON_THROW_ON_ERROR);
        if(($r['schema']??'')!=='owr-reconstruction-console-v1'||!is_int($r['updated_at']??null)||!is_array($r['items']??null))throw new \RuntimeException('Invalid report');
        $r['stale']=time()-$r['updated_at']>90||$r['updated_at']>time()+5;
        return $r;
    }
    public static function enqueue(string $report,string $inbox,array $input,?array $history=null): array {
        $keys=array_keys($input);sort($keys);
        if($keys!==['item_id','token']||!is_string($input['item_id'])||!preg_match('/^[a-zA-Z0-9_-]{1,64}$/D',$input['item_id'])||!is_string($input['token'])||!preg_match('/^[a-f0-9]{64}$/D',$input['token']))throw new \RuntimeException('Invalid request');
        $r=self::report($report);$found=false;
        foreach($r['items'] as $item)if(($item['item_id']??null)===$input['item_id']&&($item['token']??null)===$input['token']&&($item['approval']??null)==='approved'){if(($item['require_local_match']??false)&&($history===null||!self::matches($item,$history)))throw new \RuntimeException('Local generation/Q mismatch');$found=true;}
        if($r['stale']||!$found||!is_dir($inbox)||is_link($inbox))throw new \RuntimeException('Fresh approval report required');
        $id=hash('sha256',$input['item_id'].':'.$input['token']);$path=$inbox.'/'.$id.'.json';
        $raw=json_encode(['item_id'=>$input['item_id'],'token'=>$input['token']],JSON_THROW_ON_ERROR);
        if(is_link($path))throw new \RuntimeException('Unsafe request path');
        $h=@fopen($path,'x');
        if($h){try{if(fwrite($h,$raw)!==strlen($raw)||!fflush($h))throw new \RuntimeException('Request write failed');}finally{fclose($h);}}
        elseif(!is_file($path)||file_get_contents($path)!==$raw)throw new \RuntimeException('Request needs operator review');
        return ['request_id'=>$id,'state'=>'requested'];
    }
    public static function matches(array $item,array $history): bool {
        foreach($history['generations']??[] as $g){
            if(($g['state']??'')==='applied' && isset($g['generation'],$item['generation'],$g['q_sha256'],$item['q_sha256'])
                && $g['generation']==$item['generation'] && $g['q_sha256']===$item['q_sha256'])return true;
        }
        return false;
    }
    public static function boot(\Closure $factory,array $ids,string $report,string $inbox): void {
        $allowed=static function()use($ids){if(!is_user_logged_in()||!current_user_can('manage_options'))return false;foreach($ids as $id)if(!current_user_can('edit_post',$id))return false;return true;};
        add_action('rest_api_init',static function()use($allowed,$factory,$report,$inbox){
            register_rest_route('owr-rbr/v1','/reconstruction',[
                ['methods'=>'GET','permission_callback'=>$allowed,'callback'=>static function()use($factory,$report){
                    try{$external=self::report($report);}catch(\Throwable){$external=['stale'=>true,'items'=>[],'error'=>'External report unavailable'];}
                    try{$history=$factory()->generationHistory();}catch(\Throwable){$history=['error'=>'Saved history unavailable'];}
                    $r=new \WP_REST_Response(['local'=>$history,'external'=>$external]);$r->header('Cache-Control','no-store');return $r;
                }],
                ['methods'=>'POST','permission_callback'=>$allowed,'callback'=>static function($request)use($report,$inbox,$factory){
                    try{if(strlen($request->get_body())>1024)throw new \RuntimeException();return new \WP_REST_Response(self::enqueue($report,$inbox,$request->get_json_params(),$factory()->generationHistory()),202);}
                    catch(\Throwable){return new \WP_Error('owr_reconstruction_rejected','Request rejected. Refresh status or ask the operator to review approval and worker.',['status'=>409]);}
                }]
            ]);
        });
        add_action('admin_menu',static function()use($allowed){add_management_page('Reconstruction','再構築の状態','manage_options','owr-reconstruction',static function()use($allowed){
            if(!$allowed())wp_die('Permission denied');
            echo '<div class="wrap"><h1>保存世代と再構築</h1><p>ローカル保存履歴と、外部で登録・承認された復旧キットを分けて表示します。自動公開は行いません。</p><p>署名承認・キット登録は外部担当者の操作です。状態が古い場合は要求できません。</p><button id="owr-refresh" class="button">状態を更新</button><div id="owr-console" aria-live="polite"></div></div>';
            $config=['api'=>rest_url('owr-rbr/v1/reconstruction'),'nonce'=>wp_create_nonce('wp_rest')];
            echo '<script>const owrConsole='.wp_json_encode($config,JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT).';'.file_get_contents(dirname(__DIR__).'/assets/rbr-reconstruction-console.js').'</script>';
        });});
        add_action('admin_notices',static function()use($allowed){if($allowed()&&($_GET['page']??'')==='owr-protected-editor')echo '<div class="notice notice-info"><p><a href="'.esc_url(admin_url('tools.php?page=owr-reconstruction')).'">保存世代・Q・署名承認・再構築の状態を確認</a></p></div>';});
    }
}
