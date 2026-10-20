# 生成側・取得側の独立watchdog管理画面

通知管理メニュー配下の「生成・取得の独立監視」を開きます。管理者権限（manage_options）が必要です。読取り専用で、警報解除・再送・署名・復元・設定変更は行いません。

## 表示内容

生成側と取得側それぞれに、SSH到達性、状態報告の最終更新、発報中の警報、通知引渡し待ち、配送処理の状態、最近20件までの警報発生・解消履歴を表示します。

報告が5分以上古い場合は「現在の状態は不明」と表示し、履歴と状態は前回記録として残します。一方の報告が欠けても他方は表示できます。サイトID・監視対象IDの不一致、未来時刻、壊れたJSON、サイズ超過は正常扱いしません。

「解消」は警報条件が解消した記録です。通知サービスへの配送成功、iPhone等の端末受信、担当者の確認とは別です。配送状態がunknownなら未確認と表示します。サイト自体が停止すると画面を見られないため、外部watchdogの通知運用を継続してください。

## 外部側からの受渡し

既存の [日次watchdog](daily-watchdog.md) の各observer設定に、対象ごとに異なる public_status_file と、WordPressサイトと一致する admin_site_id を設定します。各observerは owr-observer-status-v1 の制限された報告を生成します。

既存の [watchdog手順](watchdog-observer.md) と tools/observer-status.py の固定コマンドSSH pullを使い、生成側・取得側の報告を別ファイルへ取得します。サイト側に置くのは公開用の状態報告だけです。署名鍵、通知キー、watchdogのSQLite台帳をWordPressへ渡しません。

WordPressのwp-config.phpへ、管理者が固定したパスと監視IDを指定します。

    define('OWR_DAILY_SITE_ID', 'your-site-id');
    define('OWR_DAILY_WATCHDOG_REPORTS', [
        'source' => [
            'path' => '/var/lib/owr-status-web/source-observer.json',
            'monitor_id' => 'daily-source',
        ],
        'receiver' => [
            'path' => '/var/lib/owr-status-web/receiver-observer.json',
            'monitor_id' => 'daily-receiver',
        ],
    ]);

monitor_idはそれぞれ外部observerの設定と一致させます。報告を入れ替えると拒否されます。既にOWR_DAILY_SITE_IDがある場合は重複定義せず、その値を使ってください。報告はWeb公開ディレクトリ外に配置し、WordPressには読取りだけ許可します。取得側で原子的に更新し、HTTP要求時にSSHや外部処理を起動しません。

従来のOWR_OBSERVER_STATUS_FILEを利用する既存watchdog画面はそのまま利用できます。今回の2対象の設定とは独立しています。

## 検証範囲

専用WordPress/MariaDBと実Chromiumで、manage_options、未ログイン、低権限、POST拒否、読取り専用性、状態・履歴の表示を検証します。外部observer自身が生成した試験報告と、明示的な表示異常fixtureを使用します。通信・配送は模擬で、今回の画面試験では実S3保存、実通知、VM障害注入を繰り返しません。前段の実VM試験と画面受入は別の証拠です。

実行入口は tools/run-daily-watchdog-admin-lab.py --output ＜新しい専用フォルダ＞。既存観測や過去の試験フォルダを再利用しません。

専用環境の12ケースを実ブラウザで確認済みです。各ケースで未ログイン・管理者・編集者・POST拒否を確認し、初回のWordPress自身の初期化後に設定・Cron・要求ファイル・observer台帳の不変を確認しました。PHP契約試験10項目、既存observer契約試験9項目も通過しています。

初回試験は8番目のケースのログイン待ちで停止しました。原因は未確定です。ログインの診断と入力欄の明示クリアを追加した新規環境の再試験結果と分けて保存しています。プラグイン不具合・環境不具合のどちらにも断定していません。

通知履歴は警報の発生・解消履歴と現在の配送集計です。個々の通知の配送時刻・端末受信・確認履歴はこの公開報告には含まれません。
