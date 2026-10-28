<?php
declare(strict_types=1);
namespace Owr\M1;
if (!defined('ABSPATH')) exit;
require_once __DIR__.'/AdminText.php';

/** Read-only preparation checks; actual capture still verifies every stored resource. */
final class SetupReadiness
{
    public const TERMS = '2026-10-28';
    public static function text(string $en, string $ja): string {
        return str_starts_with((string)determine_locale(), 'ja') ? $ja : $en;
    }
    public static function identity(array $c): string {
        return hash('sha256', json_encode(array_map(static fn($k)=>(string)($c[$k]??''), ['bucket','region','prefix','owner']), JSON_THROW_ON_ERROR));
    }
    public static function configured(array $c): bool {
        return !empty($c['bucket']) && !empty($c['region']) && !empty($c['prefix']);
    }
    public static function accepted(array $c): bool {
        // Previously configured installations already authorized this storage service.
        return self::configured($c) && (!isset($c['setup_version']) || ($c['terms_version']??'')===self::TERMS);
    }
    public static function local(): array {
        global $wpdb, $wp_version;
        $rows=[];
        $add=static function($id,$ok,$label,$next)use(&$rows){$rows[$id]=['ok'=>$ok,'label'=>$label,'next'=>$ok?self::text('No action needed.','対応は不要です。'):$next];};
        $add('runtime',version_compare($wp_version,'6.4','>=')&&version_compare(PHP_VERSION,'8.1','>='), 'WordPress '.$wp_version.' / PHP '.PHP_VERSION,
            self::text('Server administrator: update to WordPress 6.4+ and PHP 8.1+.','サーバー管理者：WordPress 6.4以上・PHP 8.1以上へ更新してください。'));
        $add('zip',class_exists('ZipArchive'),self::text('ZIP support','ZIPを扱う機能'),self::text('Server administrator: enable the PHP zip extension.','サーバー管理者：PHPのzip拡張を有効にしてください。'));
        $add('temporary',is_dir(sys_get_temp_dir())&&is_writable(sys_get_temp_dir()),self::text('Temporary save directory','保存用の一時作業場所'),self::text('Server administrator: allow web PHP to write to its temporary directory.','サーバー管理者：PHPの一時フォルダーへの書き込みを許可してください。'));
        $bad=[];
        foreach([$wpdb->posts,$wpdb->postmeta,$wpdb->options] as $table){
            $engine=$wpdb->get_var($wpdb->prepare('SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s',$table));
            if(strtolower((string)$engine)!=='innodb')$bad[]=$table;
        }
        $add('database',!$bad,self::text('Database preparation','データベースの準備'),self::text('Server administrator: check InnoDB for these tables: ','サーバー管理者：次のテーブルをInnoDBで使用できるか確認してください：').implode(', ',$bad));
        $markdown=(bool)$wpdb->get_var("SELECT ID FROM {$wpdb->posts} WHERE post_type='ozmd_document' LIMIT 1") || (bool)$wpdb->get_var("SELECT meta_id FROM {$wpdb->postmeta} WHERE meta_key='_ozmd_source' LIMIT 1");
        $active=(array)get_option('active_plugins',[]);
        $add('markdown',!$markdown||in_array('ozeki-markdown-documents/ozeki-markdown-documents.php',$active,true),'Ozeki Markdown Documents',self::text('WordPress administrator: activate Ozeki Markdown Documents to preserve existing Markdown content.','WordPress管理者：既存のMarkdown文書を保存するため、Ozeki Markdown Documentsを有効にしてください。'));
        if(!$markdown)$rows['markdown']['unused']=true;
        $add('pending',!get_option('owr_m1_pending')&&!get_option('owr_m1_comment_pending'),self::text('Unfinished saves','未完了の保存'),self::text('WordPress administrator: resolve the storage error, then use Resume history.','WordPress管理者：保存先のエラーを解消し、「未完了の保存を再開」を押してください。'));
        return $rows;
    }
    public static function requireLocal(): void {
        foreach(self::local() as $row)if(!$row['ok'])throw new \RuntimeException($row['next']);
    }
    public static function baseline(array $c): bool {
        $b=(array)get_option('owr_setup_baseline',[]);
        return ($b['identity']??'')===self::identity($c) && !empty($b['manifest']);
    }
    public static function requireStart(array $c): void {
        self::requireLocal();
        if(($c['setup_role']??'source')!=='source')throw new \RuntimeException(self::text('Choose Protect this site before starting protection.','保護を開始する場合は「このサイトを保護」を選択してください。'));
        if(!self::baseline($c))throw new \RuntimeException(self::text('Create a complete initial snapshot for this storage destination before starting protection.','この保存先への最初の保存を完了してから、保護を開始してください。'));
    }
    public static function storageNext(array $c): string {
        if(($c['setup_role']??'source')==='recovery')return self::text('Select an existing Checkpoint under Site-wide recovery.','「初期保存とサイト全体の復旧」で既存の復旧ポイントを選択してください。');
        if(!self::baseline($c))return self::text('Create the first snapshot under Site-wide recovery.','「最初の保存を作成」へ進んでください。');
        return !empty($c['protect'])?self::text('No action needed.','対応は不要です。'):self::text('Enable Protect supported operations in storage settings.','保存先設定の「保護を開始する」を有効にしてください。');
    }
    public static function render(array $c): void {
        $t=[self::class,'text'];
        echo '<section id="owr-setup"><h2>'.esc_html($t('Preparation for protection','保護開始までの準備状況')).'</h2>';
        echo '<p>'.esc_html($t('Check environment → save storage settings → check storage → create initial snapshot → start protection.','環境を確認 → 保存先を設定 → 保存先を確認 → 最初の保存 → 保護を開始')).'</p>';
        if(($c['setup_role']??'source')==='recovery'){
            echo '<p>'.esc_html($t('Recovery destination: keep protection off. Choose an existing Checkpoint under Site-wide recovery; do not create an initial snapshot here.','復旧先：保護は無効のまま、「初期保存とサイト全体の復旧」で既存の復旧ポイントを選択してください。ここで最初の保存は作成しません。')).'</p></section>';return;
        }
        $rows=self::local();$localReady=!in_array(false,array_column($rows,'ok'),true);
        $r=(array)get_option('owr_setup_storage',[]);
        $current=($r['identity']??'')===self::identity($c);
        $rows['storage']=['ok'=>$current&&!empty($r['ok']),'unchecked'=>!$current,'label'=>$t('Storage connection and versioning','保存先への接続・バージョン管理'),'next'=>$current?(!empty($r['ok'])?self::storageNext($c):AdminText::message((string)($r['message']??''))):$t('Save storage settings and confirm the terms, then select Check storage.','保存先の設定と利用条件の確認を保存し、「保存先を確認」を押してください。')];
        $rows['baseline']=['ok'=>self::baseline($c),'unchecked'=>!self::baseline($c),'label'=>$t('First save and verified read-back','最初の保存・読み戻し'),'next'=>self::baseline($c)?$t('Completed for this destination.','この保存先で完了しています。'):$t('Use Create complete initial snapshot after checking storage.','保存先の確認後、「最初の保存を作成」を押してください。')];
        $rows['protect']=['ok'=>!empty($c['protect']),'unchecked'=>empty($c['protect']),'label'=>$t('Protection','保護'),'next'=>!empty($c['protect'])?$t('Protection is enabled. Check a published post in Save protection status.','保護中です。公開した投稿の保存を「投稿などの保存状況」で確認してください。'):$t('After the first save, enable Protect supported operations in storage settings.','最初の保存が完了したら、保存先設定の「保護を開始する」を有効にしてください。')];
        echo '<table class="widefat striped"><thead><tr><th>'.esc_html($t('Item','項目')).'</th><th>'.esc_html($t('Status','状態')).'</th><th>'.esc_html($t('Next action','次の操作')).'</th></tr></thead><tbody>';
        foreach($rows as $row){
            $status=!empty($row['unused'])?$t('Not used','今回は使用しない'):($row['ok']?$t('Confirmed','確認済み'):(!empty($row['unchecked'])?$t('Not checked','未確認'):$t('Action needed','対応が必要')));
            echo '<tr><th scope="row">'.esc_html($row['label']).'</th><td>'.esc_html($status).'</td><td>'.esc_html($row['next']).'</td></tr>';
        }
        echo '</tbody></table><p>'.esc_html($t('Connection checks do not write or delete objects. The first save verifies writing and reading. Active supported integrations are included in that save; see the coverage table for requirements.','接続確認ではデータの書き込み・削除は行いません。書き込みと読み戻しは最初の保存で確認します。有効な対応連携も保存対象です。連携ごとの条件は対応表を参照してください。')).'</p>';
        if($current&&!empty($r['at']))echo '<p>'.esc_html($t('Storage last checked (UTC): ','保存先の最終確認（UTC）：').$r['at']).'</p>';
        if(self::configured($c)&&!isset($c['setup_version']))echo '<p>'.esc_html($t('Existing settings remain in use. Older initial saves are not reclassified by this new display. Confirm the terms when next saving settings.','既存の設定は継続して使用します。過去の初期保存はこの新しい表示では判定し直しません。次に設定を保存するときに利用条件を確認してください。')).'</p>';
        if(self::configured($c)&&$localReady&&$current&&!empty($r['ok'])&&!self::baseline($c))echo '<p><a class="button" href="#owr-action-whole_initial">'.esc_html($t('Go to first save','最初の保存へ進む')).'</a></p>';
        echo '<p><a href="#owr-storage">'.esc_html($t('Open storage settings','保存先の設定へ')).'</a> · <a href="https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide'.(str_starts_with(determine_locale(),'ja')?'-ja':'').'.md">'.esc_html($t('Setup and recovery guide','導入・復旧ガイド')).'</a></p></section>';
    }
}
