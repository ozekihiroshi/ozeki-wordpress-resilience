<?php
namespace Ozeki\Resilience;

/** Bounded local status view. No commands, settings, requests or credentials. */
final class DailyAdmin {
    const LABELS = [
        'approved'=>'承認済み','awaiting_approval'=>'署名承認待ち','pending'=>'待ち',
        'expired'=>'期限切れ','unverified'=>'未確認','restore_verified'=>'復元検証済み',
        'restore_failed'=>'復元失敗','recovery_running'=>'復元処理中',
        'recovery_interrupted'=>'途中停止・結果不明','recovery_reviewed_closed'=>'後片付け確認済み',
        'registration_pending'=>'結果登録待ち','evidence_error'=>'証拠不整合',
        'approval_expired'=>'承認期限切れ','running'=>'処理中','failed'=>'失敗',
        'unknown'=>'不明','missing'=>'未取得','verified'=>'検証済み','not_verified'=>'未検証',
        'none'=>'なし','not_attempted'=>'未実施','not_observed'=>'未観測','stored'=>'保存完了',
        'finished'=>'終了','interrupted'=>'途中停止','reviewed_closed'=>'後片付け確認済み',
        'succeeded'=>'成功','recorded'=>'登録済み','waiting'=>'待機','unavailable'=>'確認不能',
        'not_recorded'=>'後片付け記録なし','incomplete'=>'後片付け未完了',
        'closed'=>'後片付け確認済み','automatic_removed'=>'復元処理で資源削除済み','invalid'=>'記録不整合',
    ];
    static function boot(): void {
        add_action('admin_menu',static function() {
            $hook=add_submenu_page(NotificationAdmin::SLUG,'日次バックアップ・復元','日次バックアップ・復元',
                'manage_options','owr-daily-status',[self::class,'render']);
            add_action('load-'.$hook,[self::class,'guard']);
        });
    }
    static function guard(): void {
        NotificationAdmin::guard();
        if (($_SERVER['REQUEST_METHOD'] ?? 'GET')!=='GET') { wp_die('読取り専用です。','',['response'=>405]); }
    }
    static function read(): array {
        if (!defined('OWR_DAILY_STATUS_FILE') || !defined('OWR_DAILY_SITE_ID')) { return ['state'=>'unavailable']; }
        $p=OWR_DAILY_STATUS_FILE;
        if (!is_string($p) || is_link($p) || !is_file($p) || !is_readable($p)) { return ['state'=>'unavailable']; }
        try {
            $raw=file_get_contents($p,false,null,0,65537);
            if ($raw===false || strlen($raw)>65536) { throw new \RuntimeException(); }
            $v=json_decode($raw,true,16,JSON_THROW_ON_ERROR);
            if (($v['format'] ?? '')!=='owr-daily-admin-v1' || ($v['site_id'] ?? null)!==OWR_DAILY_SITE_ID ||
                !is_bool($v['missing_due_slot'] ?? null)) { throw new \RuntimeException(); }
            $at=ObserverAdmin::stamp($v['observed_at'] ?? null);
            $clean=[];
            foreach (['runs'=>['day','phase','storage_complete','approval_state','restore_state'],
                      'attempts'=>['request_id','day','state','outcome','registration','cleanup']] as $list=>$fields) {
                if (!is_array($v[$list] ?? null) || !array_is_list($v[$list]) || count($v[$list])>30) { throw new \RuntimeException(); }
                $clean[$list]=[];
                foreach ($v[$list] as $row) {
                    $item=[];
                    foreach ($fields as $f) {
                        $x=$row[$f] ?? null;
                        if ($f==='storage_complete') { $valid=is_bool($x); }
                        elseif ($f==='day') { $valid=is_string($x) && preg_match('/^\d{4}-\d{2}-\d{2}$/D',$x); }
                        elseif ($f==='request_id') { $valid=is_string($x) && preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$x); }
                        else { $valid=is_string($x) && isset(self::LABELS[$x]); }
                        if (!$valid) { throw new \RuntimeException(); }
                        $item[$f]=$x;
                    }
                    $clean[$list][]=$item;
                }
            }
            return $clean+['state'=>time()-$at>=300?'stale':'current','observed_at'=>$v['observed_at'],'missing_due_slot'=>$v['missing_due_slot']];
        } catch (\Throwable $e) { return ['state'=>'invalid']; }
    }

    static function transfer(): array {
        if (!defined('OWR_DAILY_TRANSFER_FILE')) { return ['state'=>'unconfigured']; }
        $p=OWR_DAILY_TRANSFER_FILE;
        if (!is_string($p) || is_link($p) || !is_file($p) || !is_readable($p)) { return ['state'=>'unavailable']; }
        try {
            $raw=file_get_contents($p,false,null,0,4097);
            if ($raw===false || strlen($raw)>4096) { throw new \RuntimeException(); }
            $v=json_decode($raw,true,8,JSON_THROW_ON_ERROR);
            if (($v['format'] ?? '')!=='owr-daily-transfer-v1' || !defined('OWR_DAILY_SITE_ID') ||
                ($v['site_id'] ?? null)!==OWR_DAILY_SITE_ID ||
                !in_array($v['state'] ?? null,['ok','transfer_failed','source_failed','source_stale'],true) ||
                !array_key_exists('report_sha256',$v)) { throw new \RuntimeException(); }
            $at=ObserverAdmin::stamp($v['attempted_at'] ?? null);
            $hash=$v['report_sha256'];
            if ($hash!==null && (!is_string($hash) || !preg_match('/^[a-f0-9]{64}$/D',$hash) ||
                !defined('OWR_DAILY_STATUS_FILE') || is_link(OWR_DAILY_STATUS_FILE) ||
                !is_file(OWR_DAILY_STATUS_FILE) || hash_file('sha256',OWR_DAILY_STATUS_FILE)!==$hash)) { throw new \RuntimeException(); }
            if ($v['state']==='ok' && $hash===null) { throw new \RuntimeException(); }
            return ['state'=>time()-$at>=300?'stopped':$v['state'],'attempted_at'=>$v['attempted_at']];
        } catch (\Throwable $e) { return ['state'=>'invalid']; }
    }

    static function render(): void {
        self::guard();
        $v=self::read();
        echo '<div class="wrap"><h1>日次バックアップ・隔離復元</h1><p>読取り専用。保存・署名承認・復元・後片付けの実行はこの画面では行いません。</p>';
        echo '<p data-daily-state="'.esc_attr($v['state']).'">'.esc_html([
            'unavailable'=>'状態報告は未取得です。正常とは判断できません。',
            'invalid'=>'状態報告の形式・対象サイト・時刻を確認できません。',
            'stale'=>'報告が5分以上更新されていません。現在の状態は不明です。以下は前回記録です。',
            'current'=>'状態報告を取得しています。'][$v['state']]).'</p>';

        $transfer=self::transfer();
        echo '<p data-daily-transfer="'.esc_attr($transfer['state']).'">'.esc_html([
            'unconfigured'=>'定期受渡しの観測は未設定です。',
            'unavailable'=>'受渡し処理の記録がありません。',
            'invalid'=>'受渡し記録と状態報告を照合できません。',
            'stopped'=>'受渡し処理が5分以上更新されていません。現在の状態は不明です。',
            'ok'=>'定期受渡し：取得成功。',
            'transfer_failed'=>'転送失敗・応答不正。以下は最後に取得した記録です。',
            'source_failed'=>'生成側で状態報告の更新に失敗しています。以下は前回記録です。',
            'source_stale'=>'生成側の状態報告が5分以上更新されていません。以下は前回記録です。',
        ][$transfer['state']]).'</p>';
        if (isset($transfer['attempted_at'])) { echo '<p>受渡し最終試行：'.esc_html($transfer['attempted_at']).'</p>'; }

        if (isset($v['runs'])) {
            echo '<p>観測時刻：'.esc_html($v['observed_at']).' ／ '.esc_html($v['missing_due_slot']?'予定枠の保存未確認':'予定枠の保存記録あり').'</p>';
            foreach (['runs'=>['日次バックアップ（最新30件）',['日付','総合状態','保存完了','署名承認','復元結果']],
                      'attempts'=>['復元要求・後片付け履歴（最新30件）',['要求ID','日付','処理状態','結果','結果登録','後片付け']]] as $key=>$spec) {
                echo '<h2>'.esc_html($spec[0]).'</h2><div style="overflow-x:auto" tabindex="0" aria-label="'.esc_attr($spec[0]).'"><table class="widefat striped" style="min-width:760px"><thead><tr>';
                foreach ($spec[1] as $title) { echo '<th>'.esc_html($title).'</th>'; }
                echo '</tr></thead><tbody>';
                foreach ($v[$key] as $row) {
                    echo '<tr>';
                    foreach ($row as $field=>$value) {
                        $text=is_bool($value)?($value?'確認済み':'未確認'):(self::LABELS[$value] ?? $value);
                        echo '<td>'.esc_html($text).'</td>';
                    }
                    echo '</tr>';
                }
                echo '</tbody></table></div>';
                if (!$v[$key]) { echo '<p>記録はありません。</p>'; }
            }
        }
        echo '<p>後片付け確認済みは復元成功を意味しません。表示はローカル報告であり、独立した署名検証・本番再公開の承認ではありません。</p></div>';
    }
}
