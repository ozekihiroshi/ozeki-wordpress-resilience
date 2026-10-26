<?php
namespace Ozeki\Resilience;
require_once __DIR__ . '/ObserverAdmin.php';
require_once __DIR__ . '/ObserverSettings.php';

final class NotificationAdmin {
    const OPTION = 'owr_notification_settings_v1';
    const SLUG = 'owr-notifications';
    const KINDS = [
        'backup_missing'=>'バックアップ未取得', 'backup_failed'=>'バックアップ失敗',
        'backup_unknown'=>'取得結果不明', 'approval_pending'=>'署名承認待ち',
        'approval_expired'=>'承認期限切れ', 'restore_failed'=>'復元試験失敗',
        'restore_incomplete'=>'復元試験未完了', 'source_unreadable'=>'監視元の読取り失敗',
        'monitor_stopped'=>'監視停止', 'heartbeat_invalid'=>'生存記録不正',
        'notification_delivery_failed'=>'通知機能の異常',
    ];
    const PROVIDERS = ['pushover'=>'Pushover', 'smtp_starttls'=>'メール（STARTTLS）', 'smtp_tls'=>'メール（TLS）'];
    const PROBLEMS = ['channel_configuration_failed'=>'宛先の接続設定を確認してください',
        'delivery_rejected'=>'配送が拒否されました','delivery_unknown'=>'配送結果が不明です。再送前に照合が必要です',
        'delivery_backlog'=>'配送待ちが長期化しています','receipt_check_failed'=>'確認照会または取消に失敗しました',
        'ack_expired'=>'未確認のまま再通知期限が終了しました','ack_overdue'=>'人による確認を待っています'];

