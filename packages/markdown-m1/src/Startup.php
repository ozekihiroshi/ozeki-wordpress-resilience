<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** A failed local upgrade pauses writing, not WordPress page rendering. */
final class Startup
{
    private static bool $ready=false;
    public static function ready(): bool { return self::$ready; }
    public static function prepare(): void {
        global $wpdb;
        $previous=$wpdb->suppress_errors(true);
        try { Identifiers::migrate();self::$ready=true; }
        catch (\Throwable $error) { self::$ready=false;self::guard(); }
        finally { $wpdb->suppress_errors($previous); }
    }
    private static function text(string $en,string $ja): string {
        return str_starts_with((string)determine_locale(),'ja')?$ja:$en;
    }
    private static function message(): string {
        return self::text('Resilience could not finish updating its settings. Saving is temporarily paused; viewing pages remains available. An administrator must check Tools → Resilience before retrying the save.','Resilienceの設定の引き継ぎが完了していません。閲覧はできますが、保存を一時停止しています。管理者が「ツール → Resilience」を確認してから、もう一度保存してください。');
    }
    public static function stop(): never {
        // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- WP_Error message is escaped; core selects the HTTP/REST/AJAX handler.
        wp_die(new \WP_Error('ozeki_resilience_update_pending',esc_html(self::message())),'Resilience',['response'=>503,'code'=>'ozeki_resilience_update_pending','back_link'=>true]);
        exit;
    }
    private static function guard(): void {
        // A read request can otherwise create a navigation post while rendering a block theme.
        add_filter('wp_navigation_should_create_fallback','__return_false');
        add_action('admin_notices',[self::class,'notice']);
        add_action('admin_menu',static function(){add_management_page('Resilience','Resilience','manage_options','ozeki-resilience',[self::class,'page']);});
        // Install guards before other plugins finish booting. Common content API guards also cover CLI/importer calls.
        foreach(['wp_insert_post_data','wp_insert_attachment_data','pre_delete_post','pre_trash_post','pre_untrash_post','pre_delete_attachment','pre_insert_term','preprocess_comment','wp_insert_comment_data','wp_update_comment_data','pre_delete_comment','pre_trash_comment','pre_untrash_comment','wp_pre_insert_user_data'] as $hook)add_filter($hook,[self::class,'stop'],PHP_INT_MIN,0);
        foreach(['add_post_metadata','update_post_metadata','delete_post_metadata','add_comment_metadata','update_comment_metadata','delete_comment_metadata','add_term_metadata','update_term_metadata','delete_term_metadata'] as $hook)add_filter($hook,[self::class,'stop'],PHP_INT_MIN,0);
        foreach(['delete_user','wpmu_delete_user','delete_term','edit_terms'] as $hook)add_action($hook,[self::class,'stop'],PHP_INT_MIN,0);
        add_action('init',[self::class,'request'],PHP_INT_MIN);
        add_action('wp_loaded',[self::class,'request'],PHP_INT_MIN);
        add_filter('rest_pre_dispatch',static function($result,$server,$request){
            return in_array($request->get_method(),['GET','HEAD','OPTIONS'],true)?$result:new \WP_Error('ozeki_resilience_update_pending',self::message(),['status'=>503]);
        },PHP_INT_MIN,3);
        add_filter('wp_handle_upload_prefilter',static function($file){$file['error']=self::message();return $file;});
        add_filter('wp_handle_sideload_prefilter',static function($file){$file['error']=self::message();return $file;});
        // No adapter, scheduled capture, cleanup or recovery action is registered until migration succeeds.
    }
    public static function request(): void {
        if(defined('WP_CLI')&&WP_CLI)return; // Content API guards still apply to CLI writes.
        global $pagenow;
        // Keep administrator sign-in available. Core validates credentials and login CSRF separately.
        $action=isset($_REQUEST['action'])&&is_string($_REQUEST['action'])?sanitize_key(wp_unslash($_REQUEST['action'])):'';
        if($pagenow==='wp-login.php'&&in_array($action,['','login','logout'],true))return;
        $method=isset($_SERVER['REQUEST_METHOD'])&&is_string($_SERVER['REQUEST_METHOD'])?strtoupper(sanitize_text_field(wp_unslash($_SERVER['REQUEST_METHOD']))):'GET';
        if(!in_array($method,['GET','HEAD','OPTIONS'],true)||(defined('DOING_CRON')&&DOING_CRON)||$action!=='')self::stop();
    }
    public static function notice(): void {
        if(!current_user_can('manage_options'))return;
        echo '<div class="notice notice-error"><p>'.esc_html(self::message()).' <a href="'.esc_url(admin_url('tools.php?page=ozeki-resilience')).'">'.esc_html(self::text('Check and retry','確認・再試行')).'</a></p></div>';
    }
    public static function page(): void {
        if(!current_user_can('manage_options')){wp_die(esc_html(self::text('Administrator access is required.','管理者権限が必要です。')));return;}
        echo '<div class="wrap"><h1>Resilience</h1><p>'.esc_html(self::message()).'</p><p>'.esc_html(self::text('Check with your hosting administrator that the database allows writes and named locks. If another update is running, wait for it to finish. Then use Retry. Existing saved assets and pending saves are retained; do not delete them or redo the initial save.','サーバー管理者に、データベースへの書込みと名前付きロックが利用できることを確認してください。別の更新処理が実行中なら完了を待ち、「再試行」を押してください。保存済み資産と未完了の保存は保持しています。削除や初期保存のやり直しは不要です。')).'</p><p><a class="button button-primary" href="'.esc_url(admin_url('tools.php?page=ozeki-resilience')).'">'.esc_html(self::text('Retry','再試行')).'</a></p></div>';
    }
}
