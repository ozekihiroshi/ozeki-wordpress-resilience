# User-guide onboarding acceptance / 利用ガイドによる初回導入確認

2026-10-26. Work type: existing-feature verification and evidence organization. State: verified with limitations. Completion: browser installation, Baseline, a normal edit and confirmed history, separate-site recovery, comparison and documented obstacles. This record reports the completed trial; the documentation PR adds no tests or product changes.

作業種類：既存機能の検証・エビデンス整理。状態：検証済み・制限あり。完了条件：管理画面から導入・Baseline・通常編集・正式履歴・別サイト復旧・照合を確認し、補助手順を記録。今回のPRは既存結果の文書化のみです。

## Package and method / 配布物と方法

Published `ozeki-wordpress-resilience-0.3.1-pre.2.zip`, 7,455,881 bytes, SHA-256:

`109f0db79f1e5b0886b11d6ebcb2df0f4728912baa1217f977de91760b0b3d0a`

Existing community/dm containers and DB services were reused with separate trial tables/content. PHP 8.3.36, WordPress 7.1.3; no core update was performed. Standard browser plugin upload/install/activation was used on both sites. Source S3 writes were confined to a new, previously empty child prefix; existing objects were not modified. Both environments used existing EC2 roles through SDK standard authentication. Cron, updates and mail were blocked by trial configuration, and GFS/cleanup stayed off.

既存community/dmのコンテナ・DB内で専用テーブルとコンテンツ領域を使い、両サイトとも標準管理画面で公開済みZIPを導入。有効な既存EC2ロールとSDK標準認証を使用しました。既存資産とは分けた空の子prefixだけに保存し、Cron・更新・メールを試験設定で抑止、GFS・削除は無効です。製品コード・公開済みZIP・IAM・既存コンテンツの変更、実削除、リリース公開はありません。

## Verified flow / 確認結果

| Step / 操作 | Result / 結果 |
|---|---|
| Baseline | First attempt stopped with `Dependency must be an active plugin.` After activating existing Markdown Documents 0.1.1 in the isolated source, succeeded at through=0. / Markdown Documents有効化前は失敗として停止、有効化後に成功 |
| Normal edit / 通常編集 | Standard post code editor saved a substantial trial article and a page link. Confirmed history 1 (body) and 2 (related information), pending=0. / 標準コードエディターで本文・リンク更新、本文と付随情報の履歴1〜2確定、未確定0 |
| Recovery / 復旧 | Browser selected Baseline + end 2; success with history 1–2, 4 post records (not four public articles), 516 files. / 管理画面で基点と終了2を選び復旧成功 |
| Application rules / 適用規則 | 18 widget-related items withheld with reasons; not reported as silently applied. / widget関連18項目は未適用理由を結果表示 |
| Comparison / 照合 | Post 1 and Page 2: title, publish status and type equal; body equal after site-URL mapping. Edited link opened the restored Page. Logout and re-login succeeded. / タイトル・公開状態・型一致、URL置換を除く本文一致、リンク遷移・再ログイン成功 |

Baseline confirmed at 2026-10-26T00:40:58Z; history 1/2 at 00:41:57Z/00:41:58Z; recovery success at 00:45:46Z. The destination used S3 resources, not the source DB as recovery input.

## Findings and scope / 不足と検証範囲

1. **Product dependency versus guide:** the admin Baseline handler in `packages/markdown-m1/src/Plugin.php` passes Markdown Documents as a required dependency to `SiteSnapshot::capture`; the active-plugin check rejects its absence. This applies even to native-only sites. The guide now states the prerequisite; changing the dependency is outside this documentation change. This was not an unassisted-guide pass.
2. **Upload environment:** dm initially rejected the ZIP at the PHP upload limit. Trial-entry-only settings of 16M upload/20M POST allowed installation; shared PHP configuration was not changed. These are the tested adjustment, not universal required values. The guide now checks PHP and web-server limits before uploading.
3. **Browser/test setup:** the in-app visual canvas issue required the standard code editor. Isolated-entry symlink routing needed environment preparation. A read-only evidence collector used mysqli because PDO MySQL was absent. None establishes a product regression. The initial sample page retained a setup-era URL outside the current source base; the deliberately edited page link was verified. No claim covers arbitrary historical URLs.
4. **IAM boundary:** complete policy JSONs were not applied anew. Source permissions were broader than source-no-delete. Recovery-role ListBucketVersions returned 403, while current listing and the fixed-version reads used by this recovery succeeded. No IAM change was needed. This is not proof that the exact sample policies were deployed or that all permissions were exercised.
5. **Not repeated:** all supported plugin combinations, visual editing, new media, fault injection, scheduling and deletion were not retested. Successful recovery need not be repeated just for these documentation corrections.

1. **製品依存と案内の不一致：** 管理画面のBaselineはMarkdown Documentsを必須指定し、有効化を検査します。通常投稿だけでも必要です。英日ガイドに反映しましたが、依存仕様は変更していません。補助なしの導線合格とはしません。
2. **容量条件：** dmのPHP上限で最初のアップロードが失敗。試験入口のみ16M/20Mへ調整し成功しました。共有設定は不変で、この値を全環境の必須値とはしません。ガイドで送信前の条件確認へ案内します。
3. **ブラウザ・試験基盤：** 本文キャンバス問題には標準コード編集を使用。隔離入口のルーティングや証拠採取用PDO不足は環境準備の問題です。初期サンプルの旧URLを含め、すべての過去URL変換を保証する試験ではありません。
4. **IAM：** 完全版JSONそのものの新規適用ではありません。保存側はより広い権限、復旧側は全バージョン一覧403でしたが今回必要な一覧・固定版読取りは成立し、IAM変更なしで復旧成功。この事実をサンプル権限すべての実証と混同しません。
5. **未実施：** 全プラグイン組合せ、ビジュアル編集、新規画像、障害注入、定期処理・削除を再試験していません。

[English guide](../../packages/markdown-m1/docs/user-guide.md) · [日本語ガイド](../../packages/markdown-m1/docs/user-guide-ja.md) · [Remaining confirmations / 残る確認事項](../../packages/markdown-m1/docs/remaining-confirmations.md)

Local evidence: `release-readiness/user-onboarding-20261026/RESULT-ja.md`, source-history.txt, recovery-result.txt, recovery-success.png, restored-post.txt/png and comparison.json. Private credentials and raw environment records are not included in this PR.
