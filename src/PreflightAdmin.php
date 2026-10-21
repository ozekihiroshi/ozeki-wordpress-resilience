<?php
namespace Ozeki\Resilience;
/** Read-only, local preflight report. Never opens SSH from a web request. */
final class PreflightAdmin {
 static function boot(): void {
  add_action('admin_menu',static function(){
   $hook=add_submenu_page(NotificationAdmin::SLUG,'導入前検査','導入前検査','manage_options','owr-preflight',[self::class,'render']);
   add_action('load-'.$hook,[DailyAdmin::class,'guard']);
  });
 }
 static function read(): array {
  if (!defined('OWR_PREFLIGHT_REPORT')||!defined('OWR_PREFLIGHT_SITE_ID')||!defined('OWR_PREFLIGHT_CONFIG_SHA256')) return ['state'=>'missing'];
  $p=OWR_PREFLIGHT_REPORT;
  if (!is_string($p)||is_link($p)||!is_file($p)||!is_readable($p)) return ['state'=>'missing'];
  try {
   $raw=file_get_contents($p,false,null,0,65537);
   if ($raw===false||strlen($raw)>65536) throw new \RuntimeException();
   $v=json_decode($raw,true,32,JSON_THROW_ON_ERROR);
   if (($v['format']??'')!=='owr-preflight-admin-v1'||($v['site_id']??null)!==OWR_PREFLIGHT_SITE_ID||($v['config_sha256']??null)!==OWR_PREFLIGHT_CONFIG_SHA256) throw new \RuntimeException();
   $at=ObserverAdmin::stamp($v['attempted_at']??null);
   if ($at>time()+5) throw new \RuntimeException();
   $r=$v['result']??null;
   if (!is_array($r)||($r['production_ready']??null)!==false||!in_array($r['state']??'', ['unsupported','needs_configuration','eligible_for_dedicated_trial'],true)) throw new \RuntimeException();
   $h=$r['host_observation']['state']??'unavailable';
   if (!in_array($h,['validated_report','unavailable','invalid','probe_failed'],true)) throw new \RuntimeException();
   $issues=$r['issues']??null;
   if (!is_array($issues)||count($issues)>100) throw new \RuntimeException();
   $clean=[];
   foreach($issues as $i){
    if (!is_string($i['code']??null)||!preg_match('/^[a-z0-9_]{1,100}$/D',$i['code'])||!in_array($i['category']??'', ['configuration','environment','operational','unsupported','unclassified'],true)) throw new \RuntimeException();
    $clean[]=['code'=>$i['code'],'category'=>$i['category']];
   }
   $unknown=$r['host_observation']['unverified']??[];
   if (!is_array($unknown)||count($unknown)>20) throw new \RuntimeException();
   foreach($unknown as $x) if (!is_string($x)||!preg_match('/^[a-z_]{1,80}$/D',$x)) throw new \RuntimeException();
   return ['state'=>time()-$at>=300?'stale':'current','at'=>$v['attempted_at'],'verdict'=>$r['state'],'host'=>$h,'issues'=>$clean,'unknown'=>$unknown];
  } catch(\Throwable $e){return ['state'=>'invalid'];}
 }
 static function transfer(): array {
  if (!defined('OWR_PREFLIGHT_TRANSFER_FILE')) return ['state'=>'unavailable'];
  $p=OWR_PREFLIGHT_TRANSFER_FILE;
  if(!is_string($p)||is_link($p)||!is_file($p)||!is_readable($p)) return ['state'=>'unavailable'];
  try {
   $raw=file_get_contents($p,false,null,0,8193);
   if($raw===false||strlen($raw)>8192) throw new \RuntimeException();
   $v=json_decode($raw,true,16,JSON_THROW_ON_ERROR);
   if(($v['format']??'')!=='owr-preflight-transfer-v1'||!defined('OWR_PREFLIGHT_SITE_ID')||!defined('OWR_PREFLIGHT_CONFIG_SHA256')||($v['site_id']??null)!==OWR_PREFLIGHT_SITE_ID||($v['config_sha256']??null)!==OWR_PREFLIGHT_CONFIG_SHA256||!in_array($v['state']??'', ['ok','acquisition_failed','transfer_failed','source_stale'],true)) throw new \RuntimeException();
   $at=ObserverAdmin::stamp($v['attempted_at']??null);
   $state=time()-$at>=300?'stopped':$v['state'];
   if($state==='ok'||$state==='acquisition_failed') {
    $report=self::read();
    if(!isset($report['at'])||($v['report_at']??null)!==$report['at']) $state='inconsistent';
   }
   return ['state'=>$state];
  } catch(\Throwable $e){return ['state'=>'invalid'];}
 }
 static function render(): void {
  DailyAdmin::guard();$v=self::read();
  echo '<div class="wrap"><h1>SSH棚卸し・導入前検査</h1><p>読取り専用。SSH取得は外部で行います。この画面は取得・設定変更・署名承認を実行しません。</p>';
  $transfer=self::transfer();
  $tl=['unavailable'=>'定期更新の記録は未取得です。','invalid'=>'定期更新の記録が不正です。','source_stale'=>'接続先の検査記録が5分以上更新されていません。検査側を確認してください。','stopped'=>'定期更新が5分以上確認できません。更新停止または受渡し停止を確認してください。','ok'=>'定期取得・受渡しは成功しています。','acquisition_failed'=>'今回の棚卸し取得・検査に失敗しました。','transfer_failed'=>'WordPressへの受渡しに失敗しました。表示中の検査結果は直前の記録です。','inconsistent'=>'更新記録と検査結果が一致しません。反映途中または受渡し不整合です。'];
  echo '<p data-preflight-transfer="'.esc_attr($transfer['state']).'">'.esc_html($tl[$transfer['state']]).'</p>';
  $labels=['missing'=>'検査記録が未取得です。','invalid'=>'検査記録を確認できません。サイト・設定版・形式を確認してください。','stale'=>'情報が古くなっています（5分以上）。現在の状態は未確認です。','current'=>'直近5分以内の検査記録です。'];
  echo '<p data-preflight-state="'.esc_attr($v['state']).'">'.esc_html($labels[$v['state']]).'</p>';
  if(isset($v['at'])){
   $host=['validated_report'=>'棚卸し応答の検査済み','unavailable'=>'取得失敗・取得不可','invalid'=>'棚卸し応答が不正','probe_failed'=>'ホスト内の検査失敗'];
   $verdict=['unsupported'=>'未対応の構成あり','needs_configuration'=>'設定・確認が必要','eligible_for_dedicated_trial'=>'専用環境での試験候補'];
   echo '<p>最終検査：'.esc_html($v['at']).'</p><p>'.esc_html($host[$v['host']]).' / '.esc_html($verdict[$v['verdict']]).'</p><h2>未確認項目</h2><ul>';
   $names=['writers'=>'更新経路','queue'=>'キュー','dependencies'=>'依存関係','runtime_image_binding'=>'実行環境との対応','multisite_config'=>'マルチサイト設定','storage'=>'保管先','trust'=>'信頼情報','operational_ledgers'=>'処理台帳','file_snapshot_consistency'=>'ファイル取得の整合性'];
   foreach($v['unknown'] as $x) echo '<li>'.esc_html($names[$x]??$x).'</li>';
   if(!$v['unknown']) echo '<li>この記録には一覧がありません。確認済みを意味しません。</li>';
   echo '</ul><h2>確認が必要な事項</h2><ul>';
   $cats=['configuration'=>'設定','environment'=>'環境','operational'=>'運用','unsupported'=>'未対応','unclassified'=>'原因未確定'];
   foreach($v['issues'] as $i) echo '<li>'.esc_html($cats[$i['category']].'：'.$i['code']).'</li>';
   echo '</ul>';
  }
  echo '<p>本番導入可能・マルウェア不在の証明ではありません。SSHホスト鍵の照合と独立署名による証明は別です。</p></div>';
 }
}
