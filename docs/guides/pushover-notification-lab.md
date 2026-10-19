# Pushover通知アダプター：専用環境と実機設定

2026-10-19。Pushoverは最初の検証対象として採用。利用者に必須契約を課す決定ではない。これはWordPress Resilienceの外部監視・通知の試作であり、WordPress管理画面の通知設定機能はまだ未実装。

## 製品と検証環境の境界

製品の通知機能は「事件の発生・解消」「宛先と配送状態」「サービス別アダプター」に分ける。利用者がメール、Pushover、Slack、LINE、PagerDuty等を選べる方向で設計する。今回実装済みなのはSMTPとPushoverの試験用配送。その他を対応済みと表示しない。

community、dm、Googleメール、大関さんのアカウントは検証事例。利用者にこれらのサーバーや同じ契約を要求しない。外部watchdogが必要なのはWordPress自身の停止をサイトの外から検知するためであり、その配置方法は利用環境で選ぶ。

LINEやSlackは、既に使っている利用者に新しいアプリを求めずに済む点で重要な候補。ただしチャットへ投稿できることと、担当者の確認・未確認時の引継ぎができることは分けて扱う。LINE Notifyは2025-03-31に終了済み。LINE対応を実装する場合は公式アカウントのMessaging API、宛先登録、利用枠・課金を設計する。[LINE公式](https://developers.line.biz/en/news/2025/04/01/line-notify/)、[Messaging API](https://developers.line.biz/en/docs/messaging-api/overview/)。SlackはIncoming Webhookによる送信を候補とし、確認操作を加える場合は別の連携が必要。[Slack公式](https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/)

電気設備監視の多数ユーザー運用では、設備・顧客ごとの宛先分離、当番、一次対応と引継ぎ、操作権限、通知量、監査・費用を追加要件にする。PagerDutyは当番とエスカレーションを持ち、別の評価対象として適している。[公式仕様](https://support.pagerduty.com/main/docs/escalation-policies)。設備監視本体への組込みや通知サービスの選定は今回行わない。共通化候補は通知イベント契約と配送アダプターであり、顧客データや資格情報を共有しない。

## 実装と状態

- `tools/pushover-adapter.py`：固定HTTPSエンドポイント、証明書検証、リダイレクト禁止、所有者専用の資格情報ファイル。緊急送信、確認照会、再通知取消。
- `tools/notification-dispatch-lab.py`：既存monitor/watchdogのSQLite outboxを読み取り専用で取り込み、宛先ごとに独立した永続配送状態を作る。SMTPが失敗してもPushoverを試行する。異なる宛先の失敗も分離する。
- 発生イベントはPushover緊急通知、解消は通常通知。push側の`kinds`で重要警報を絞る。メールには全種類を渡せる。
- `accepted`はAPI/SMTPの受付であり、端末表示や人の確認ではない。receiptは`waiting`、`acknowledged`、`expired`、`cancelled`を記録。確認は事件の解消・署名承認にはならない。
- 429は待機して再試行。再送間隔は60秒から最大1時間。400等の拒否は`rejected`、タイムアウト・5xx・送信途中のプロセス終了は`unknown`。重複した緊急通知を避けるため、unknownの自動再送はしない。
- receipt照会は通常60秒以上、失敗後300秒以上の間隔。照会・取消の失敗は`poll_error`として表示する。解消済みの未送信発生通知は`superseded`とし、古い警報を新たに鳴らさない。
- 設定は状態DBへ固定。変更を検知すると停止する。既存状態の削除による設定変更・再送は行わない。資格情報は同じファイルパスで更新できるが、別アプリ・別宛先への切替は既存receiptとの対応を含む明示的移行が必要。

**制限**：これは専用環境の一回実行ワーカー。既存監視の`undelivered`と新しい配送状態の統合、永続エラーの独立監視、unknownの照合・再送操作、設定移行UI、当番・別担当への自動引継ぎ、送信量制御の本番運用は次段階。unknown/rejectedを放置して実運用へ進めない。既存SMTPスケジューラーと同じ事件を同時配信すればメールが重複するため、試験では既存スケジューラーを接続しない。

## 専用環境での自動試験

WSL UbuntuのPython標準ライブラリで実行する。外部ネットワーク呼出しは模擬し、資格情報もダミーを使う。

```sh
cd /mnt/d/workspace/ozeki-wordpress-resilience
python3 -m unittest discover -s tests -p 'test_notification_dispatch_lab.py' -v
```

配送分離、再起動、429待機、応答喪失、確認と解消の区別、取消、期限切れ、照会失敗、古い発生通知の抑止、種類別配送、元DBの非変更、設定・イベント競合、送信内容の最小化、資格情報権限を検証する。実際のPushover配信やスマートフォン動作の試験とは区別する。

## 実機用の登録

1. スマートフォンへPushoverをインストールし、[Pushover](https://pushover.net/)で本人のアカウントを登録する。iPhone/Androidの通知許可を有効にする。料金と試用期限は[料金ページ](https://pushover.net/pricing)で確認する。
2. WebのダッシュボードでUser Keyを確認する。共有の開発者キーを製品に埋め込まず、利用者自身が[アプリケーションを登録](https://pushover.net/apps/build)する。名前の例は`OWR isolated lab`。発行されたAPI Tokenを控える。
3. User KeyとAPI TokenはチャットやGitへ貼らない。今回のキーをWordPress保存元や既存サーバーへ自動配布しない。
4. WSLのLinuxホーム内に秘密ファイルを作る。Windowsマウント配下より、Linuxのファイル権限を使える場所を選ぶ。

```sh
umask 077
mkdir -p "$HOME/.config/owr-notification-lab" "$HOME/.local/state/owr-notification-lab"
nano "$HOME/.config/owr-notification-lab/pushover.json"
chmod 600 "$HOME/.config/owr-notification-lab/pushover.json"
```

エディターで次の値を本人が置き換える。シェルのコマンド履歴へ秘密値を入力しない。

```json
{"token":"YOUR_APPLICATION_API_TOKEN","user":"YOUR_USER_KEY"}
```

## 実機用の設定例

`examples/monitoring/pushover-lab.example.json`をコピーし、`/home/YOUR_USER`を実際のホームの絶対パスへ置換する。アダプターは`~`や`$HOME`を展開しない。

```sh
cp examples/monitoring/pushover-lab.example.json "$HOME/.config/owr-notification-lab/dispatch.json"
nano "$HOME/.config/owr-notification-lab/dispatch.json"
```

`source_outbox`は専用試験用のSQLiteファイル。monitor/watchdogのoutbox形式に合わせ、初回は次の模擬事件だけを作る。本番台帳を指定すると過去の事件も取り込むため使用しない。

```sh
python3 - <<'PY'
import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
p = Path.home()/'.local/state/owr-notification-lab/source.sqlite'
with sqlite3.connect(p) as db:
    db.execute('CREATE TABLE IF NOT EXISTS outbox(payload TEXT)')
    if db.execute('SELECT count(*) FROM outbox').fetchone()[0]:
        raise SystemExit('Existing test events found; not adding another emergency.')
    event = dict(event_id=uuid.uuid4().hex, site='OWR isolated test', domain='lab',
                 kind='backup_missing', subject='phone-test', transition='opened',
                 observed_at=datetime.now(timezone.utc).isoformat())
    db.execute('INSERT INTO outbox VALUES(?)', (json.dumps(event),))
PY
```

以下の実行は**実際に本人の端末へ緊急通知を送る**。例では60秒ごとに最大5分間繰り返すため、端末を手元に置き、試験時間に実行する。

```sh
python3 tools/notification-dispatch-lab.py --config "$HOME/.config/owr-notification-lab/dispatch.json"
```

端末で確認操作をし、60秒以上経過後に同じコマンドを再実行して`receipt_state: acknowledged`を確認する。同じ事件を再送せず、receiptだけを照会する。`accepted`しか出ていなければ、人が確認したことまでは証明していない。

解消試験では、同じsite/domain/kind/subjectで`transition`を`resolved`へ変え、新しいevent_idと時刻を付けた行をsource.sqliteへ追加する。ワーカーを再実行し、未確認通知の取消と解消通知を確認する。試験用DBを消して繰返し通知を止めることはできない。アプリで確認するか、receiptの取消・設定した期限の到来を使う。

```sh
python3 - <<'PY'
import json, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
with sqlite3.connect(Path.home()/'.local/state/owr-notification-lab/source.sqlite') as db:
    rows = db.execute('SELECT payload FROM outbox ORDER BY rowid').fetchall()
    if len(rows) != 1:
        raise SystemExit('Expected one opening test event; refusing duplicate resolution.')
    event = json.loads(rows[0][0])
    event.update(event_id=uuid.uuid4().hex, transition='resolved',
                 observed_at=datetime.now(timezone.utc).isoformat())
    db.execute('INSERT INTO outbox VALUES(?)', (json.dumps(event),))
PY
```

ワーカーは単発実行なので、取消・確認照会も再実行時に進む。receipt照会間隔内なら60秒以上経過後に再度実行する。実機試験の間も自動タイマーは追加しない。

## 実機の合格条件

画面ロック、バックグラウンド、集中モード・夜間、端末の一時的な通信断を本人の端末で確認する。確認後に繰返しが止まること、解消時に取消されること、期限切れが未確認として表示されることを記録する。消音状態でも必ず鳴るとは扱わない。API受付だけで合格にしない。

Pushoverの緊急再通知・確認・取消の根拠：[API](https://pushover.net/api)、[receipt API](https://pushover.net/api/receipts)。この手順を用意した時点では登録・実通知・サーバー配置・定期実行の有効化は行っていない。

## 後続の通知健全性試作

通知失敗と配送処理停止の監視は[専用環境の健全性機構](notification-health-lab.md)へ進めました。配送用heartbeatを独立watchdogへ接続する方式で、通常監視の状態DBとは分離します。実機試験用設定の変更や追加の実送信は行っていません。
