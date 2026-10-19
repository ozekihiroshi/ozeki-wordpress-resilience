# 稼働設定の切替と管理画面のテスト送信（専用環境版）

## 切替の契約

WordPressで保存するのは設定候補。外部運用担当が内容を確認し、明示的に適用する。サイト侵害時にもWordPressから外部の接続設定・秘密情報を自由に変更させない。今回、実サービスへの送信、本番の定期実行・転送設定は変更していない。

- 切替と配送は同じ排他ロックを使う。SQLiteの1トランザクションで、旧設定による切替時点の取込みと新経路の登録を確定する。失敗時は旧状態を保つ。
- 切替前に取得したイベントは旧設定に所属する。以降の新しい警報だけを新経路へ振り分ける。新しい宛先へ過去の全イベントを再配送しない。
- 未配送、再試行時刻・回数、結果不明、拒否、確認待ち、受付・確認履歴を維持する。結果不明を自動再送しない。
- 解消通知は、開いた警報を扱った経路へ戻す。無効化した宛先でも旧通知の確認・取消・解消を処理する。無効化は新規警報の停止であり、未配送の廃棄ではない。
- 外部の接続設定と宛先、認証情報の所有者専用コピーを版ごとに固定する。後からキーや宛先を更新しても、旧通知を新宛先へ送らない。初回移行は既存のキーを変更する前に行う。既に上書きされた旧キーを復元する機能ではない。
- 古いワーカー設定はDBとの不一致で停止する。移行後は `notification-live.py run` がDB内の稼働設定を読む。
- 画面の配送件数は旧設定分も含む。旧版のテスト受付を新版の配信試験成功として表示しない。受付は端末での受信や人の確認を保証しない。

現時点では経路は最大400件。設定の反映ごとに経路が増えるため、上限では適用を拒否して既存状態を維持する。完了済みの経路・認証情報を安全に整理する機能は今後の範囲。状態ディレクトリはWeb公開領域外、外部ワーカー専用の権限にする。

## 外部担当者の手順

既存の初回構成・配送DBがあることを前提とする。まず既存構成を同じ設定版で `apply` して管理対象へ移す。その後、管理画面からエクスポートした新しい版を適用できる。

1. 管理画面の設定候補と外部側の接続設定を照合する。外部側に保存するSMTP/Pushoverの秘密情報をWordPressへ渡さない。
2. 稼働設定のハッシュを確認する。初回は既存 `config.json` のハッシュ、その後はDB内の設定のハッシュを使う。以下はプロジェクトルートでの読取りのみの例。

```sh
python3 - <<'PY'
import importlib.util
s = importlib.util.spec_from_file_location('live', 'tools/notification-live.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
print(m.load('notification-admin-bridge').digest(m.current('/private/delivery')))
PY
```

3. 新しい出力ディレクトリに候補を生成する。`--migration` は稼働DBを変更しない。`--include-existing` は既存sourceを使うことの確認であり、移行時に過去のイベントを新経路へ再配送する指定ではない。

```sh
python3 tools/notification-admin-bridge.py compile \
  --settings /private/exported-settings.json \
  --profiles /private/profiles.json \
  --source-outbox /private/source.sqlite --state /private/delivery \
  --output /private/candidate-revision-2 --migration --include-existing

python3 tools/notification-live.py apply \
  --compiled /private/candidate-revision-2 \
  --expected-hash 確認した稼働設定のSHA256
```

初回の同一版移行では既存のコンパイル済みディレクトリを `--compiled` に指定できる。同じ候補の再適用は経路を重複作成しない。異なるサイト、古い版、古い稼働ハッシュは拒否する（初回のサイトとの紐付けは外部担当者が確認する）。切替直後は新しいワーカー処理が完了するまで、最新状態のレポートを発行しない。

4. 以後は新しい実行入口を使う。実際の接続設定を使う場合、このコマンドは外部通知を送る。

```sh
python3 tools/notification-live.py run --state /private/delivery \
  --requests /private/owr-test-requests --status /private/admin-status.json
```

## 管理画面のテスト送信

Web公開領域外に専用要求ディレクトリを用意し、WordPress実行ユーザーだけに書込み、外部配送プロセスに読取り・消費の権限を与える。実サービスでは外部ホストへの要求転送と戻りの状態転送が必要。今回は専用コンテナの共有ディレクトリで検証した。WordPressから外部ワーカーのDB・認証情報・接続設定にアクセスさせない。

```php
define('OWR_NOTIFICATION_REQUEST_DIR', '/private/owr-test-requests');
define('OWR_NOTIFICATION_STATUS_FILE', '/private/admin-status.json');
```

要求ファイルは0640で作成する。専用グループとsetgidディレクトリ等で外部読取りを許可する。全ユーザー書込み可にはしない。状態レポートはWordPressから読取り専用。

1. 画面で「外部配送の報告を受信」を確認する。設定未反映・古いレポート・無効な宛先ではテストを受け付けない。
2. 「○○へテスト送信」を押す。管理者権限、POST、nonce、設定版を検証し、要求IDを保存する。この時点では「外部配送の処理待ち」。
3. 外部ワーカーが承認済みの稼働設定と照合し、固定のテスト本文を通常優先度で送信する。画面からURL・キー・任意本文・別の宛先は指定できない。
4. 外部レポート反映後に画面を再読込みする。「サービス受付」になったら端末で受信を確認する。端末確認済みの認定はまだ自動化しない。

同じ要求IDは再送しない。1宛先につき60秒間隔、要求期限300秒、要求ファイル最大100件。外部側でも頻度・版・サイト・宛先を検証する。処理済み要求ファイルは消費し、結果は外部DBに残す。送信中の中断は結果不明として保持し、盲目的に再送しない。結果不明・拒否・一時失敗は画面で確認し、新しいテストを手動で要求する。通常警報の再試行処理とは分けている。

## 検証と残る範囲

```sh
python3 -m unittest discover -s tests -p 'test_notification*.py'
python3 tools/run-notification-admin-lab.py --output /tmp/owr-admin-new-result
```

使い捨てのWordPress、MariaDB、Chromiumを外部通信不可・公開ポートなしで動かす。プロバイダー呼出しだけを模擬し、実キー・実宛先を使わない。切替失敗のロールバック、未配送・確認待ち・結果不明の保持、キーの版固定、旧ワーカー拒否、テストの重複・期限・権限・nonce・設定版・頻度と画面表示を検証する。

外部ホスト間の要求・レポート転送は[専用SSH受渡し](notification-transfer.md)で実装・専用環境検証済み。定期実行への本番配置、完了した旧経路の整理、受信者本人による確認の登録、独立watchdogの画面統合は未実装・未配置。WordPressが停止しても外部監視が継続する設計は維持する。
