<?php
declare(strict_types=1);
namespace OzekiResilience\M1;
if (!defined('ABSPATH')) exit;

/** Display recorded software requirements without downloading or installing software. */
final class RecoveryPreparation {
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
                $header=$valid?get_file_data(WP_PLUGIN_DIR.'/'.$plugin,['Version'=>'Version','Name'=>'Plugin Name']):[];
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
