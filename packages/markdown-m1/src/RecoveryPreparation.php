<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Display recorded software requirements without downloading or installing software. */
final class RecoveryPreparation {
    /** Shared, read-only requirements for the selected point and confirmed history. */
    public static function checks(array $m,array $data): array {
        $t=[SetupReadiness::class,'text'];$rows=[];
        $add=static function($label,$expected,$actual,$ok,$next)use(&$rows,$t){$rows[]=['label'=>$label,'expected'=>$expected,'actual'=>$actual,'ok'=>$ok,'next'=>$ok?$t('Confirmed','確認済み'):$next];};
        $expected=(string)($m['wordpress']??'');$current=(string)$GLOBALS['wp_version'];
        $ok=$expected!==''&&implode('.',array_slice(explode('.',$expected),0,2))===implode('.',array_slice(explode('.',$current),0,2))&&version_compare($current,$expected,'>=');
        $add('WordPress',$expected,$current,$ok,$t('Install the recorded WordPress release line with the same or a newer maintenance patch, then recheck.','記録されたWordPress系列の同じか新しい修正版を導入し、再確認してください。'));
        $plugins=$m['plugins']??[];
        foreach(array_keys($m['required_form_plugins']??[]) as $plugin)if(!in_array($plugin,$plugins,true))$plugins[]=$plugin;
        foreach($plugins as $plugin){
            $valid=is_string($plugin)&&!str_contains($plugin,'..')&&!str_starts_with($plugin,'/')&&preg_match('~^[a-zA-Z0-9_./-]+\.php$~D',$plugin);
            $header=$valid&&is_file(WP_PLUGIN_DIR.'/'.$plugin)?get_file_data(WP_PLUGIN_DIR.'/'.$plugin,['Version'=>'Version']):[];
            $version=(string)($m['required_form_plugins'][$plugin]??$m['software_inventory']['plugins'][$plugin]['version']??'');
            if($plugin===TableHistory::PLUGIN&&isset($m['required_tablepress_version']))$version=(string)$m['required_tablepress_version'];
            $active=$valid&&in_array($plugin,(array)get_option('active_plugins',[]),true);$actual=(string)($header['Version']??'');
            $add((string)$plugin,$version,$actual?:$t('Not installed','未導入'),$active&&($version===''||$version===$actual),$t('Install the recorded version from a trusted distributor and activate it in Plugins, then recheck.','信頼できる配布元から記録された版を導入し、「プラグイン」で有効化して再確認してください。'));
        }
        $language=$data['options']['WPLANG']??'';if($language===false)$language='';$valid=is_string($language)&&preg_match('/^[a-zA-Z0-9_@-]*$/D',$language);
        $ok=$valid&&($language===''||$language==='en_US'||in_array($language,get_available_languages(),true));
        $add($t('Site language pack','サイトの言語パック'),$valid?($language?:'en_US'):$t('Invalid saved value','保存値が不正'),$ok?$t('Installed','導入済み'):$t('Not installed','未導入'),$ok,$t('In Settings → General → Site Language, select the recorded language and save. If downloads are unavailable, ask the administrator to install the official language pack for this WordPress version. Then recheck.','「設定 → 一般 → サイトの言語」で記録された言語を選んで保存してください。ダウンロードできない場合は管理者に、このWordPress版の公式言語パックの導入を依頼し、その後に再確認してください。'));
        $c=(new Plugin())->config();
        $add($t('Recovery destination','復旧先'),$t('A separate site with protection off','保護をオフにした別サイト'),home_url(),rtrim((string)($m['source_url']??''),'/')!==rtrim(home_url(),'/')&&empty($c['protect']),$t('Use a separate WordPress destination and leave protection off.','別のWordPressを復旧先にし、保護をオフにしてください。'));
        foreach(SetupReadiness::local() as $row)$add($row['label'],'','',$row['ok'],$row['next']);
        return $rows;
    }
    public static function requireReady(array $m,array $data): void {
        $missing=[];foreach(self::checks($m,$data) as $row)if(!$row['ok'])$missing[]=$row['label'].' ('.$row['expected'].'): '.$row['next'];
        // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Internal message; admin response escapes the complete message.
        if($missing)throw new \RuntimeException(SetupReadiness::text('Recovery preparation needed: ','復旧先の準備が必要です：').implode(' / ',$missing));
    }
    public static function renderCheck(array $check): void {
        if(!$check||($check['identity']??'')!==SetupReadiness::identity((new Plugin())->config()))return;
        $t=[SetupReadiness::class,'text'];
        echo '<section id="owr-recovery-check"><h3>'.esc_html($t('Recovery preparation check','復旧前の準備確認')).'</h3><p>'.esc_html(($check['at']??'').' / '.$t('History end: ','履歴の終点：').($check['through']??'').' / '.($check['ref']['key']??'')).'</p>';
        echo '<p>'.esc_html($t('After preparing the missing items, select the same recovery point and history end and click Check / recheck recovery preparation. Recovery checks these conditions again before changing destination content.','不足項目を準備したら、同じ復旧ポイントと履歴の終点を選び「復旧前の準備を確認・再確認」を押してください。復旧時にも、復旧先の内容を変更する前に再確認します。')).'</p>';
        echo '<p><a href="'.esc_url(admin_url('options-general.php')).'">'.esc_html($t('Open language settings','言語設定を開く')).'</a> · <a href="'.esc_url(admin_url('plugins.php')).'">'.esc_html($t('Open Plugins','プラグインを開く')).'</a></p><table class="widefat striped"><thead><tr>';
        foreach([$t('Requirement','確認項目'),$t('Required','必要なもの'),$t('Current','現在'),$t('Next action','次の操作')] as $h)echo '<th>'.esc_html($h).'</th>';
        echo '</tr></thead><tbody>';
        foreach(self::checks($check['requirements'],['options'=>['WPLANG'=>$check['language']]]) as $row){echo '<tr>';foreach(['label','expected','actual','next'] as $key)echo '<td>'.esc_html((string)$row[$key]).'</td>';echo '</tr>';}
        echo '</tbody></table></section>';
    }
    public static function render(array $points): void {
        $t=[SetupReadiness::class,'text'];
        echo '<h3>'.esc_html($t('Prepare the recovery destination','復旧先に用意するもの')).'</h3><p>'.esc_html($t('Open the recovery point you will use and prepare its recorded software from trusted distributors. Themes are listed for reference; recovery keeps the destination theme. These are the requirements recorded in the point, not a completed recovery check.','使用する復旧ポイントを開き、記録されたソフトウェアを信頼できる配布元から用意してください。テーマは再導入の参考情報です。復旧先で選んだテーマを維持します。この一覧は復旧ポイントに記録された構成であり、復旧処理全体の確認結果ではありません。')).'</p>';
        foreach($points as $point){
            $m=$point['preparation']??[];
            echo '<details><summary>'.esc_html(gmdate('c',$point['created']).' / '.$t('history ','履歴 ').$point['through'].' / '.$point['ref']['key']).'</summary>';
            $wp=(string)($m['wordpress']??'');$current=(string)$GLOBALS['wp_version'];
            $sameLine=implode('.',array_slice(explode('.',$wp),0,2))===implode('.',array_slice(explode('.',$current),0,2));
            $rows=[['WordPress',$wp,$current,$wp!==''&&$sameLine&&version_compare($current,$wp,'>=')?$t('Confirmed','確認済み'):$t('Use this release line, at the same or a newer maintenance patch.','記録された系列の同じか新しい修正版を用意してください。')]];
            foreach($m['plugins']??[] as $plugin){
                // Treat S3 inventory as untrusted text, never as a path to read locally.
                $expected=(string)($m['software_inventory']['plugins'][$plugin]['version']??'');
                $active=in_array($plugin,(array)get_option('active_plugins'),true);
                $valid=!str_contains($plugin,'..')&&!str_starts_with($plugin,'/')&&preg_match('~^[a-zA-Z0-9_./-]+\.php$~D',$plugin);
                $header=$valid&&is_file(WP_PLUGIN_DIR.'/'.$plugin)?get_file_data(WP_PLUGIN_DIR.'/'.$plugin,['Version'=>'Version','Name'=>'Plugin Name']):[];
                $actual=(string)($header['Version']??'');
                $next=!$active?$t('Install and activate from a trusted distributor.','信頼できる配布元から導入し、有効化してください。'):($expected===''?$t('Version not recorded; consult the saved environment notes.','版の記録がありません。保存元の環境記録を確認してください。'):($actual===$expected?$t('Confirmed','確認済み'):$t('Prepare the recorded version.','記録された版を用意してください。')));
                $name=(string)($m['software_inventory']['plugins'][$plugin]['name']??($header['Name']??$plugin));
                $rows[]=[$name?:$plugin,$expected?:$t('Not recorded','記録なし'),$actual?:$t('Not installed','未導入'),$next];
            }
            echo '<table class="widefat striped"><thead><tr>';
            foreach([$t('Software','ソフトウェア'),$t('Recorded version','保存時の版'),$t('Installed version','復旧先の版'),$t('Next action','次の操作')] as $heading)echo '<th>'.esc_html($heading).'</th>';
            echo '</tr></thead><tbody>';
            foreach($rows as $row){echo '<tr>';foreach($row as $cell)echo '<td>'.esc_html($cell).'</td>';echo '</tr>';}
            echo '</tbody></table>';
            foreach($m['software_inventory']['themes']??[] as $slug=>$theme)echo '<p>'.esc_html($t('Theme (reference): ','テーマ（参考）：').$slug.' / '.($theme['name']??'').' / '.($theme['version']??'')).'</p>';
            if(rtrim((string)($m['source_url']??''),'/')===rtrim(home_url(),'/'))echo '<p>'.esc_html($t('Use a separate recovery URL. Reopen the original domain after checking recovery.','復旧確認用の別URLを用意してください。元のドメインへの切替は復旧確認後に行います。')).'</p>';
            echo '</details>';
        }
    }
}
