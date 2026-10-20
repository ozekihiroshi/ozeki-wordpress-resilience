<?php
namespace Ozeki\Resilience;

final class ObserverAdmin {
    const ALARMS = ['monitor_stopped'=>'完了・応答の期限超過','heartbeat_invalid'=>'生存記録不正','notification_delivery_failed'=>'監視側の通知異常'];
    static function stamp($value): int {
        if (!is_string($value) || strlen($value)>64 || !preg_match('/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/D',$value)) { throw new \InvalidArgumentException(); }
        $stamp=strtotime($value);
        if ($stamp===false || $stamp>time()+5) { throw new \InvalidArgumentException(); }
        return $stamp;
    }
    static function count($value): int {
        if (!is_int($value) || $value<0 || $value>1000000000) { throw new \InvalidArgumentException(); }
        return $value;
    }
    static function status(array $settings, $path=null, ?string $monitorId=null): array {
        if ($path===null) {
            if (!defined('OWR_OBSERVER_STATUS_FILE')) { return ['state'=>'unavailable']; }
            $path=OWR_OBSERVER_STATUS_FILE;
        }
        if (!is_string($path) || is_link($path) || !is_file($path) || !is_readable($path)) { return ['state'=>'unavailable']; }
        try {
            $raw=file_get_contents($path,false,null,0,32769);
            if ($raw===false || strlen($raw)>32768) { throw new \InvalidArgumentException(); }
            $v=json_decode($raw,true,32,JSON_THROW_ON_ERROR);
            if (($v['format'] ?? '')!=='owr-observer-status-v1' || ($v['site_id'] ?? '')!==$settings['site_id'] || !is_bool($v['simulated'] ?? null) || !is_string($v['monitor_id'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$v['monitor_id'])) { throw new \InvalidArgumentException(); }
            if ($monitorId!==null && $v['monitor_id']!==$monitorId) { throw new \InvalidArgumentException(); }
            $observed=self::stamp($v['observed_at'] ?? null);$targets=[];
            foreach (['reachability','watchdog'] as $key) {
                $item=$v['targets'][$key] ?? null;
                if (!is_array($item) || !array_key_exists('last_seen',$item) || !is_array($item['active'] ?? null) || count($item['active'])>3 || !in_array($item['observation'] ?? null,['confirmed','unavailable','invalid','missing'],true)) { throw new \InvalidArgumentException(); }
                if ($item['last_seen']!==null && self::stamp($item['last_seen'])>$observed+5) { throw new \InvalidArgumentException(); }
                foreach ($item['active'] as $alarm) { if (!is_string($alarm) || !isset(self::ALARMS[$alarm])) { throw new \InvalidArgumentException(); } }
                $targets[$key]=['last_seen'=>$item['last_seen'],'active'=>$item['active'],'pending'=>self::count($item['pending'] ?? null),'observation'=>$item['observation']];
            }
            $delivery=$v['delivery'] ?? [];
            if (!in_array($delivery['state'] ?? null,['ok','failed','unknown'],true)) { throw new \InvalidArgumentException(); }
            $delivery=['state'=>$delivery['state'],'pending'=>self::count($delivery['pending'] ?? null)];
            if (!is_array($v['history'] ?? null) || count($v['history'])>20) { throw new \InvalidArgumentException(); }
            $history=[];
            foreach ($v['history'] as $e) {
                if (!is_array($e) || !is_string($e['target'] ?? null) || !isset($targets[$e['target']]) || !is_string($e['kind'] ?? null) || !isset(self::ALARMS[$e['kind']]) || !in_array($e['transition'] ?? null,['opened','resolved'],true) || self::stamp($e['at'] ?? null)>$observed) { throw new \InvalidArgumentException(); }
                $history[]=array_intersect_key($e,array_flip(['target','kind','transition','at']));
            }
            $result=['state'=>time()-$observed>=300?'stale':'current','observed_at'=>$v['observed_at'],'monitor_id'=>$v['monitor_id'],'simulated'=>$v['simulated'],'targets'=>$targets,'delivery'=>$delivery,'history'=>$history];
            if (isset($v['configuration'])) { $result['configuration']=ObserverSettings::configuration($v['configuration']); }
            return $result;
        } catch (\Throwable $e) { return ['state'=>'invalid']; }
    }
    static function render(array $settings): void {
        NotificationAdmin::guard();
        self::renderStatus(self::status($settings),'watchdog・監視ホスト',
            ['reachability'=>'監視ホストへの到達性','watchdog'=>'watchdogの処理完了'],'owr-observer');
    }
    static function renderStatus(array $s, string $title, array $names, string $id): void {
        NotificationAdmin::guard();
        echo '<section id="'.esc_attr($id).'"><h2>'.esc_html($title).'</h2><p data-observer-state="'.esc_attr($s['state']).'">'.esc_html(['unavailable'=>'外部観測の報告は未取得です。正常とは判定できません。','invalid'=>'報告の形式・対象サイト・時刻を確認できません。','stale'=>'報告が5分以上更新されていません。現在の状態は不明です。以下は最後に受信した記録です。','current'=>'別ホストからの観測結果を受信しています。'][$s['state']]).'</p>';
        if (isset($s['targets'])) {
            echo '<p>観測完了：'.esc_html($s['observed_at']).' ／ '.esc_html($s['monitor_id']).($s['simulated']?' ／ 専用環境・模擬配送':'').'</p>';
            echo '<div style="max-width:100%;overflow-x:auto" tabindex="0" aria-label="監視状態一覧"><table class="widefat striped" style="min-width:720px"><thead><tr><th>対象</th><th>最終確認</th><th>状態・警報</th><th>通知引渡し待ち</th></tr></thead><tbody>';
            foreach ($s['targets'] as $key=>$t) {
                $state=['confirmed'=>'確認済み','unavailable'=>'今回の取得は不能','invalid'=>'記録が不正','missing'=>'完了記録が未取得'][$t['observation']];
                $alarms=array_map(fn($a)=>self::ALARMS[$a],$t['active']);
                if (!$alarms) { $alarms[]=($t['observation']==='confirmed' && $t['last_seen']!==null)?'発報中の警報なし':'警報判定待ち・状態未確認'; }
                echo '<tr><th>'.esc_html($names[$key]).'</th><td>'.esc_html($t['last_seen'] ?? '未取得').'</td><td>'.esc_html(($s['state']==='stale'?'前回記録：':'').$state.' ／ '.implode('、',$alarms)).'</td><td>'.esc_html((string)$t['pending']).'</td></tr>';
            }
            echo '</tbody></table></div><h3>独立した警報通知</h3><p>'.esc_html(($s['state']==='stale'?'前回記録：':'').['ok'=>'配送処理で異常は報告されていません（端末受信・人の確認を保証しません）。','failed'=>'通知失敗・未配送または配送処理の異常があります。外部観測ホストを確認してください。','unknown'=>'通知配送の状態は未確認です。'][$s['delivery']['state']]).'</p><p>未配送・結果不明などの件数：'.esc_html((string)$s['delivery']['pending']).'</p><h3>最近の警報履歴（最大20件）</h3><ul>';
            foreach ($s['history'] as $e) { echo '<li>'.esc_html($e['at'].' ／ '.$names[$e['target']].' ／ '.self::ALARMS[$e['kind']].' ／ '.($e['transition']==='opened'?'発生':'解消')).'</li>'; }
            if (!$s['history']) { echo '<li>報告内に履歴はありません。</li>'; }
            echo '</ul>';
        }
        echo '<p>到達不能はホスト停止・通信断・SSH設定異常などを含みます。この画面は外部監視の代わりにはなりません。サイト停止中の警報は外部観測側から送信します。</p></section>';
    }
}
