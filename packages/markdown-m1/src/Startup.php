<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Contain a failed local migration without blocking unrelated WordPress operations. */
final class Startup
{
    private static bool $ready=false;
    private static bool $gapRecordingFailed=false;
    public static function ready(): bool { return self::$ready; }
    public static function prepare(): void {
        global $wpdb;
        $previous=$wpdb->suppress_errors(true);
        try {
            Identifiers::migrate();self::pauseAfterGap();self::$ready=true;
            if(get_option('ozeki_resilience_startup_gap'))add_action('admin_notices',[self::class,'notice']);
        }
        catch (\Throwable $error) {
            self::$ready=false;
            // Publish a sticky interruption only when this request cannot boot preservation.
            // Add rather than replace: a concurrent retry may already have recorded 'paused'.
            try {
                add_option('ozeki_resilience_startup_gap','pending','',false);
                if(!self::gap())throw new \RuntimeException('Cannot record preservation interruption.');
            } catch (\Throwable $recordError) {
                self::$gapRecordingFailed=true;
                // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log -- Fixed operational alert when durable interruption recording itself fails; no request or credential data.
                error_log('Ozeki Resilience: preservation interruption could not be recorded. Administrator intervention required.');
            }
            self::guard();
        }
        finally { $wpdb->suppress_errors($previous); }
    }
    private static function text(string $en,string $ja): string {
        return str_starts_with((string)determine_locale(),'ja')?$ja:$en;
    }
    private static function message(): string {
        if(self::$gapRecordingFailed)return self::text('Resilience preservation is stopped and its interruption record could not be saved. Ask the administrator to repair database writes and check changes made during the interruption before resuming protection.','Resilienceの保全は停止しています。中断の記録も保存できませんでした。管理者がデータベースへの書込みを修復し、停止中の変更を確認してから保護を再開してください。');
        if(self::ready())return self::text('Resilience protection remains off after a settings migration. Resolve pending saves, review changes made during the interruption, create a new trusted complete initial snapshot, then explicitly enable protection.','設定移行後の保護は停止中です。未完了保存と停止中の変更を確認し、健全なサイトから新しい初回保存を作成した後、明示的に保護を開始してください。');
        return self::text('Resilience could not finish updating its settings. Resilience preservation is stopped; normal WordPress operations remain available. Changes made during this interruption are not confirmed in S3. Check Tools → Resilience.','Resilienceの設定の引き継ぎが完了していません。Resilienceの保全は停止しています。WordPressの通常操作は継続できますが、停止中の変更はS3への確定を確認できません。「ツール → Resilience」を確認してください。');
    }
    private static function guard(): void {
        // Only Resilience's boot is withheld. Core and other plugins keep their own permissions.
        add_action('admin_notices',[self::class,'notice']);
        add_action('admin_menu',static function(){add_management_page('Resilience','Resilience','manage_options','ozeki-resilience',[self::class,'page']);});
    }
    private static function pauseAfterGap(): void {
        if(self::gap()!=='pending')return;
        $config=(array)get_option('ozeki_resilience_m1_config',[]);
        $config['protect']=false;update_option('ozeki_resilience_m1_config',$config,false);
        delete_option('ozeki_resilience_setup_baseline');
        if(get_option('ozeki_resilience_m1_config')!==$config||get_option('ozeki_resilience_setup_baseline'))throw new \RuntimeException('Cannot record paused protection.');
        update_option('ozeki_resilience_startup_gap','paused',false);
        if(get_option('ozeki_resilience_startup_gap')!=='paused')throw new \RuntimeException('Cannot record preservation gap.');
    }
    private static function gap(): mixed {
        // Another request can record a failure while this request completes migration.
        // Do not trust this request's earlier cached absence of the non-autoloaded option.
        wp_cache_delete('ozeki_resilience_startup_gap','options');
        wp_cache_delete('notoptions','options');
        return get_option('ozeki_resilience_startup_gap');
    }
    public static function notice(): void {
        if(!current_user_can('manage_options'))return;
        echo '<div class="notice notice-error"><p>'.esc_html(self::message()).' <a href="'.esc_url(admin_url('tools.php?page=ozeki-resilience')).'">'.esc_html(self::text('Check and retry','確認・再試行')).'</a></p></div>';
    }
    public static function page(): void {
        if(!current_user_can('manage_options')){wp_die(esc_html(self::text('Administrator access is required.','管理者権限が必要です。')));return;}
        echo '<div class="wrap"><h1>Resilience</h1><p>'.esc_html(self::message()).'</p><p>'.esc_html(self::text('Check with your hosting administrator that the database allows writes and named locks. If another update is running, wait for it to finish. Then use Retry. Existing saved assets and pending saves are retained; do not delete them. After migration succeeds, review the preservation gap and follow the protection restart guidance.','サーバー管理者に、データベースへの書込みと名前付きロックが利用できることを確認してください。別の更新処理が実行中なら完了を待ち、「再試行」を押してください。保存済み資産と未完了の保存は保持しています。削除しないでください。移行成功後は保全の空白を確認し、保護再開の案内に従ってください。')).'</p><p><a class="button button-primary" href="'.esc_url(admin_url('tools.php?page=ozeki-resilience')).'">'.esc_html(self::text('Retry','再試行')).'</a></p></div>';
    }
}