    static function boot(): void {
        ObserverSettings::boot();
        add_action('admin_post_owr_notification_test', [self::class,'testSend']);
        add_action('admin_menu', [self::class,'menu']);
        add_action('admin_post_owr_notification_save', [self::class,'save']);
        add_action('admin_post_owr_notification_export', [self::class,'export']);
    }
    static function menu(): void {
        add_menu_page('Resilience 通知', 'Resilience', 'manage_options', self::SLUG, [self::class,'render'], 'dashicons-shield');
        add_submenu_page(self::SLUG,'通知','通知','manage_options',self::SLUG,[self::class,'render']);
        add_submenu_page(self::SLUG,'独立watchdogの通知設定','独立watchdog','manage_options',ObserverSettings::SLUG,[ObserverSettings::class,'render']);
    }
    static function guard(bool $post = false): void {
        if (!current_user_can('manage_options')) { wp_die('この操作には管理者権限が必要です。','', ['response'=>403]); }
        if ($post && ($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') { wp_die('POSTが必要です。','',['response'=>405]); }
    }
    static function state(): array {
        $state = get_option(self::OPTION);
        if (!is_array($state)) {
            $new = ['format'=>'owr-notification-settings-v1','site_id'=>wp_generate_uuid4(),
                'revision'=>0,'revision_token'=>wp_generate_uuid4(),'channels'=>[], 'audit'=>[]];
            add_option(self::OPTION,$new,'',false);
            $state = get_option(self::OPTION);
        }
        return $state;
    }
    static function text($value, int $max = 100): string {
        if (!is_string($value) || strlen($value)>$max || preg_match('/[\x00-\x1f<>]/',$value)) { throw new \InvalidArgumentException('入力形式が正しくありません。'); }
        return trim($value);
    }
    static function channel(array $input, string $id): array {
        $name = self::text($input['label'] ?? '',160);
        $provider = self::text($input['provider'] ?? '');
        $profile = self::text($input['profile'] ?? '');
        $recipient = self::text($input['recipient'] ?? '',254);
        if ($name === '' || !isset(self::PROVIDERS[$provider]) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$profile)) {
            throw new \InvalidArgumentException('名前、対応する方式、接続設定名を指定してください。');
        }
        if ($provider !== 'pushover' && (!is_email($recipient) || strpbrk($recipient,"\r\n,; ") !== false)) {
            throw new \InvalidArgumentException('メール宛先を1件指定してください。');
        }
        if ($provider === 'pushover' && $recipient === '') { throw new \InvalidArgumentException('端末や受信者の表示名を指定してください。キーは入力しないでください。'); }
        $kinds = $input['kinds'] ?? [];
        if (!is_array($kinds) || !$kinds || count($kinds)>count(self::KINDS)) { throw new \InvalidArgumentException('対象警報を1つ以上選択してください。'); }
        foreach ($kinds as $kind) { if (!is_string($kind) || !isset(self::KINDS[$kind])) { throw new \InvalidArgumentException('未対応の警報です。'); } }
        if (count(array_unique($kinds))!==count($kinds)) { throw new \InvalidArgumentException('警報が重複しています。'); }
        sort($kinds);
        $enabled = $input['enabled'] ?? '0';
        if (!in_array($enabled,['0','1'],true)) { throw new \InvalidArgumentException('利用状態が不正です。'); }
        $result = compact('id','provider','profile','recipient','kinds') + ['label'=>$name,'enabled'=>$enabled==='1'];
        if ($provider==='pushover') {
            $retry = filter_var($input['retry'] ?? null,FILTER_VALIDATE_INT);
            $expire = filter_var($input['expire'] ?? null,FILTER_VALIDATE_INT);
            if ($retry===false || $expire===false || $retry<30 || $expire<$retry || $expire>10800) { throw new \InvalidArgumentException('再通知間隔は30秒以上、期限は間隔以上かつ10800秒以下にしてください。'); }
            $result['retry']=$retry;$result['expire']=$expire;
        }
        return $result;
    }
    static function save(): void {
        self::guard(true); check_admin_referer('owr_notification_save');
        global $wpdb;
        $old = self::state();
        try {
            $input = wp_unslash($_POST);
            if (!is_string($input['revision'] ?? null) || $input['revision'] !== (string)$old['revision']) { wp_die('別の操作で設定が更新されました。画面を再読込みしてください。','',['response'=>409]); }
            $id = self::text($input['channel_id'] ?? '');
            if ($id !== '' && !isset($old['channels'][$id])) { throw new \InvalidArgumentException('通知先が見つかりません。'); }
            if ($id === '') {
                if (count($old['channels'])>=20) { throw new \InvalidArgumentException('試作版は通知先20件までです。'); }
                $id = 'ch_' . str_replace('-','',wp_generate_uuid4());
            }
            $channel = self::channel($input,$id);
            $new = $old;$new['channels'][$id] = $channel;
            $new['revision']++;$new['revision_token']=wp_generate_uuid4();
            $new['audit'][]=['revision'=>$new['revision'],'actor'=>get_current_user_id(),'at'=>gmdate('c'),'channel_id'=>$id];
            // Compare-and-swap keeps simultaneous submissions from silently overwriting each other.
            $changed = $wpdb->query($wpdb->prepare("UPDATE {$wpdb->options} SET option_value=%s WHERE option_name=%s AND BINARY option_value=BINARY %s",
                maybe_serialize($new),self::OPTION,maybe_serialize($old)));
            if ($changed!==1) { wp_die('設定が競合しました。画面を再読込みしてください。','',['response'=>409]); }
            wp_cache_delete(self::OPTION,'options');wp_cache_delete('alloptions','options');
            wp_safe_redirect(admin_url('admin.php?page='.self::SLUG.'&saved=1'));exit;
        } catch (\InvalidArgumentException $e) { wp_die(esc_html($e->getMessage()),'', ['response'=>400]); }
    }
    static function testSend(): void {
        self::guard(true);
        $input=wp_unslash($_POST);
        $id=$input['request_id'] ?? '';
        if (!is_string($id) || !preg_match('/^[a-f0-9-]{36}$/D',$id)) { wp_die('要求IDが不正です。','',['response'=>400]); }
        check_admin_referer('owr_notification_test_'.$id);
        $state=self::state();$status=self::status($state);$channel=$input['channel_id'] ?? '';
        if (!is_string($channel) || empty($state['channels'][$channel]['enabled']) || $status['state']!=='connected' ||
            ($input['revision_token'] ?? '')!==$state['revision_token']) { wp_die('反映済みの有効な設定を再読込みしてください。','',['response'=>409]); }
        if (!defined('OWR_NOTIFICATION_REQUEST_DIR') || !is_dir(OWR_NOTIFICATION_REQUEST_DIR) || !is_writable(OWR_NOTIFICATION_REQUEST_DIR)) {
            wp_die('テスト送信の受付先は未接続です。','',['response'=>503]);
        }
        $dir=rtrim(OWR_NOTIFICATION_REQUEST_DIR,'/');
        $lock=fopen($dir.'/.request.lock','c');
        if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { wp_die('別の要求を処理中です。','',['response'=>409]); }
        try {
            $path=$dir.'/'.$id.'.json';
            if (!file_exists($path)) {
                $files=glob($dir.'/*.json');
                if ($files===false || count($files)>=100) { wp_die('受付記録が上限です。外部配送側で確認してください。','',['response'=>503]); }
                foreach($files as $file) {
                    if (filesize($file)>4096) { continue; }
                    $prior=json_decode((string)file_get_contents($file),true);
                    if (($prior['channel_id'] ?? '')===$channel && time()-($prior['created_at'] ?? 0)<60) { wp_die('同じ宛先のテストは60秒間隔です。','',['response'=>429]); }
                }
                $request=['request_id'=>$id,'channel_id'=>$channel,'site_id'=>$state['site_id'],
                    'revision'=>$state['revision'],'revision_token'=>$state['revision_token'],'created_at'=>time()];
                $tmp=tempnam($dir,'.pending-');
                if ($tmp===false || file_put_contents($tmp,wp_json_encode($request))===false || !chmod($tmp,0640) || !rename($tmp,$path)) {
                    if ($tmp && file_exists($tmp)) { unlink($tmp); }
                    wp_die('要求を保存できませんでした。','',['response'=>503]);
                }
            }
        } finally { flock($lock,LOCK_UN);fclose($lock); }
        wp_safe_redirect(admin_url('admin.php?page='.self::SLUG.'&test_requested=1'));exit;
    }

    static function export(): void {
        self::guard(true);check_admin_referer('owr_notification_export');
        $state = self::state();unset($state['audit']);
        $state['channels']=array_values($state['channels']);
        nocache_headers();header('Content-Type: application/json; charset=utf-8');
        header('Content-Disposition: attachment; filename="owr-notification-settings.json"');
        echo wp_json_encode($state,JSON_UNESCAPED_UNICODE|JSON_PRETTY_PRINT);exit;
    }
    static function status(array $settings): array {
        $unavailable = ['state'=>'unavailable','message'=>'外部配送の状態は未接続です。保存だけでは通知は有効になりません。'];
        if (!defined('OWR_NOTIFICATION_STATUS_FILE')) { return $unavailable; }
        $path = OWR_NOTIFICATION_STATUS_FILE;
        if (!is_string($path) || !is_readable($path) || !is_file($path) || filesize($path)>262144) { return $unavailable; }
        $data = json_decode((string)file_get_contents($path),true);
        if (!is_array($data) || ($data['format'] ?? '')!=='owr-notification-admin-status-v1' ||
            ($data['site_id'] ?? '')!==$settings['site_id'] || !is_string($data['completed_at'] ?? null) || !is_array($data['channels'] ?? null)) {
            return ['state'=>'invalid','message'=>'配送状態の形式または対象サイトを確認できません。'];
        }
        $stamp = strtotime($data['completed_at']);
        if ($stamp===false || $stamp>time()+5 || time()-$stamp>=900) { return ['state'=>'stale','message'=>'配送状態が古い、または時刻が不正です。外部監視を確認してください。']; }
        if (($data['revision_token'] ?? '')!==$settings['revision_token'] || ($data['revision'] ?? null)!==$settings['revision']) {
            return ['state'=>'pending','message'=>'保存した設定は外部配送へ未反映です。現在の配送設定を置き換えたとは扱いません。'];
        }
        $safe = [];
        $states=['pending'=>'配送待ち','retry'=>'再試行待ち','unknown'=>'結果不明','rejected'=>'配送拒否','accepted'=>'サービス受付','superseded'=>'解消済みのため送信省略'];
        foreach ($data['channels'] as $channel) {
            if (!is_array($channel) || !is_string($channel['id'] ?? null) || !isset($settings['channels'][$channel['id']]) || isset($safe[$channel['id']]) || !is_array($channel['counts'] ?? null) || !is_array($channel['problems'] ?? null) || !is_array($channel['receipts'] ?? null)) {
                return ['state'=>'invalid','message'=>'配送状態の通知先が一致しません。'];
            }
            foreach ($channel['counts'] as $key=>$count) { if (!isset($states[$key]) || !is_int($count) || $count<0) { return ['state'=>'invalid','message'=>'配送件数が不正です。']; } }
            foreach ($channel['receipts'] as $key=>$count) { if (!in_array($key,['waiting','acknowledged','expired','cancelled'],true) || !is_int($count) || $count<0) { return ['state'=>'invalid','message'=>'確認件数が不正です。']; } }
            foreach ($channel['problems'] as $problem) { if (!is_string($problem) || !isset(self::PROBLEMS[$problem])) { return ['state'=>'invalid','message'=>'未対応の配送異常です。']; } }
            $safe[$channel['id']] = ['counts'=>$channel['counts'],'receipts'=>$channel['receipts'],'problems'=>$channel['problems']];
        }
        $enabled = array_keys(array_filter($settings['channels'],fn($channel)=>$channel['enabled']));
        $present = array_keys($safe);sort($enabled);sort($present);
        if (array_diff($enabled,$present)) { return ['state'=>'invalid','message'=>'有効な通知先の状態が不足しています。']; }
        $tests=[];
        foreach(array_slice(is_array($data['tests'] ?? null)?$data['tests']:[],0,20) as $test) {
            if (is_array($test) && ($test['revision_token'] ?? '')===$settings['revision_token'] && is_string($test['channel_id'] ?? null) && isset($settings['channels'][$test['channel_id']]) &&
                in_array($test['status'] ?? '',['accepted','unknown','rejected','retry','blocked'],true)) {
                $tests[]=['channel_id'=>$test['channel_id'],'status'=>$test['status']];
            }
        }
        return ['tests'=>$tests,'state'=>'connected' ,'message'=>'外部配送の報告を受信しています。受付は端末での受信・人の確認を意味しません。',
            'completed_at'=>$data['completed_at'],'channels'=>$safe,'simulated'=>($data['simulated'] ?? true)!==false];
    }
    static function render(): void {
        self::guard();$state=self::state();$status=self::status($state);
        $edit = isset($_GET['edit']) && is_string($_GET['edit']) ? sanitize_key(wp_unslash($_GET['edit'])) : '';
        $channel=$state['channels'][$edit] ?? ['id'=>'','label'=>'','provider'=>'pushover','profile'=>'','recipient'=>'','enabled'=>false,'kinds'=>['backup_missing','restore_failed','approval_expired'],'retry'=>60,'expire'=>300];
        echo '<div class="wrap"><h1>Resilience — 通知</h1><p>重要警報はプッシュ、詳細・履歴はメールへ。通知先ごとに対象を選択できます。</p>';
        echo '<div class="notice notice-info inline" data-owr-development-scope="true"><p>開発・評価版です。このプラグインを有効化するだけではバックアップ・復元・監視・通知配送は開始しません。外部処理の配置と接続設定が必要です。</p></div>';
        echo '<div class="notice notice-info inline"><p>開発版：この画面は設定候補の保存と外部配送状態の表示を行います。保存時に外部送信や監視設定の切替は行いません。</p></div>';
        if (isset($_GET['saved'])) { echo '<div class="notice notice-success inline"><p>設定を保存しました。外部配送への反映と配信試験は別の手順です。</p></div>'; }
        ObserverAdmin::render($state);
        echo '<h2>配送状態</h2><p data-status="'.esc_attr($status['state']).'">'.esc_html($status['message']).'</p>';
        if (isset($status['completed_at'])) { echo '<p>最終完了：'.esc_html($status['completed_at']).($status['simulated']?' ／ 専用環境・模擬配送':'').'</p>'; }
        if(isset($_GET['test_requested'])){echo '<div class="notice notice-info inline"><p>テスト要求を保存しました。外部配送の処理待ちです。送信成功とは扱いません。</p></div>';}
        $covered=[];foreach($state['channels'] as $c){if($c['enabled']){$covered=array_merge($covered,$c['kinds']);}}
        if (array_diff(['backup_missing','restore_failed','approval_expired'],$covered)) { echo '<div class="notice notice-warning inline"><p>重要警報の通知先が未選択、または無効です。通知できる構成とは扱いません。</p></div>'; }
        echo '<h2>通知先</h2><div tabindex="0" aria-label="通知先一覧" style="max-width:100%;overflow-x:auto"><table class="widefat striped" style="min-width:640px"><thead><tr><th>名前・宛先</th><th>方式・利用状態</th><th>対象警報</th><th>配送結果（旧設定分を含む）</th><th>操作</th></tr></thead><tbody>';
        foreach($state['channels'] as $c){
            echo '<tr><td>'.esc_html($c['label']).'<br>'.esc_html($c['recipient']).'</td><td>'.esc_html(self::PROVIDERS[$c['provider']]).'<br>'.($c['enabled']?'利用希望：有効':'無効').'</td><td>';
            echo esc_html(implode('、',array_map(fn($k)=>self::KINDS[$k],$c['kinds']))).'</td><td>';
            $delivery=$status['channels'][$c['id']] ?? null;
            if($delivery){
                foreach($delivery['counts'] as $key=>$count){echo esc_html(['pending'=>'配送待ち','retry'=>'再試行待ち','unknown'=>'結果不明','rejected'=>'配送拒否','accepted'=>'サービス受付','superseded'=>'送信省略'][$key].': '.$count).'<br>';}
                foreach($delivery['receipts'] as $key=>$count){echo esc_html(['waiting'=>'確認待ち','acknowledged'=>'人による確認済み','expired'=>'確認期限切れ','cancelled'=>'再通知取消済み'][$key].': '.$count).'<br>';}
                foreach($delivery['problems'] as $problem){echo '<strong>'.esc_html(self::PROBLEMS[$problem]).'</strong><br>';}
                if(!$delivery['counts']){echo '配送記録なし';}
            }else{echo '外部配送の反映・確認待ち';}
            echo '</td><td><a href="'.esc_url(admin_url('admin.php?page='.self::SLUG.'&edit='.$c['id'])).'">編集</a></td></tr>';
        }
        if(!$state['channels']){echo '<tr><td colspan="5">通知先はまだ登録されていません。</td></tr>';}
        echo '</tbody></table></div><h2>'.($channel['id']?'通知先を編集':'通知先を追加').'</h2><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        wp_nonce_field('owr_notification_save');
        echo '<input type="hidden" name="action" value="owr_notification_save"><input type="hidden" name="revision" value="'.esc_attr((string)$state['revision']).'"><input type="hidden" name="channel_id" value="'.esc_attr($channel['id']).'">';
        echo '<table class="form-table"><tbody>';
        foreach(['label'=>'通知先の名前','profile'=>'接続設定名','recipient'=>'宛先メール／Pushoverの受信者表示名'] as $field=>$label){
            echo '<tr><th><label for="owr-'.$field.'">'.esc_html($label).'</label></th><td><input class="regular-text" required id="owr-'.$field.'" name="'.$field.'" value="'.esc_attr($channel[$field]).'" maxlength="'.($field==='recipient'?'254':($field==='label'?'160':'64')).'">';
            if($field==='profile'){echo '<p class="description">外部配送側に登録する接続設定の名前（英数字・_・-）。APIキーやパスワードはこの画面に入力しません。</p>';}
            echo '</td></tr>';
        }
        echo '<tr><th><label for="owr-provider">通知方式</label></th><td><select id="owr-provider" name="provider">';
        foreach(self::PROVIDERS as $key=>$label){echo '<option value="'.esc_attr($key).'" '.selected($channel['provider'],$key,false).'>'.esc_html($label).'</option>';}
        echo '</select><p class="description">LINE・Slack・PagerDutyは今後の対応です。</p></td></tr><tr><th>対象警報</th><td><fieldset><legend class="screen-reader-text">対象警報を選択</legend>';
        foreach(self::KINDS as $key=>$label){echo '<label style="display:block;margin-bottom:6px"><input type="checkbox" name="kinds[]" value="'.esc_attr($key).'" '.checked(in_array($key,$channel['kinds'],true),true,false).'> '.esc_html($label).'</label>';}
        echo '</fieldset></td></tr><tr><th>利用状態</th><td><label><input type="checkbox" name="enabled" value="1" '.checked($channel['enabled'],true,false).'>外部配送でこの通知先を利用する</label><p class="description">無効化は新しい警報への利用を止めます。旧設定の未配送・確認・取消処理と記録は保持します。</p></td></tr>';
        foreach(['retry'=>'Pushover 再通知間隔（秒）','expire'=>'Pushover 再通知期限（秒）'] as $field=>$label){echo '<tr><th><label for="owr-'.$field.'">'.esc_html($label).'</label></th><td><input type="number" id="owr-'.$field.'" name="'.$field.'" min="30" max="10800" value="'.esc_attr((string)($channel[$field] ?? ($field==='retry'?60:300))).'"><p class="description">メールでは使用しません。</p></td></tr>';}
        echo '</tbody></table>';submit_button('設定候補を保存');echo '</form>';
        if($channel['id']){echo '<p><a href="'.esc_url(admin_url('admin.php?page='.self::SLUG)).'">新しい通知先を追加</a></p>';}
        echo '<h2>外部配送との接続</h2><p>設定版 '.esc_html((string)$state['revision']).'。接続設定の秘密情報は外部監視側で管理します。設定候補をエクスポートし、外部側で適用・試験してください。既存の未配送記録を削除して切り替えないでください。</p><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
        wp_nonce_field('owr_notification_export');echo '<input type="hidden" name="action" value="owr_notification_export">';submit_button('設定候補をエクスポート','secondary');echo '</form>';
        echo '<h2>テスト送信</h2><p>反映済みの通知先へ通常優先度で送信します。外部配送側が処理した後に画面を再読込みしてください。受付後も端末で受信を確認してください。</p>';
        if($status['state']==='connected' && defined('OWR_NOTIFICATION_REQUEST_DIR')) {
            foreach($state['channels'] as $c) {
                if(!$c['enabled']){continue;}$request=wp_generate_uuid4();
                echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';
                wp_nonce_field('owr_notification_test_'.$request);
                foreach(['action'=>'owr_notification_test','request_id'=>$request,'channel_id'=>$c['id'],'revision_token'=>$state['revision_token']] as $key=>$value){echo '<input type="hidden" name="'.esc_attr($key).'" value="'.esc_attr($value).'">';}
                submit_button($c['label'].'へテスト送信','secondary');echo '</form>';
            }
        }else{echo '<p>設定の反映またはテスト受付先の接続を待っています。</p>';}
        foreach($status['tests'] ?? [] as $test){echo '<p>'.esc_html($state['channels'][$test['channel_id']]['label'].'：'.['accepted'=>'テスト：サービス受付（端末で確認してください）','unknown'=>'テスト：結果不明・自動再送なし','rejected'=>'テスト：拒否','retry'=>'テスト：一時失敗・自動再送なし','blocked'=>'テスト：期限・設定版・頻度の確認が必要'][$test['status']]).'</p>';}
        echo '<h2>変更履歴</h2><ul>';foreach(array_reverse(array_slice($state['audit'],-10)) as $entry){echo '<li>'.esc_html('設定版 '.$entry['revision'].' ／ '.$entry['at'].' ／ 管理者ID '.$entry['actor']).'</li>';}
        echo '</ul></div>';
    }
}
