# WordPress通知管理画面の専用環境試作

2026-10-19。[設定仕様](../spec/12-notification-settings-and-health.md)に沿った初期管理画面。WordPress管理者が「Resilience → 通知」から通知先、対象警報、配送状態を扱う。

## 今回の実装

- 複数通知先の追加・編集・無効化。通知先IDを保持し、削除で履歴を失う操作は用意しない。
- 方式はPushover、メールSTARTTLS、メールTLS。LINE・Slack・PagerDutyは未対応と表示する。
- 通知先名、メール宛先またはPushover受信者の表示名、外部の接続設定名、対象警報、Pushover再通知間隔・期限を保存する。
- 設定版、操作した管理者ID、時刻を記録。古い画面からの更新を拒否し、DBの比較更新で同時保存による上書きを防ぐ。
- 配送待ち、再試行、サービス受付、拒否、結果不明、人の確認待ち・確認済み・期限切れ・取消を分けて表示する。受付だけで端末到達や人の確認とは扱わない。
- 未接続、古い状態、不正な状態、設定版の未反映を表示する。重要警報の通知先が不足している場合は警告する。
- 管理者権限、POST、nonceを検証する。出力をエスケープし、ヘッダー注入、未対応警報、無効な間隔等を拒否する。

管理画面は**設定候補**を保存する。保存だけで外部ワーカーへ適用したり、実通知を送ったりしない。利用状態も「利用希望：有効」と表示する。現在は初回設定を外部側で明示的に反映する方式で、稼働済み設定の自動切替・移行はまだ行わない。

## 資格情報と役割分離

API Token、User Key、SMTPパスワードはWordPressへ保存しない。外部配送側で管理する接続設定の識別名（例：`operator_push`）を画面で指定する。Pushoverの宛先キーもこの接続設定に含め、画面には人が識別できる受信者名だけを入力する。

通知先を選べることと、侵害され得るWordPressから独立監視の秘密情報を変更できることを分ける。WordPressの設定エクスポートは独立側から見れば未承認の入力であり、外部運用担当が確認したうえで初回構成を作る。

SMTPの送信元・ホスト・TLS方式・認証情報ファイルも外部接続設定で指定する。画面で指定したメール宛先がこの接続設定へ追加される。外部側での受信者の許可範囲・変更承認は本番運用設計として別途扱う。

## 初回接続の手順（専用環境）

1. `ozeki-wordpress-resilience.php`と`src/NotificationAdmin.php`を同名のプラグインフォルダへ配置して有効化する。この画面はPHP 8.1以上が必要。
2. 管理者で「Resilience → 通知」を開く。接続設定名は外部運用側と合意した識別名にする。
3. 通知先・対象警報を保存する。「設定候補をエクスポート」でJSONを取得する。秘密値は含まないが、メール宛先を含むので公開リポジトリへ入れない。
4. 外部側で以下の接続設定を作る。パスは外部ホストの絶対パス。秘密ファイルの権限等は既存の[Pushover手順](pushover-notification-lab.md)に従う。

```json
{
  "operator_push": {
    "transport": "pushover",
    "credentials_file": "/home/OPERATOR/.config/owr/pushover.json"
  },
  "history_mail": {
    "transport": "smtp_starttls",
    "host": "smtp.example.invalid",
    "port": 587,
    "from": "resilience@example.invalid",
    "credentials_file": "/home/OPERATOR/.config/owr/smtp.json"
  }
}
```

5. 初回構成を生成する。この操作は送信しない。`--output`は新しいディレクトリ、`--state`は未使用の配送状態ディレクトリを指定する。既存状態がある場合は移行が必要として拒否する。既存DBを消して回避しない。

```sh
python3 tools/notification-admin-bridge.py compile \
  --settings /private/owr-notification-settings.json \
  --profiles /private/notification-profiles.json \
  --source-outbox /private/monitor/monitor.sqlite \
  --state /private/new-delivery-state \
  --output /private/new-compiled-settings
```

`config.json`と、対象サイト・設定版・構成ハッシュを結ぶ`binding.json`ができる。今回の自動試験ではこの構成を使って配送ワーカーを実行し、プロバイダーだけを模擬した。実キーを使ったワーカー実行は実際に通知を送るため、この試験では行っていない。

既存のsource outboxにイベントがある場合も、過去の全事件を無断再送しないため既定では生成を拒否する。内容を確認して過去イベントを意図的に含める場合だけ`--include-existing`を指定する。専用環境の試験では、この指定で試験イベント1件を取り込む。

6. ワーカー完了後、秘密値を除いた状態レポートを生成する。状態DBの設定版と構成を照合し、配送ロックを共有して一貫した状態を読む。

```sh
python3 tools/notification-admin-bridge.py status \
  --compiled /private/new-compiled-settings \
  --output /private/admin-status.json
```

模擬配送の結果には必ず`--simulated`を付ける。実機試験済みの印ではなく、模擬か実サービス接続かを示す項目である。

7. 配送側から作成したレポートをWordPress側の公開ディレクトリ外へ読み取り専用で配置し、`wp-config.php`で固定パスを設定する。

```php
define('OWR_NOTIFICATION_STATUS_FILE', '/private/owr/admin-status.json');
```

画面から任意URLやファイルパスを指定させない。試験では専用ファイルをコンテナに読み取り専用マウントした。本番のレポート転送・権限分離・定期更新は未配置。レポートが900秒以上古い、未来時刻、別サイト、違う設定版、有効な宛先の欠落の場合は現在の配送状態として表示しない。

## 検証方法

```sh
python3 tools/run-notification-admin-lab.py --output /tmp/owr-admin-new-result
python3 -m unittest discover -s tests -p 'test_notification_admin_bridge.py' -v
```

前提はWSLのDockerと、既に準備した`lab/m1/images.env`のWordPress/MariaDBイメージ、およびローカルの`selenium/standalone-chrome:latest`。自動ダウンロードはしない。実行ごとに専用コンテナ名を生成し、外部通信できないネットワーク名前空間に配置する。公開ポートはなく、HTTPクライアントとChromiumもその中で実行する。終了時に今回作ったコンテナだけを削除する。

実WordPressでのログイン・フォームPOST・権限拒否・設定競合・状態表示、デスクトップ/スマートフォン幅の描画を試す。外部アダプターは模擬し、実通知・既存サーバー変更はしない。結果JSONと画面キャプチャを出力する。

## 残る範囲

稼働済み設定の版移行と画面からのテスト送信要求は[次段階の実装](notification-live-switch.md)で専用環境検証済み。受信者本人の確認を伴う「配信試験済み」認定、秘密値の登録支援、外部レポートの安全な自動配送、独立watchdogの状態表示は次段階。未実装の機能をボタンで成功扱いしない。独立watchdogの接続状態は画面上で「未確認」と表示する。

サイト侵害時はWordPress画面そのものを信頼の起点にしない。外部での配送記録・独立監視を維持する。今回のUIは初回設定と可視化の試作であり、一般利用者向けの完全自動セットアップや本番リリース判定ではない。

実装時の参照：[WordPress管理メニュー](https://developer.wordpress.org/reference/functions/add_menu_page/)、[WordPress nonce](https://developer.wordpress.org/apis/security/nonces/)。
