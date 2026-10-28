<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Local WordPress identifiers only; archived schemas and S3 objects never change. */
final class Identifiers
{
    private const DONE='ozeki_resilience_identifiers_v1';
    private const OPTIONS=[
        'owr_m1_config','owr_m1_pending','owr_m1_comment_pending','owr_m1_comment_error',
        'owr_m1_capture_error','owr_m1_notice','owr_m1_error','owr_m1_checkpoint_status',
        'owr_m1_cleanup_preview','owr_m1_cleanup_status','owr_m1_restore_result',
        'owr_gfs_due','owr_setup_baseline','owr_setup_storage','owr_site_initial',
        'owr_site_cleanup_preview','owr_site_cleanup_status','owr_site_origin_url',
        'owr_site_restore_attempt','owr_site_restore_result','owr_site_retention_result','owr_site_snapshot_result',
    ];
    private const POST_META=['_owr_m1_asset','_owr_m1_origin','_owr_m1_origin_id','_owr_m1_origin_url'];
    private const USER_META=['_owr_member_origin','_owr_member_source'];
    private static function current(string $key): string { return str_replace('owr_', 'ozeki_resilience_', $key); }

    /** Prefer an existing current identifier if an older archive contains both. */
    public static function metadata(array $rows): array {
        $seen=[];foreach($rows as $row)$seen[(string)$row['post_id']][$row['meta_key']]=true;
        $out=[];foreach($rows as $row){
            if(in_array($row['meta_key'],self::POST_META,true)){
                $new=self::current($row['meta_key']);
                if(isset($seen[(string)$row['post_id']][$new]))continue;
                $row['meta_key']=$new;
            }$out[]=$row;
        }return $out;
    }

    public static function migrate(): void {
        if(get_option(self::DONE))return;
        global $wpdb;
        $lock='ozeki-resilience-identifiers-'.substr(hash('sha256',$wpdb->prefix),0,24);
        // phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- Serialize the one-time migration across requests.
        if((string)$wpdb->get_var($wpdb->prepare('SELECT GET_LOCK(%s, 0)',$lock))!=='1')throw new \RuntimeException('Ozeki Resilience: identifier update is busy. Retry this request.');
        try {
            wp_cache_delete(self::DONE,'options');
            if(get_option(self::DONE))return;
            // Rename raw rows, preserving serialized bytes, autoload state and multi-value metadata.
            // Existing new names take precedence; old conflicting rows are retained but never read by the product.
            foreach(self::OPTIONS as $old)self::rename($wpdb->options,'option_name',null,$old);
            foreach(self::POST_META as $old)self::rename($wpdb->postmeta,'meta_key','post_id',$old);
            foreach(self::USER_META as $old)self::rename($wpdb->usermeta,'meta_key','user_id',$old);
            wp_cache_flush();
            foreach(_get_cron_array() as $at=>$hooks){
                foreach(['owr_m1_checkpoint','owr_m1_checkpoint_daily'] as $old){
                    foreach($hooks[$old]??[] as $event){
                        // Retired daily jobs are removed; init schedules from the preserved configuration.
                        if($old==='owr_m1_checkpoint'){
                            $new=self::current($old);$args=$event['args'];
                            if(!wp_get_scheduled_event($new,$args,(int)$at)){
                                $ok=$event['schedule']?wp_schedule_event((int)$at,$event['schedule'],$new,$args,true):wp_schedule_single_event((int)$at,$new,$args,true);
                                if(is_wp_error($ok)||$ok===false)throw new \RuntimeException('Ozeki Resilience: could not migrate the Checkpoint schedule. Retry this request.');
                            }
                        }
                        $ok=wp_unschedule_event((int)$at,$old,$event['args'],true);
                        if(is_wp_error($ok)||$ok===false)throw new \RuntimeException('Ozeki Resilience: could not retire the previous Checkpoint schedule. Retry this request.');
                    }
                }
            }
            if(!update_option(self::DONE,1,false)&&!get_option(self::DONE))throw new \RuntimeException('Ozeki Resilience: could not finish the identifier update. Retry this request.');
        } finally {
            // Also clear caches after a partial failure so the idempotent retry sees renamed rows.
            wp_cache_flush();
            // phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- Release the request-owned migration lock.
            $wpdb->get_var($wpdb->prepare('SELECT RELEASE_LOCK(%s)',$lock));
        }
    }

    private static function rename(string $table,string $column,?string $owner,string $old): void {
        global $wpdb;
        // %i escapes identifiers; the values are exact known keys, never a prefix-wide rename.
        if($owner===null){
            // phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- One-time raw rename preserves saved serialized bytes; migrate invalidates caches.
            $result=$wpdb->query($wpdb->prepare('UPDATE %i legacy LEFT JOIN %i destination ON destination.%i=%s SET legacy.%i=%s WHERE legacy.%i=%s AND destination.%i IS NULL',$table,$table,$column,self::current($old),$column,self::current($old),$column,$old,$column));
        }else{
            // phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- Preserve all metadata values and existing current mappings; migrate invalidates caches.
            $result=$wpdb->query($wpdb->prepare('UPDATE %i legacy LEFT JOIN %i destination ON destination.%i=%s AND legacy.%i=destination.%i SET legacy.%i=%s WHERE legacy.%i=%s AND destination.%i IS NULL',$table,$table,$column,self::current($old),$owner,$owner,$column,self::current($old),$column,$old,$column));
        }
        if($result===false)throw new \RuntimeException('Ozeki Resilience: identifier update failed. Check database write access and retry.');
    }
}
