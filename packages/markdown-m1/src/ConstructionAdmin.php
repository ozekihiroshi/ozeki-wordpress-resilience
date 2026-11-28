<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if(!defined('ABSPATH'))exit;
require_once __DIR__.'/ConstructionPreservation.php';
require_once __DIR__.'/ConstructionCapture.php';
require_once __DIR__.'/ConstructionJob.php';
require_once __DIR__.'/SetupReadiness.php';
require_once __DIR__.'/ConstructionFollow.php';
require_once __DIR__.'/FlamingoReconstruction.php';

/** Explicitly isolated management entry. Never enables itself on existing sites. */
final class ConstructionAdmin {
    private static ?Store $isolatedStore=null;
    public static function enabled(): bool {return defined('OWR_CONSTRUCTION_ISOLATED')&&OWR_CONSTRUCTION_ISOLATED===true&&ConstructionJournal::enabled();}
    public static function boot(?Store $isolatedStore=null): void {
        if(!self::enabled())return;
        self::$isolatedStore=$isolatedStore;
        (new ConstructionCapture())->boot();
        add_action('admin_menu',static fn()=>add_management_page('Construction preservation','Construction preservation','manage_options','ozeki-construction',[self::class,'page']));
        add_action('admin_post_ozeki_construction',[self::class,'action']);
        add_action('ozeki_resilience_construction_flush',[self::class,'flushPending']);
    }
    public static function store(): Store {self::authorize();return self::$isolatedStore??(new Plugin())->store();}
    public static function scheduleTransfer(): void {
        if(!self::enabled())return;
        $c=(array)get_option('ozeki_resilience_m1_config',[]);
        if(empty($c['protect'])||($c['setup_role']??'source')!=='source'||get_option(ConstructionPreservation::KEY,null)===null)return;
        if(!wp_next_scheduled('ozeki_resilience_construction_flush'))wp_schedule_single_event(time()+10,'ozeki_resilience_construction_flush');
    }
    public static function flushPending(): void {
        if(!self::enabled())return;
        $p=new Plugin();$c=$p->config();
        if(empty($c['protect'])||($c['setup_role']??'source')!=='source'||!SetupReadiness::accepted($c))return;
        try{
            (new ConstructionPreservation(self::$isolatedStore??$p->store(),SetupReadiness::identity($c)))->flush();
            update_option(ConstructionPreservation::KEY.'_notice','confirmed',false);
        }catch(\Throwable $e){update_option(ConstructionPreservation::KEY.'_notice','incomplete',false);}
        // No retry loop, periodic backup, or deletion scheduling is added.
    }
    private static function service(): ConstructionPreservation {
        $p=new Plugin();$c=$p->config();
        if(($c['setup_role']??'source')!=='source'||!SetupReadiness::accepted($c))throw new \RuntimeException('Prepared source storage and consent required');
        return new ConstructionPreservation(self::store(),SetupReadiness::identity($c));
    }
    public static function authorize(): void {
        if(!self::enabled()||!current_user_can('manage_options'))throw new \RuntimeException('Construction administration not authorized');
    }
    public static function stateText(string $state): string {
        $labels=[
            'not_started'=>['No recorded operations','操作記録なし'], 'transfer_pending'=>['Local recording complete; transfer pending','ローカル記録済み・転送待ち'],
            'gap'=>['Unrecorded change detected; preservation is incomplete','未記録の変更を検出・保全未完了'], 'outcome_unknown'=>['Operation outcome is unknown','操作結果が不明'],
            'unsupported'=>['An operation requires an additional recording contract','記録の契約が不足している操作あり'], 'record_error'=>['Record integrity could not be confirmed','記録の整合性を確認できません'],
            'writer_busy_or_interrupted'=>['Recording is running or was interrupted','記録処理が実行中、または中断しています'],
            'initial_required'=>['Initial preservation required','初回保存が必要'], 'pending'=>['Transfer pending','転送待ち'], 'confirmed'=>['Confirmed in storage','保存先で確定済み'],
            'destination_changed'=>['Storage destination differs','保存先が変更されています'], 'storage_not_ready'=>['Storage preparation required','保存先の準備が必要'],
            'not_requested'=>['Reconstruction not requested','再構築は未要求'], 'queued'=>['Waiting for the prepared local worker','準備済みローカル実行器の開始待ち'],
            'running'=>['Reconstruction running; do not start another worker','再構築中・別の実行器を開始しないでください'],
            'claim_outcome_unknown'=>['Worker start is uncertain; do not retry automatically','実行器の開始結果が不明・自動再試行不可'],
            'registered_pending_use_check'=>['Registration finished; usage checks remain','通常登録が終了・利用確認待ち'], 'held'=>['Reconstruction held; inspect the private result','再構築を保留・非公開の結果記録を確認してください'],
        ];
        $pair=$labels[$state]??['Unknown state; no completion claimed','状態不明・完了として扱いません'];return SetupReadiness::text(...$pair);
    }
    public static function action(): void {
        if(!self::enabled()||!current_user_can('manage_options'))wp_die(esc_html(SetupReadiness::text('Not authorized.','権限がありません。')),'',['response'=>403]);
        self::authorize();check_admin_referer('ozeki_construction');
        $op=isset($_POST['operation'])&&is_string($_POST['operation'])?wp_unslash($_POST['operation']):'';
        try {
            if($op==='queue'){
                $p=new Plugin();$c=$p->config();
                if(($c['setup_role']??'')!=='recovery')throw new \RuntimeException('Prepare a separate recovery destination');
                if(!is_string($_POST['commit']??null))throw new \RuntimeException('Commit reference missing');
                $ref=json_decode(wp_unslash($_POST['commit']),true,32,JSON_THROW_ON_ERROR);
                (new ConstructionJob(self::store(),SetupReadiness::identity($c)))->queue($ref);
            }elseif($op==='initial'){
                $s=self::service();
                if(($_POST['trust_initial']??'')!=='1')throw new \RuntimeException('Confirm the initial site and pause editing');
                $s->initial(static function(){ $snapshot=new SiteSnapshot(self::store());$ref=$snapshot->capture(true,[]);return $snapshot->load($ref['manifest'],true); });
            }elseif($op==='flush')self::service()->flush();
            else throw new \RuntimeException('Unknown construction action');
            update_option(ConstructionPreservation::KEY.'_notice','confirmed',false);
        }catch(\Throwable $e){
            // Never expose input bodies, AWS errors, credentials, or exception paths.
            update_option(ConstructionPreservation::KEY.'_notice','incomplete',false);
        }
        wp_safe_redirect(admin_url('tools.php?page=ozeki-construction'));exit;
    }
    public static function page(): void {
        self::authorize();$t=static fn($en,$ja)=>SetupReadiness::text($en,$ja);
        echo '<div class="wrap"><h1>'.esc_html($t('Construction preservation (isolated)','構築記録の保全（隔離環境）')).'</h1>';
        echo '<p>'.esc_html($t('Local registration is not a confirmed preservation point. Unknown or unrecorded changes remain on hold.','通常登録の成功は保全の確定ではありません。結果不明・記録のない変更は保留します。')).'</p>';
        try{$status=self::service()->status();}catch(\Throwable $e){$status=ConstructionJournal::status()+['transfer'=>'storage_not_ready'];}
        echo '<p>'.esc_html(self::stateText($status['state'])).'</p><p>'.esc_html(self::stateText($status['transfer'])).'</p>';
        echo '<p>'.esc_html($t('Recorded operations / confirmed through: ','記録した操作数／確定済み番号： ')).esc_html((string)($status['count']??'?').' / '.(string)($status['confirmed_through']??0)).'</p>';
        echo '<p>'.esc_html(self::stateText(ConstructionJob::summary()['state'])).'</p>';
        $saved=get_option(ConstructionPreservation::KEY,null);
        if(isset($saved['commit']))echo '<p>'.esc_html($t('Confirmed reference (use only on a prepared separate destination):','確定記録の参照（準備した別の復旧先で使用）')).'</p><pre>'.esc_html(wp_json_encode($saved['commit'])).'</pre>';
        $notice=get_option(ConstructionPreservation::KEY.'_notice');
        if($notice==='incomplete')echo '<p>'.esc_html($t('The request did not complete. Inspect local records, storage preparation and pending outcomes before retrying. No successful preservation is claimed.','処理は完了していません。記録・保存先の準備・結果不明の操作を確認してください。保全成功として扱いません。')).'</p>';
        foreach(['initial'=>$t('Create initial preservation point','初回保存を作成'),'flush'=>$t('Confirm pending records in storage','未転送の記録を保存先で確定')] as $op=>$label){
            echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';wp_nonce_field('ozeki_construction');
            echo '<input type="hidden" name="action" value="ozeki_construction"><input type="hidden" name="operation" value="'.esc_attr($op).'">';
            if($op==='initial')echo '<label><input type="checkbox" name="trust_initial" value="1" required> '.esc_html($t('I trust this initial site and have paused editing.','初回保存の内容を確認し、編集を停止しました。')).'</label> ';
            submit_button($label,'secondary','submit',false);echo '</form>';
        }
        echo '<h2>'.esc_html($t('Request normal registration on this destination','この復旧先で通常登録を要求')).'</h2><p>'.esc_html($t('A prepared local worker is required. This page does not install software or start a shell. Uncertain jobs are never retried automatically.','準備済みのローカル実行器が必要です。この画面はソフトウェアの導入やシェルの起動を行いません。結果不明の作業は自動再実行しません。')).'</p>';
        echo '<form method="post" action="'.esc_url(admin_url('admin-post.php')).'">';wp_nonce_field('ozeki_construction');
        echo '<input type="hidden" name="action" value="ozeki_construction"><input type="hidden" name="operation" value="queue"><textarea name="commit" rows="4" cols="80" required aria-label="'.esc_attr($t('Confirmed commit reference','確定記録の参照')).'"></textarea>';
        submit_button($t('Queue reconstruction','再構築を予約'),'secondary','submit',false);echo '</form>';
        echo '</div>';
    }
}
