<?php
namespace Ozeki\Resilience;

final class ObserverSettings {
    const OPTION='owr_observer_settings_v1';
    const SLUG='owr-observer-settings';
    const KINDS=['monitor_stopped'=>'watchdog・監視ホストの停止／期限超過','heartbeat_invalid'=>'生存記録の不正','notification_delivery_failed'=>'監視側の通知異常'];
    static function boot(): void {
        add_action('admin_post_owr_observer_test',[self::class,'testSend']);
        add_action('admin_post_owr_observer_save',[self::class,'save']);
        add_action('admin_post_owr_observer_apply',[self::class,'apply']);
    }
    static function state(): array {
        $state=get_option(self::OPTION);
        if (!is_array($state)) {
            add_option(self::OPTION,['format'=>'owr-notification-settings-v1','site_id'=>NotificationAdmin::state()['site_id'],'revision'=>0,'revision_token'=>wp_generate_uuid4(),'channels'=>[]],'',false);
            $state=get_option(self::OPTION);
        }
        return $state;
    }
    static function configuration(array $c): array {
        if (!is_string($c['active_hash'] ?? null) || !preg_match('/^[a-f0-9]{64}$/D',$c['active_hash']) || !is_string($c['revision_token'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{0,64}$/D',$c['revision_token']) || !is_bool($c['processing_error'] ?? false)) { throw new \InvalidArgumentException(); }
        $clean=['active_hash'=>$c['active_hash'],'revision'=>ObserverAdmin::count($c['revision'] ?? null),'revision_token'=>$c['revision_token'],'processing_error'=>$c['processing_error'] ?? false,'last_request'=>null];
        if (!is_bool($c['test_processing_error'] ?? false) || !is_array($c['tests'] ?? []) || count($c['tests'] ?? [])>20) { throw new \InvalidArgumentException(); }
        $clean['test_processing_error']=$c['test_processing_error'] ?? false;$clean['tests']=[];
        foreach ($c['tests'] ?? [] as $r) {
            if (!is_array($r) || !is_string($r['request_id'] ?? null) || !preg_match('/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/D',$r['request_id']) || !is_string($r['channel_id'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$r['channel_id']) || !is_string($r['revision_token'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$r['revision_token']) || !in_array($r['status'] ?? null,['accepted','unknown','rejected','retry','blocked'],true)) { throw new \InvalidArgumentException(); }
            ObserverAdmin::count($r['revision'] ?? null);$clean['tests'][]=array_intersect_key($r,array_flip(['request_id','channel_id','revision','revision_token','status']));
        }
        if (isset($c['last_request'])) {
            $r=$c['last_request'];
            if (!is_array($r) || !is_string($r['request_id'] ?? null) || !preg_match('/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/D',$r['request_id']) || !is_string($r['revision_token'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D',$r['revision_token']) || !in_array($r['outcome'] ?? null,['applied','rejected','conflict'],true) || !in_array($r['reason'] ?? null,['applied','policy','expired','conflict'],true)) { throw new \InvalidArgumentException(); }
            ObserverAdmin::count($r['revision'] ?? null);$clean['last_request']=array_intersect_key($r,array_flip(['request_id','revision','revision_token','outcome','reason']));
        }
        return $clean;
    }
    static function save(): void {
        NotificationAdmin::guard(true);check_admin_referer('owr_observer_save');global $wpdb;
        $old=self::state();$input=wp_unslash($_POST);
        if (($input['revision'] ?? null)!==(string)$old['revision']) { wp_die('設定が競合しました。再読込みしてください。','',['response'=>409]); }
        try {
            $id=NotificationAdmin::text($input['channel_id'] ?? '');
            if ($id!=='' && !isset($old['channels'][$id])) { throw new \InvalidArgumentException('通知先が見つかりません。'); }
            if ($id==='') {
                if (count($old['channels'])>=10) { throw new \InvalidArgumentException('通知先は10件までです。'); }
                $id='ch_'.str_replace('-','',wp_generate_uuid4());
            }
            $channel=NotificationAdmin::channel($input,$id);
            if (array_diff($channel['kinds'],array_keys(self::KINDS))) { throw new \InvalidArgumentException('独立watchdogの警報を選択してください。'); }
            $new=$old;$new['channels'][$id]=$channel;$new['revision']++;$new['revision_token']=wp_generate_uuid4();
            $changed=$wpdb->query($wpdb->prepare("UPDATE {$wpdb->options} SET option_value=%s WHERE option_name=%s AND BINARY option_value=BINARY %s",maybe_serialize($new),self::OPTION,maybe_serialize($old)));
            if ($changed!==1) { wp_die('設定が競合しました。再読込みしてください。','',['response'=>409]); }
            wp_cache_delete(self::OPTION,'options');wp_cache_delete('alloptions','options');
            wp_safe_redirect(admin_url('admin.php?page='.self::SLUG.'&saved=1'));exit;
        } catch (\InvalidArgumentException $e) { wp_die(esc_html($e->getMessage()),'',['response'=>400]); }
    }
    static function apply(): void {
        NotificationAdmin::guard(true);$input=wp_unslash($_POST);$rid=$input['request_id'] ?? '';
        if (!is_string($rid) || !preg_match('/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/D',$rid)) { wp_die('要求IDが不正です。','',['response'=>400]); }
        check_admin_referer('owr_observer_apply_'.$rid);
        $state=self::state();$report=ObserverAdmin::status(NotificationAdmin::state());$c=$report['configuration'] ?? null;
        if (!$state['channels'] || $report['state']!=='current' || !$c || ($input['revision_token'] ?? null)!==$state['revision_token'] || ($input['expected_hash'] ?? null)!==$c['active_hash']) { wp_die('最新の設定と外部状態を再読込みしてください。','',['response'=>409]); }
        $created=filter_var($input['created_at'] ?? null,FILTER_VALIDATE_INT);
        if ($created===false || $created>time()+5 || time()-$created>300) { wp_die('要求の時刻が古いか不正です。再読込みしてください。','',['response'=>409]); }
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_is_writable -- Local worker queue protocol; no installation or remote filesystem writes.
        if (!defined('OWR_OBSERVER_REQUEST_DIR') || !is_dir(OWR_OBSERVER_REQUEST_DIR) || !is_writable(OWR_OBSERVER_REQUEST_DIR)) { wp_die('独立watchdogの設定受付先は未接続です。','',['response'=>503]); }
        $settings=$state;$settings['channels']=array_values($settings['channels']);
        $request=['format'=>'owr-observer-settings-request-v1','request_id'=>$rid,'expected_hash'=>$c['active_hash'],'created_at'=>$created,'settings'=>$settings];
        $raw=wp_json_encode($request,JSON_UNESCAPED_SLASHES);
        if (strlen($raw)>4096) { wp_die('設定要求は4KBまでです。通知先数や表示名を減らしてください。','',['response'=>400]); }
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Local worker queue protocol; no installation or remote filesystem writes.
        $dir=rtrim(OWR_OBSERVER_REQUEST_DIR,'/');$lock=fopen($dir.'/.request.lock','c');
        if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { wp_die('別の要求を処理中です。','',['response'=>409]); }
        try {
            $path=$dir.'/'.$rid.'.json';
            if (file_exists($path)) {
                if (is_link($path) || file_get_contents($path)!==$raw) { wp_die('要求が競合しました。','',['response'=>409]); }
            } else {
                $files=glob($dir.'/*.json');
                if ($files===false || count($files)>=100) { wp_die('設定要求が上限です。転送処理を確認してください。','',['response'=>503]); }
                $tmp=tempnam($dir,'.pending-');
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod,WordPress.WP.AlternativeFunctions.rename_rename,WordPress.WP.AlternativeFunctions.unlink_unlink -- Local worker queue protocol; no installation or remote filesystem writes.
                if ($tmp===false || file_put_contents($tmp,$raw)===false || !chmod($tmp,0640) || !rename($tmp,$path)) { if ($tmp && file_exists($tmp)) { unlink($tmp); }wp_die('要求を保存できませんでした。','',['response'=>503]); }
            }
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Local worker queue protocol; no installation or remote filesystem writes.
        } finally { flock($lock,LOCK_UN);fclose($lock); }
        wp_safe_redirect(admin_url('admin.php?page='.self::SLUG.'&requested=1'));exit;
    }
    static function testSend(): void {
        NotificationAdmin::guard(true);$input=wp_unslash($_POST);$rid=$input['request_id'] ?? '';
        if (!is_string($rid) || !preg_match('/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/D',$rid)) { wp_die('要求IDが不正です。','',['response'=>400]); }
        check_admin_referer('owr_observer_test_'.$rid);
        $state=self::state();$report=ObserverAdmin::status(NotificationAdmin::state());$config=$report['configuration'] ?? null;$channel=$input['channel_id'] ?? '';
        if ($report['state']!=='current' || !$config || $config['processing_error'] || $config['test_processing_error'] || $config['revision']!==$state['revision'] || $config['revision_token']!==$state['revision_token'] || ($input['revision_token'] ?? null)!==$state['revision_token'] || ($input['expected_hash'] ?? null)!==$config['active_hash'] || !is_string($channel) || empty($state['channels'][$channel]['enabled'])) { wp_die('反映済みの有効な設定と最新の外部状態を確認してください。','',['response'=>409]); }
        $created=filter_var($input['created_at'] ?? null,FILTER_VALIDATE_INT);
        if ($created===false || $created>time()+5 || time()-$created>300) { wp_die('要求の時刻が古いか不正です。','',['response'=>409]); }
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_is_writable -- Local worker queue protocol; no installation or remote filesystem writes.
        if (!defined('OWR_OBSERVER_REQUEST_DIR') || !is_dir(OWR_OBSERVER_REQUEST_DIR) || !is_writable(OWR_OBSERVER_REQUEST_DIR)) { wp_die('独立watchdogの受付先は未接続です。','',['response'=>503]); }
        $request=['format'=>'owr-observer-test-request-v1','site_id'=>$state['site_id'],'request_id'=>$rid,'channel_id'=>$channel,'created_at'=>$created,'revision'=>$state['revision'],'revision_token'=>$state['revision_token'],'expected_hash'=>$config['active_hash']];
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- Local worker queue protocol; no installation or remote filesystem writes.
        $raw=wp_json_encode($request,JSON_UNESCAPED_SLASHES);$dir=rtrim(OWR_OBSERVER_REQUEST_DIR,'/');$lock=fopen($dir.'/.request.lock','c');
        if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) { wp_die('別の要求を処理中です。','',['response'=>409]); }
        try {
            $path=$dir.'/'.$rid.'.json';
            if (file_exists($path)) {
                if (is_link($path) || file_get_contents($path)!==$raw) { wp_die('要求が競合しました。','',['response'=>409]); }
            } else {
                $ratepath=$dir.'/.test-rate';$rates=[];
                if (file_exists($ratepath)) {
                    if (is_link($ratepath)) { wp_die('頻度管理の記録を確認してください。','',['response'=>503]); }
                    $rates=json_decode((string)file_get_contents($ratepath,false,null,0,8193),true);
                    if (!is_array($rates)) { wp_die('頻度管理の記録を確認してください。','',['response'=>503]); }
                    foreach ($rates as $key=>$stamp) { if (!is_int($stamp)) { wp_die('頻度管理の記録を確認してください。','',['response'=>503]); }if (time()-$stamp>=60) { unset($rates[$key]); } }
                }
                if (isset($rates[$channel]) && time()-$rates[$channel]<60) { wp_die('同じ通知先のテストは60秒間隔です。','',['response'=>429]); }
                $files=glob($dir.'/*.json');
                if ($files===false || count($files)>=100) { wp_die('受付記録が上限です。','',['response'=>503]); }
                $rates[$channel]=time();$tmp=tempnam($dir,'.rate-');
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod,WordPress.WP.AlternativeFunctions.rename_rename,WordPress.WP.AlternativeFunctions.unlink_unlink -- Local worker queue protocol; no installation or remote filesystem writes.
                if ($tmp===false || file_put_contents($tmp,wp_json_encode($rates))===false || !chmod($tmp,0640) || !rename($tmp,$ratepath)) { if ($tmp && file_exists($tmp)) { unlink($tmp); }wp_die('頻度管理を保存できませんでした。','',['response'=>503]); }
                $tmp=tempnam($dir,'.pending-');
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod,WordPress.WP.AlternativeFunctions.rename_rename,WordPress.WP.AlternativeFunctions.unlink_unlink -- Local worker queue protocol; no installation or remote filesystem writes.
                if ($tmp===false || file_put_contents($tmp,$raw)===false || !chmod($tmp,0640) || !rename($tmp,$path)) { if ($tmp && file_exists($tmp)) { unlink($tmp); }wp_die('テスト要求を保存できませんでした。','',['response'=>503]); }
            }
        // Local private IPC requires OS locks, exact permissions and atomic same-filesystem rename; FTP-backed WP_Filesystem cannot preserve this contract.
        // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- Local worker queue protocol; no installation or remote filesystem writes.
        } finally { flock($lock,LOCK_UN);fclose($lock); }
        wp_safe_redirect(admin_url('admin.php?page='.self::SLUG.'&test_id='.$rid));exit;
    }
    static function renderTests(array $state,array $report): void {
        $c=$report['configuration'] ?? null;
        echo '<h2>独立watchdogのテスト送信</h2><p>反映済みの通知先へ固定のテスト本文を通常優先度で送信します。同じ通知先は60秒間隔です。サービス受付後も端末で受信を確認してください。</p>';
        if (($report['delivery']['state'] ?? '')==='failed') { echo '<p data-observer-delivery="failed">通常警報の配送に異常があります。テスト送信がサービス受付になっていても、通常警報の配送成功を意味しません。Resilience → 通知で詳細を確認してください。</p>'; }
        if ($c && $c['test_processing_error']) { echo '<p>外部のテスト処理に異常があります。通常の監視・警報配送と分けて確認してください。</p>'; }
        $ready=$report['state']==='current' && $c && !$c['processing_error'] && !$c['test_processing_error'] && $c['revision']===$state['revision'] && $c['revision_token']===$state['revision_token'];
        if ($ready && defined('OWR_OBSERVER_REQUEST_DIR')) {
            foreach ($state['channels'] as $channel) {
                if (!$channel['enabled']) { continue; }$rid=wp_generate_uuid4();
                echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';wp_nonce_field('owr_observer_test_'.$rid);
                foreach (['action'=>'owr_observer_test','request_id'=>$rid,'channel_id'=>$channel['id'],'created_at'=>(string)time(),'revision_token'=>$state['revision_token'],'expected_hash'=>$c['active_hash']] as $k=>$v) { echo '<input type="hidden" name="'.esc_attr($k).'" value="'.esc_attr($v).'">'; }
                submit_button($channel['label'].'へテスト送信','secondary');echo '</form>';
            }
        } else { echo '<p>設定の反映と最新の外部状態・受付先の接続を待っています。</p>'; }
        $tests=$c['tests'] ?? [];$rid=$_GET['test_id'] ?? '';
        if (is_string($rid) && preg_match('/^[a-f0-9-]{36}$/D',$rid) && !in_array($rid,array_column($tests,'request_id'),true)) { echo '<p data-observer-test="pending">この要求の配送結果はまだ報告されていません。受付は送信成功を意味しません。</p>'; }
        if ($report['state']!=='current') { echo '<p>現在の外部状態は未確認です。以下に記録がある場合も前回報告の履歴です。</p>'; }
        echo '<h3>最近のテスト結果（最大20件）</h3><ul>';
        foreach ($tests as $r) {
            $label=$state['channels'][$r['channel_id']]['label'] ?? '旧通知先';
            $text=['accepted'=>'サービス受付（端末で確認してください）','unknown'=>'結果不明・自動再送なし','rejected'=>'配送拒否・自動再送なし','retry'=>'一時失敗・自動再送なし','blocked'=>'未送信（期限・設定版・有効状態・頻度を確認）'][$r['status']];
            echo '<li data-observer-test="'.esc_attr($r['status']).'">'.esc_html($label.' ／ 設定版 '.$r['revision'].' ／ '.$text.' ／ 要求 '.$r['request_id']).'</li>';
        }
        if (!$tests) { echo '<li>配送結果の報告はまだありません。</li>'; }echo '</ul>';
    }
    static function render(): void {
        NotificationAdmin::guard();$state=self::state();$report=ObserverAdmin::status(NotificationAdmin::state());$config=$report['configuration'] ?? null;
        $id=isset($_GET['edit']) && is_string($_GET['edit'])?sanitize_key(wp_unslash($_GET['edit'])):'';
        $channel=$state['channels'][$id] ?? ['id'=>'','label'=>'','provider'=>'pushover','profile'=>'','recipient'=>'','enabled'=>true,'kinds'=>array_keys(self::KINDS),'retry'=>60,'expire'=>1800];
        echo '<div class="wrap"><h1>独立watchdogの通知設定</h1><p>保存した設定を外部観測側へ反映要求します。未配送・確認待ち・取消処理は旧宛先とともに保持し、切替後の新しい警報から新設定を使います。</p>';
        if (isset($_GET['saved'])) { echo '<p>設定候補を保存しました。外部側にはまだ反映していません。</p>'; }
        if (isset($_GET['requested'])) { echo '<p>反映要求を保存しました。転送・外部処理待ちです。反映完了とは扱いません。</p>'; }
        $applied=$report['state']==='current' && $config && $config['revision_token']===$state['revision_token'] && $config['revision']===$state['revision'];
        echo '<p data-observer-settings="'.($applied?'applied':'pending').'">'.($applied?'この設定版は外部側に反映済みです。':'この設定版の反映は未確認です。').' 設定候補版：'.esc_html((string)$state['revision']).'</p>';
        if ($report['state']!=='current') { echo '<p>外部状態が未取得・不正または古いため、反映要求はできません。</p>'; }
        if ($config) {
            echo '<p>外部の設定版：'.esc_html((string)$config['revision']).'</p>';
            if ($config['processing_error']) { echo '<p>外部の設定受付処理に異常があります。従来の通知設定で処理を継続します。</p>'; }
            if ($config['last_request']) { $r=$config['last_request'];echo '<p data-apply-outcome="'.esc_attr($r['outcome']).'">'.esc_html('直近の要求：設定版 '.$r['revision'].' ／ '.['applied'=>'反映済み','policy'=>'外部の許可条件に合わず拒否','expired'=>'要求の期限切れ','conflict'=>'外部設定との競合'][$r['reason']]).'</p>'; }
        }
        echo '<table class="widefat striped"><thead><tr><th>通知先</th><th>方式・利用状態</th><th>対象警報</th><th>操作</th></tr></thead><tbody>';
        foreach ($state['channels'] as $c) { echo '<tr><td>'.esc_html($c['label']).'<br>'.esc_html($c['recipient']).'</td><td>'.esc_html(NotificationAdmin::PROVIDERS[$c['provider']]).' ／ '.($c['enabled']?'有効候補':'無効候補').'</td><td>'.esc_html(implode('、',array_map(fn($k)=>self::KINDS[$k],$c['kinds']))).'</td><td><a href="'.esc_url(admin_url('admin.php?page='.self::SLUG.'&edit='.$c['id'])).'">編集</a></td></tr>'; }
        if (!$state['channels']) { echo '<tr><td colspan="4">通知先は未登録です。外部の既存設定は自動で取り込みません。</td></tr>'; }
        echo '</tbody></table><h2>'.($channel['id']?'通知先を編集':'通知先を追加').'</h2><form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';wp_nonce_field('owr_observer_save');
        foreach (['action'=>'owr_observer_save','revision'=>(string)$state['revision'],'channel_id'=>$channel['id']] as $k=>$v) { echo '<input type="hidden" name="'.esc_attr($k).'" value="'.esc_attr($v).'">'; }
        foreach (['label'=>'通知先名','profile'=>'外部で登録済みの接続設定名','recipient'=>'メール宛先／Pushover受信者の表示名'] as $k=>$label) { echo '<p><label>'.esc_html($label).'<br><input class="regular-text" required name="'.esc_attr($k).'" value="'.esc_attr($channel[$k]).'"></label></p>'; }
        echo '<p>APIキー・パスワードは入力しません。外部側で許可された接続設定・メール宛先だけを利用できます。</p><p><label>通知方式 <select name="provider">';
        foreach (NotificationAdmin::PROVIDERS as $k=>$label) { echo '<option value="'.esc_attr($k).'" '.selected($channel['provider'],$k,false).'>'.esc_html($label).'</option>'; }
        echo '</select></label></p><fieldset><legend>対象警報</legend>';
        foreach (self::KINDS as $k=>$label) { echo '<p><label><input type="checkbox" name="kinds[]" value="'.esc_attr($k).'" '.checked(in_array($k,$channel['kinds'],true),true,false).'>'.esc_html($label).'</label></p>'; }
        echo '</fieldset><p><label><input type="checkbox" name="enabled" value="1" '.checked($channel['enabled'],true,false).'>この通知先を有効にする</label></p>';
        foreach (['retry'=>'Pushover再通知間隔（秒）','expire'=>'Pushover再通知期限（秒）'] as $k=>$label) { echo '<p><label>'.esc_html($label).' <input type="number" min="30" max="10800" name="'.esc_attr($k).'" value="'.esc_attr((string)($channel[$k] ?? ($k==='retry'?60:1800))).'"></label></p>'; }
        submit_button('独立watchdogの設定候補を保存');echo '</form><p><a href="'.esc_url(admin_url('admin.php?page='.self::SLUG)).'">新しい通知先を追加</a></p><h2>外部側へ反映</h2><p>必須警報の通知先がなくなる変更や、外部ルールに合わない宛先は拒否されます。反映結果は状態取得後に再読込みして確認してください。通常の通知設定は変更しません。</p>';
        if ($state['channels'] && $report['state']==='current' && $config && defined('OWR_OBSERVER_REQUEST_DIR')) {
            $rid=wp_generate_uuid4();echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';wp_nonce_field('owr_observer_apply_'.$rid);
            foreach (['action'=>'owr_observer_apply','request_id'=>$rid,'created_at'=>(string)time(),'revision_token'=>$state['revision_token'],'expected_hash'=>$config['active_hash']] as $k=>$v) { echo '<input type="hidden" name="'.esc_attr($k).'" value="'.esc_attr($v).'">'; }
            submit_button('外部側へ反映を要求','secondary');echo '</form>';
        }
        self::renderTests($state,$report);echo '</div>';
    }
}
