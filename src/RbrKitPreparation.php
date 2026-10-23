<?php
declare(strict_types=1);
namespace Owr;
final class RbrKitPreparation {
 public static function request(string $report,string $inbox,array $input,array $history):array {
  $keys=array_keys($input);sort($keys);
  if($keys!==['attempt','operation']||!is_string($input['operation'])||!is_int($input['attempt'])||$input['attempt']<0||$input['attempt']>99)throw new \RuntimeException('Invalid selection');
  $r=RbrReconstructionConsole::report($report);
  if($r['stale']||!preg_match('/^[a-f0-9]{64}$/D',$r['profile_sha256']??''))throw new \RuntimeException('Fresh preparation worker required');
  $g=null;foreach($history['generations']??[] as $entry)if($entry['operation']===$input['operation'])$g=$entry;
  if(!$g||$g['state']!=='applied'||empty($g['expected_ref'])||empty($g['generation']))throw new \RuntimeException('Applied generation with Q required');
  $receipt=json_encode(['state'=>'applied','sequence'=>$g['sequence'],'generation'=>$g['generation'],'expected_ref'=>$g['expected_ref']],JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
  $job=hash('sha256',$receipt.$r['profile_sha256']);$previous=null;
  foreach($r['items'] as $item)if(($item['job_id']??'')===$job)$previous=$item;
  $attempt=$input['attempt'];
  if($previous){if(!in_array($previous['state'],['failed','interrupted'],true)||$attempt!==$previous['attempt']+1)throw new \RuntimeException('Not resumable');}
  elseif($attempt!==0)throw new \RuntimeException('Initial attempt required');
  if(!is_dir($inbox)||is_link($inbox))throw new \RuntimeException('Unsafe inbox');
  $raw=json_encode(['job_id'=>$job,'attempt'=>$attempt,'profile_sha256'=>$r['profile_sha256'],'receipt'=>$receipt],JSON_THROW_ON_ERROR);
  $path=$inbox.'/'.$job.'-'.$attempt.'.json';if(is_link($path))throw new \RuntimeException('Unsafe request');
  $h=@fopen($path,'x');if($h){try{if(fwrite($h,$raw)!==strlen($raw)||!fflush($h))throw new \RuntimeException('Write failure');}finally{fclose($h);}}
  elseif(!is_file($path)||file_get_contents($path)!==$raw)throw new \RuntimeException('Request needs review');
  return ['job_id'=>$job,'state'=>'requested','attempt'=>$attempt];
 }
 public static function boot(\Closure $factory,array $ids,string $report,string $inbox):void {
  $allowed=static function()use($ids){if(!current_user_can('manage_options'))return false;foreach($ids as $id)if(!current_user_can('edit_post',$id))return false;return true;};
  add_action('rest_api_init',static function()use($factory,$report,$inbox,$allowed){register_rest_route('owr-rbr/v1','/kit-preparation',[
   ['methods'=>'GET','permission_callback'=>$allowed,'callback'=>static function()use($factory,$report){try{$r=RbrReconstructionConsole::report($report);}catch(\Throwable){$r=['stale'=>true,'items'=>[]];}$out=new \WP_REST_Response(['local'=>$factory()->generationHistory(),'external'=>$r]);$out->header('Cache-Control','no-store');return $out;}],
   ['methods'=>'POST','permission_callback'=>$allowed,'callback'=>static function($request)use($factory,$report,$inbox){try{if(strlen($request->get_body())>1024)throw new \RuntimeException();return new \WP_REST_Response(self::request($report,$inbox,$request->get_json_params(),$factory()->generationHistory()),202);}catch(\Throwable){return new \WP_Error('owr_preparation_rejected','要求を受け付けられません。世代・状態・担当者の確認が必要です。',['status'=>409]);}}]
  ]);});
  add_action('admin_menu',static function()use($allowed){add_management_page('Kit preparation','復旧キットの準備','manage_options','owr-kit-preparation',static function()use($allowed){if(!$allowed())wp_die('Permission denied');echo '<div class="wrap"><h1>承認待ちの復旧キットを準備</h1><p>保存済み世代を選択してください。署名承認・再構築・公開は行いません。</p><button id="owr-kit-refresh" class="button">状態を更新</button><div id="owr-kit-status" aria-live="polite"></div></div>';echo '<script>const owrKit='.wp_json_encode(['api'=>rest_url('owr-rbr/v1/kit-preparation'),'nonce'=>wp_create_nonce('wp_rest')],JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT).';'.file_get_contents(dirname(__DIR__).'/assets/rbr-kit-preparation.js').'</script>';});});
  add_action('admin_notices',static function()use($allowed){if($allowed()&&in_array($_GET['page']??'',['owr-protected-editor','owr-reconstruction'],true))echo '<div class="notice notice-info"><p><a href="'.esc_url(admin_url('tools.php?page=owr-kit-preparation')).'">保存世代から復旧キットを準備</a></p></div>';});
 }
}
