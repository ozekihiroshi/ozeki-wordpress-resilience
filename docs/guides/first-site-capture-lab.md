# 最初のサイト構成：収集設定と取得アダプターの専用試験

2026-10-20。外部Python取得処理の初期実装。WordPressプラグインの取得画面や本番の収集サービスではない。既存72時間観測の三資産fixtureとは別のコンテナ・台帳・出力を使い、S3・本番サイト・IAMへ接続しない。

## 実装した入口

- `tools/first-site-capture.py validate --config FILE`：設定の読取り検査。format、対象、必要更新元、停止上限、担当、外部依存、役割参照を検査し、正規化JSONのSHA-256を返す。未知の項目も拒否する。秘密の値を設定へ追加しない。
- `capture(config, expected_config_hash, backend, state_root)`：独立に指定された設定ハッシュを照合してから、サイト排他、事前確認、停止・排出、ストリーム取得、一覧・スキーマ・通常添付参照検査、停止解除、結果記録を行う。公開CLIは設定検査のみで、任意サイトを捕まえるCLIは未提供。
- `tools/first-site-docker-lab.py`：専用生成コンテナのみを扱う実接続。名前・専用ラベル・ネットワーク・mount範囲・PHP受付制御を確認する。ラベルは悪意あるDocker管理者に対する信頼境界ではない。
- `tools/run-first-site-capture-lab.py`：新規コンテナで実WordPress/MariaDBの専用受入を実行。既存の継続試験起動スクリプトは呼び出さない。既存のgate/prepend fixtureを読取り再利用する。

[設定例](../../examples/first-site/generated-lab.json)は専用試験用。保管と署名の参照は未接続を明示している。実サイトへ参照値を置換するだけで利用できる構成ではない。現接続はlab DB、wp_ prefix、/var/www/html固定。SQLコマンドへ任意の設定を埋め込まない。

## 試す手順

WSL Ubuntuのリポジトリルートで、まず設定のみを確認する。

```sh
python3 tools/first-site-capture.py validate --config examples/first-site/generated-lab.json
python3 -m unittest discover -s tests -p test_first_site_capture.py -v
```

実取得試験はDockerと`lab/m1/images.env`のローカルイメージを使用する。毎回、新しい出力名を選ぶ。既存の結果・active台帳を削除して再試行しない。

```sh
mkdir -p "$HOME/.local/share/owr-first-site-local"
chmod 700 "$HOME/.local/share/owr-first-site-local"
python3 tools/run-first-site-capture-lab.py --execute-lab \
  --output "$HOME/.local/share/owr-first-site-local/first-result.json"
```

WordPressとDBは外部通信・公開ポートのないネットワークを共有する。コンテナ名はowr-first-site-で始まる。取得物はWSL側の新規privateディレクトリへストリームし、保存元に大きなアーカイブを作らない。生成データのDB/設定にも使い捨て認証情報が含まれるため、privateディレクトリの原本をGitへ追加しない。

## 設定と実行時の拒否条件

単一サイト、InnoDB、ローカルファイル、外部キューなしを初期対象とする。除外一覧は現在空のみを受け付ける。外部依存・マルチサイト・非対応エンジン・不完全な更新元一覧・役割の同一参照・停止時間や代替担当の欠落を拒否する。運用設定だけで経路が実際に制御できると判断せず、専用接続が実行時のスコープを照合する。

DB内の通常のWordPress添付メタデータを読み、_wp_attached_file、_wp_attachment_metadataのfile/sizes/original_imageが取得ファイルに存在するか検査する。通常投稿と添付参照のDB再読込みも試験する。全プラグイン固有データ、投稿HTML内の任意URL、外部サービス依存を自動発見する機能ではない。DB内キューや独自プラグインを含む任意サイトの適合判定は未提供。

取得ファイルの全ハッシュを取得前後とtar内で照合。リンク・特殊ファイル・不正パス・重複メンバー・展開容量超過を拒否し、その時点では展開しない。標準添付参照が欠落した場合はinconsistent。取得済みSQLの汎用リストア検証はcapture自体には含めず、専用試験で別工程として行う。

## 台帳と状態

状態領域は実行ユーザー所有0700、取得物は0600。設定は処理開始前に固定ハッシュと照合。サイトごとのflockとactive記録で二重起動を拒否する。解除不明ならactiveを残し、次回はprior_attempt_requires_reconciliationで拒否する。プロセス強制終了後も自動的に台帳を消さない。

結果はowr-first-site-capture-v1。資産はdatabase/filesの2種類で、queue.state=absentと調査根拠を明記する。既存三資産の署名付きRecovery Setと互換なmanifestではない。storage_complete/signed/restore_verified/production_recovery_approvedはすべてfalseのまま。

取得の不整合、証拠不足、生成失敗を分け、解除失敗時は取得側判定を別フィールドに残して全体をcapture_failedとする。PHP gateの期限・接続切断時解除を使い、コントローラー側も停止期限を確認する。停止状態の確認は転送中0.5秒間隔と終端、時刻上限は各ブロックで検査する。サーバー喪失や悪意ある管理者、全プロセスの強制停止を網羅した独立監視ではない。

## 検証の分類と残作業

新規設定/取得アダプターの不具合は外部取得処理の製品課題として修正する。試験スクリプトやDocker/WSLの起動障害は対象を分けて記録し、製品機能合格へ補完しない。最初の試行ではブロックごとのDocker確認が転送を遅くして停止期限へ到達した。アダプターの実装課題として修正し、期限や成功条件は緩和しなかった。元の失敗結果はunverified・解除済みとして保管する。

残作業は汎用ホスト向けの更新元調査・停止/解除接続、設定の独立承認運用、通常WPの参照検査範囲拡張、キューなし取得物のS3固定版/保持/独立署名/隔離復元への接続、導入UI。取得成功をバックアップ保管・侵害後安全性の完成とは扱わない。既存0.1.0-dev.1配布物は変更しない。

## 今回の実測

新規契約14テスト（通常・最適化実行とも成功）、既存整合性契約9テスト、専用実WordPress/MariaDBで7ケースを確認。件数は対象が違うため合算しない。生成データだけを使用し、専用資源の削除も確認した。[公開集計とソースハッシュ](../../evidence-public/first-site-capture.json)。解除失敗・容量不足・台帳排他は契約試験、HTTP/DB停止・取得・DB読込み・ダンプ失敗・期限失効・制御切断・添付欠落は実接続試験として区別する。

停止期限は単調時計と実時刻の両方を検査する。時計の前進・逆行で許容範囲を外れればunverified。休止後の時刻飛躍を模擬した拒否試験を追加した。実際のホスト休止を意図的に発生させた受入試験ではない。

### 2資産の後続工程（2026-10-20）

上記の取得原本を変更せず、[別契約のS3・署名・復元試験](first-site-s3-recovery-lab.md)へ接続した。生成データの専用環境で検証済み。一般サイト導入・日次運用への統合は残る。

### タイムアウト調査による更新

停止確認中も出力を読み続ける外部匿名一時保管を追加した。停止前にホスト側で2×max_bytes+reserve_bytesの空きを確認する。停止確認の次回は完了から0.5秒後。工程別時間とタイムアウト箇所を秘密情報なしで記録する。[原因と比較試験](first-site-timeout-investigation.md)。過去の集計・ソースハッシュは当時の記録として保持する。
