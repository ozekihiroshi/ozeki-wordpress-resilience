# Ozeki Resilience 0.3.3 rc.20 — 本番導入前の候補

2026-11-24。**GitHub候補配布です。候補作成時点ではcommunity本番に未導入でした。WordPress.orgには未提出で、公開承認済みではありません。** その後、同日中にcommunityをrc.20へ更新し、履歴77まで確認しました（末尾追記）。提出済みrc.18、rc.19を含む既存ZIP・タグを保全しています。申請更新・審査メール返信は保留です。

## 今回の修正

rc.19が復旧した添付へ付ける自身の識別情報を、閲覧制限を意味しない既知の項目として扱います。この識別情報だけで、公開ファイルが再保存時に保留扱いへ変わる不整合を修正しました。許可するのは完全一致する1項目だけです。非公開状態、不明なメタ情報、継承した制限、ディレクトリの保護は引き続き判定します。

[原因と再発防止確認](../review/media-origin-marker-20261124/RESULTS.txt)。rc.19の安全な表示・編集後の実行防止、構造化データの値の維持は継続します。復旧先には信頼できるソフトウェアを別途準備し、復旧処理はインストール・初期化をせず、準備済み設定を維持します。

## ZIPと対応ソース

- [導入ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.20/ozeki-resilience-0.3.3.zip)
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.20)
- SHA-256: `90849e809d215b9472fba3c36226a171fffb432922cf7aaf6eb14ea1a516e610`
- 8,320,939 bytes / 3,820ファイル。ビルド元 `a4bb22f`。後続変更は配布対象外の確認記録のみです。
- rc.19との差分はFileScope.php、日英README、更新ガイドの4ファイル。依存ライブラリは不変。8ガイドと相対リンク86件を確認し、開発資料・試験は同梱していません。

## 完成ZIPの確認

| 項目 | 結果 |
|---|---|
| Plugin Check 2.2.0 | エラー0、警告123。全警告はrc.19と同一。抑制せず記録 |
| 新規導入・rc.19からの更新 | 成功。設定、記事・会員等のDB状態、有効化状態を維持 |
| 日英管理画面 | PHPでの描画確認で警告なし |
| ZIP整合 | 導入後・試験後とも全3,820ファイルがZIPと一致。製品44ファイルが対応ソースと一致 |
| community初回保存＋正式履歴76 | 94投稿を復旧し、確認用ページの追記を確認 |
| 添付原本と閲覧条件 | 対象51件の原本不足0。公開12件はHTTP 200、保留39件は直接URLでHTTP 404 |
| 実S3への再保存・再復旧 | 新しい試験専用保存先へ初回保存・追記し、試験履歴26まで再復旧。本文・ファイル内容・閲覧条件が一致 |
| 準備済み設定 | 両復旧後と再保存後に維持。表の読込み・ウィジェット描画も確認 |
| ソフトウェア | 両復旧でファイル不変、install.php読込みなし。WP-Members初期化の禁止ガードに抵触なし |
| 既存S3 | 635版・10,991,173 bytesの一覧が不変。新規試験480版も復旧による変更なし |

導入・更新・Plugin Checkはdmの専用Docker（WordPress 7.1.5 / PHP 8.3.37）で実施しました。往復確認は同じcommunityの固定版原本を使う別の隔離Docker（WordPress 7.1.4 / PHP 8.3）です。完成ZIPをそのまま導入し、コードの上書き補正はしていません。原本は読取り専用の固定版コピーを用い、再保存は制限付きホスト中継から新規の実S3試験プレフィックスだけへ書き込みました。本番サイトと本番保存先への書込み、定期保存、自動削除、メール送信は行っていません。

最初の復旧の未適用272件と再復旧の133件は適用結果として残しています。すべての設定を戻したという意味ではありません。確認はWordPress API・フックと内部HTTPによるものです。全会員ログイン・問い合わせ配送・全画面の人によるブラウザ確認は今回の範囲に含みません。

[ZIP監査](../../evidence-public/wordpress-org-033-rc20/package-audit.json) / [対応ソース](../../evidence-public/wordpress-org-033-rc20/source-match.json) / [導入・更新](../../evidence-public/wordpress-org-033-rc20/rc20-install-update.json) / [Plugin Check全件](../../evidence-public/wordpress-org-033-rc20/rc20-plugin-check.json) / [実S3往復](../../evidence-public/wordpress-org-033-rc20/real-s3-result.json) / [保全確認](../../evidence-public/wordpress-org-033-rc20/preservation.json)

## 互換性と次の段階

保存形式は変わりません。既存原本・履歴の移行や上書き、新しい初回保存は不要です。今回の判定修正を使うため、復旧先にもrc.20を用意してください。以前からの添付・参照形式の読取り条件は継続します。

次は結果を確認後、同じZIPをcommunity本番へ導入して通常利用を確認する段階です。今回、本番導入・WordPress.org送信・審査メール返信は行っていません。

## English summary

rc.20 is a prerelease candidate, not deployed to community and not submitted to WordPress.org. It recognizes only our exact attachment provenance key as access-neutral. Private status, unknown metadata and inherited restrictions remain enforced. Archive formats and existing originals/history are unchanged; update recovery destinations too.

The exact ZIP passed fresh installation, rc.19 update, Japanese/English admin rendering, Plugin Check (0 errors, the same 123 warnings), and isolated real-S3 recovery/resave/recovery using community history through 76. All 51 registered file originals remain available: 12 public and 39 held. Content, media and page restrictions matched after the second recovery. Prepared settings remained intact without plugin installation or initialization. These are API/HTTP checks, not a complete human browser acceptance test. Production deployment is the next separately reviewed step.

## 本番導入後の追記（2026-11-24）

同じZIPをcommunity本番へ導入しました。既存設定・履歴76件を維持し、確認ページの追記は77で確定、S3本文一致と日英の履歴77件表示を確認しました。[運用記録](../operations/community-rc20-20261124.md)。WordPress.org送信・メール返信は保留です。ZIP・タグは変更していません。

Production follow-up: community now runs the same rc.20 ZIP; saving and bilingual history through 77 were verified. See the operation record above. Submission and review reply remain on hold.
