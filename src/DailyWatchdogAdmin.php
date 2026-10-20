<?php
namespace Ozeki\Resilience;

/** Local, bounded, read-only view of two independently observed hosts. */
final class DailyWatchdogAdmin {
    static function boot(): void {
        add_action('admin_menu',static function() {
            $hook=add_submenu_page(NotificationAdmin::SLUG,'生成・取得の独立監視','生成・取得の独立監視',
                'manage_options','owr-daily-watchdog',[self::class,'render']);
            add_action('load-'.$hook,[DailyAdmin::class,'guard']);
        });
    }
    static function read(string $role): array {
        if (!in_array($role,['source','receiver'],true) || !defined('OWR_DAILY_SITE_ID') ||
            !defined('OWR_DAILY_WATCHDOG_REPORTS')) { return ['state'=>'unavailable']; }
        $all=OWR_DAILY_WATCHDOG_REPORTS;
        $c=is_array($all)?($all[$role] ?? null):null;
        if ($c===null) { return ['state'=>'unavailable']; }
        if (!is_array($c) || !is_string($c['path'] ?? null) || $c['path']==='' ||
            !is_string($c['monitor_id'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$c['monitor_id'])) {
            return ['state'=>'invalid'];
        }
        return ObserverAdmin::status(['site_id'=>OWR_DAILY_SITE_ID],$c['path'],$c['monitor_id']);
    }
    static function transfer(string $role): array {
        $all=defined('OWR_DAILY_WATCHDOG_REPORTS')?OWR_DAILY_WATCHDOG_REPORTS:[];
        $c=is_array($all)?($all[$role] ?? null):null;
        if (!is_array($c) || !isset($c['transfer_file'])) { return ['state'=>'unavailable']; }
        $p=$c['transfer_file'];
        if (!is_string($p) || is_link($p) || !is_file($p) || !is_readable($p)) { return ['state'=>'unavailable']; }
        try {
            $raw=file_get_contents($p,false,null,0,8193);
            if ($raw===false || strlen($raw)>8192) { throw new \RuntimeException(); }
            $v=json_decode($raw,true,16,JSON_THROW_ON_ERROR);
            if (($v['format'] ?? '')!=='owr-observer-transfer-v1' || !defined('OWR_DAILY_SITE_ID') ||
                ($v['site_id'] ?? null)!==OWR_DAILY_SITE_ID || ($v['monitor_id'] ?? null)!==($c['monitor_id'] ?? '') ||
                !in_array($v['state'] ?? '', ['ok','source_stale','transfer_failed'],true)) { throw new \RuntimeException(); }
            $at=ObserverAdmin::stamp($v['attempted_at'] ?? null);
            if ($at>time()+5) { throw new \RuntimeException(); }
            return ['state'=>time()-$at>=300?'stopped':$v['state'],'attempted_at'=>$v['attempted_at']];
        } catch (\Throwable $e) { return ['state'=>'invalid']; }
    }
    static function render(): void {
        DailyAdmin::guard();
        echo '<div class="wrap"><h1>生成側・取得側の独立watchdog</h1><p>読取り専用。外部watchdogから受け取った状態報告を表示します。警報の解除・再送・設定変更は行いません。</p>';
        foreach (['source'=>'生成側','receiver'=>'取得側'] as $role=>$label) {
            $transfer=self::transfer($role);
            $labels=['unavailable'=>'定期取得の記録は未取得です。','invalid'=>'定期取得の記録を確認できません。',
                'ok'=>'定期取得は成功しています。','transfer_failed'=>'転送に失敗しています。直前の報告を保持しています。',
                'source_stale'=>'接続できましたが、独立watchdogの報告が5分以上更新されていません。',
                'stopped'=>'定期取得の記録が5分以上更新されていません。取得処理の稼働を確認してください。'];
            echo '<p data-transfer-role="'.esc_attr($role).'" data-transfer-state="'.esc_attr($transfer['state']).'">'.esc_html($label.'：'.$labels[$transfer['state']].(isset($transfer['attempted_at'])?' 最終取得処理：'.$transfer['attempted_at']:'')).'</p>';

            ObserverAdmin::renderStatus(self::read($role),$label,
                ['reachability'=>$label.'への到達性','watchdog'=>$label.'の状態報告の更新'],'owr-daily-watchdog-'.$role);
        }
        echo '<p>履歴の「発生」「解消」は警報状態の変化です。通知先への配送、端末受信、人による確認とは別です。表示は復旧セットの署名承認ではありません。</p></div>';
    }
}
