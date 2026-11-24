# community履歴77までのrc.20隔離復旧 / Isolated recovery through history 77

確認日：2026-11-24 JST。既に完了した隔離確認の記録です。この文書反映では本番サイト・S3にアクセスしていません。

## 対象と方法

- communityの既存の初回保存と正式履歴1〜77を使用。dmの読取り専用ロールで取得した固定版コピーを、ハッシュ照合して読み取りました。
- GitHub公開済みrc.20 ZIPをそのまま使用。SHA-256: `90849e809d215b9472fba3c36226a171fffb432922cf7aaf6eb14ea1a516e610`。コードの上書き補正はありません。
- dmにネットワーク分離したDocker復旧先を2つ用意しました。WordPress 7.1.4 / PHP 8.3、信頼できるテーマ・必要なプラグインを事前に通常どおりセットアップしました。
- 復旧後の新しい初回保存と編集内容は、新規の試験専用プレフィックスへ制限付きホスト中継で実S3保存しました。本番保存先への書込み権限は試験WordPressへ渡していません。
- 保存・復旧はWordPress APIと通常フック、表示確認は内部HTTPを使用しました。メール送信・定期保存・自動削除は無効です。

## 確認結果

| 確認 | 結果 |
|---|---|
| 初回保存＋正式履歴77からの復旧 | 94投稿。確認用ページの従来の追記とrc.20更新後の追記を表示で確認 |
| 添付原本 | 対象51件に原本不足なし。公開12件、保留39件 |
| ファイル直接URL | 公開12件はHTTP 200、保留39件はHTTP 404。保留原本は非公開で保持 |
| 復旧後の利用 | 確認用ページの表示・編集、表の読込み、ウィジェット描画を確認 |
| 再保存 | 新しい試験用初回保存とページ追記を実S3へ保存 |
| 再復旧 | 別の隔離サイトへ試験履歴26まで復旧。94投稿、本番の追記と試験用追記を確認 |
| 往復の一致 | 対象本文、ファイル内容・閲覧条件、ページの会員閲覧条件が一致 |
| 準備済み設定 | 両復旧後・再保存後とも維持 |
| ソフトウェア | 両復旧でファイル不変、install.php等の読込みなし。WP-Members初期化の禁止ガードに抵触なし |
| 保存状態 | 観測時点で未完了保存・添付エラーなし |

再復旧の「履歴26」は新しい試験保存先の履歴番号です。本番履歴77を巻き戻した意味ではありません。集計結果の `production_append_and_trial_append_present.first` は、最初の復旧先で**再保存後**に観測した状態です。

## 保全と確認範囲

- 既存S3の638版・10,993,297 bytesについて、実施前後のキー・版ID・ETag・サイズ・最新版フラグを照合し、不変を確認しました。
- 新しい試験S3の480版も再復旧前後で不変でした。原本と試験資産は削除していません。
- 所有する試験用コンテナ・ネットワーク・ボリュームは終了・除去しました。既存サービスは変更していません。
- 最初の復旧で未適用272件、再復旧で133件を適用結果として残しています。全設定を復元したという意味ではありません。今回これらを新たに分類・解消したとはしていません。
- 全画面のブラウザ操作、実会員のログイン、問い合わせの送信・メール配送、あらゆるプラグインの表示経路は今回の確認範囲外です。51件の原本・閲覧条件の結果も、このcommunity復旧点の対象についての確認です。
- 本番サイト、既存原本・履歴、ZIP・タグは変更していません。WordPress.org送信・審査メール返信は保留で、rc.20は未提出・公開未承認です。

[往復結果](../../evidence-public/community-rc20-history77-20261124/roundtrip.json) / [保全確認](../../evidence-public/community-rc20-history77-20261124/preservation.json) / [先行する本番更新・保存確認](community-rc20-20261124.md)

公開するのは集計結果だけです。原本コピー、実サイトの本文・会員情報、認証情報はリポジトリに含めません。

## English

The exact rc.20 ZIP restored community's initial Baseline and formal history through 77 in isolated Docker. Source objects were a hash-verified fixed-version copy obtained with a read-only role. The 94 restored posts included both production verification-page appends. All 51 registered file originals were available: 12 public files returned HTTP 200; 39 held files returned HTTP 404 at direct URLs and remained privately retained.

A fresh scoped real-S3 Baseline and a page edit were saved from the first destination. Recovery into a second destination through trial history 26 preserved both production and trial appends. Selected content, media bytes/access states and page restrictions matched. Prepared settings, table loading and widget rendering passed. Neither recovery installed or initialized plugins or changed software files. No pending saves or attachment errors were observed.

The original 638 S3 versions (10,993,297 bytes) remained unchanged. The 480 trial versions were unchanged by recovery. Owned trial containers/networks/volumes were removed; original and trial assets were retained. Production, existing originals/history, ZIPs and tags were not changed. Submission and review reply remain on hold; rc.20 is not submitted or approved.

These are API/hooks/internal-HTTP checks, not a complete browser walkthrough, member-login or inquiry-delivery test. The 272/133 non-applied entries remain application reports; this task does not claim all settings were restored or those entries were newly resolved. The 51-file result is specific to this recovery set. This documentation-only follow-up publishes aggregates, not private source data.
