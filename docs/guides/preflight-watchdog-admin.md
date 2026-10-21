# 導入前検査watchdogの管理画面

「Resilience → 導入前検査の独立監視」で、検査側・受渡し側の到達性、進捗の更新、警報・回復の履歴、通知失敗・未配送件数を確認できます。既存の `ObserverAdmin` と2対象watchdog表示を再利用しています。管理者権限 `manage_options` が必要な読取り専用画面で、解除・再送・設定変更は行いません。

## 外部監視側の報告

[独立watchdog](preflight-watchdog.md)の各observe設定へ、既存の公開状態出力を指定します。

```json
{
  "admin_site_id": "example-site",
  "public_status_file": "/var/lib/owr-public/preflight-source.json"
}
```

これは設定への追加項目であり、完全なobserve設定ではありません。受渡し側は別の出力ファイルとmonitor_idを使用します。報告は既存の `owr-observer-status-v1` 形式です。状態ファイル・通知台帳・秘密鍵をWordPressへ渡さず、公開報告だけを管理された配置経路で渡します。

## WordPress側の設定

`wp-config.php` に以下を設定します。OWR_PREFLIGHT_SITE_IDが導入前検査で設定済みの場合は重複定義しません。

```php
define('OWR_PREFLIGHT_SITE_ID', 'example-site');
define('OWR_PREFLIGHT_WATCHDOG_REPORTS', [
    'source' => [
        'path' => '/var/lib/owr-reports/preflight-source.json',
        'monitor_id' => 'preflight-source',
    ],
    'receiver' => [
        'path' => '/var/lib/owr-reports/preflight-receiver.json',
        'monitor_id' => 'preflight-receiver',
    ],
]);
```

外部配置ユーザーだけが報告と親ディレクトリーを書けるようにし、WordPressには読取りだけを許可します。受渡し後は原子的renameで公開します。サイトとmonitor_idが不一致、サイズ超過、形式不正、未来時刻の場合は正常表示にしません。片側未取得と両側未取得を区別し、5分以上古い報告は現在の状態が不明と表示します。

既存の状態転送が出力する `owr-observer-transfer-v1` 記録を使う場合は、各対象へ `transfer_file` を追加できます。未設定なら「定期取得の記録は未取得」と表示します。この変更は表示機能であり、導入前検査watchdogの定期転送サービスを自動配置するものではありません。

## 履歴と通知状態の意味

「発生」「解消」は警報の状態変化です。通知サービスへの配送、端末の受信、人の確認とは別です。配送結果は公開報告のdelivery状態を表示します。不明な場合は成功と扱いません。検査が進んでいても導入前検査の未確認項目が解消したとは限らず、この画面で本番導入可否や復旧セットの署名承認は行いません。

## 専用検証

既存72時間観測と別のWordPress/MariaDB/Chromiumを使用します。既存observer処理で試験用の警報・回復報告を生成し、画面ケースでは時刻を明示的に調整します。通信断自体を再実行する試験ではなく、新しい表示との接続を確認する試験です。正常、警報、回復履歴、未配送、古い報告、片側欠落、対象取り違え、不正報告、権限、POST拒否を確認します。HTTP前後でWordPress設定・Cron・要求ファイル・元の試験台帳が変わらないことも確認します。

検証結果は [公開用記録](../../evidence-public/preflight-watchdog-admin.json) にまとめています。初回のWordPress初期化とCron登録が済んだ後を基準に、画面検証前後の設定・Cron・要求ファイル・試験台帳の不変を確認しています。

実watchdogの報告を定期取得する設定と障害・回復試験は [定期受渡し手順](preflight-observer-relay.md) を参照してください。

導入前検査watchdogの状態転送を常駐化する手順は [systemdによる停止・再開と自動起動](preflight-observer-systemd.md) にあります。
