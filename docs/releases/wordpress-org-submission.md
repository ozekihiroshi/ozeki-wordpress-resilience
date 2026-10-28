# WordPress.org申請記録 — Ozeki Resilience 0.3.1

**2026年10月26日、0.3.1（rc.2）の申請が受け付けられました。現在は審査待ち（Awaiting Review）で、公開承認・WordPress.orgへの掲載はまだ行われていません。旧0.2.0候補は履歴として保全し、今回の申請対象には含めません。**

## 受付結果

- 受付画面： [WordPress.org申請ページ](https://wordpress.org/plugins/developers/add/)（申請アカウントでのログインが必要）
- 状態：Awaiting Review — This plugin has not yet been reviewed.
- 仮割当slug：`ozeki-resilience`（審査結果により変更される可能性あり）
- 自動スキャン：Pass。表示された警告は `RAADME-jp.md` の `unexpected_markdown_file` 1件。手動審査の合格や公開承認を意味しません。
- 受付確認メール送信済みと画面に表示。メール自体の到着確認は未実施。
- [受付記録](../../evidence-public/wordpress-org-031-rc2-submission.json)


## 入力・アップロード内容

| 項目 | 内容 |
|---|---|
| WordPress.orgユーザー名 | ozekihiroshi |
| 製品名 | Ozeki Resilience |
| 仮割当slug | ozeki-resilience（審査により変更の可能性あり） |
| バージョン | 0.3.1 |
| アップロードZIP | ozeki-resilience-0.3.1.zip |
| 容量 | 7,423,450 bytes |
| SHA-256 | `537504d9b5be632a277c084ddfacf2a4f8a220498f940b6dde32c9e7bf650dbe` |
| Requires at least / PHP | WordPress 6.4 / PHP 8.1（既存の宣言値。全組合せ試験は主張しない） |
| Tested up to | 7.1（今回の環境7.1.3） |
| Contributors | ozekihiroshi |
| ライセンス | GPLv2 or later |

短い説明：Preserve supported site content and confirmed history in Amazon S3, then reconstruct it on a prepared WordPress.

上記の一部はreadme/headerから読み取る情報です。ユーザーが確認項目へチェックし、明示的な送信承認後にUploadを実行しました。受付画面でファイル名・バージョン・補足説明内のrc.2ハッシュとソースURLを確認しています。

## 送信した補足説明（英語）

全文は [wordpress-org-additional-information.txt](wordpress-org-additional-information.txt) に保存しています。

rc.2はreadmeの構成と候補リンクの説明改訂版です。仕組み・対応範囲・対象外・利用者の準備を区別しました。コードと同梱ライブラリはrc.1と一致し、新機能・保証拡大はありません。Plugin Checkはrc.1の既存結果（0 errors / 103 warnings）で、今回再実行したとは記載しません。[ZIP差分確認](../../evidence-public/wordpress-org-031-rc2-validation.json)。

## 公開資料

- [0.3.1候補リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2)
- [インストール用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.2/ozeki-resilience-0.3.1.zip)
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.1-rc.2/packages/markdown-m1)
- [ソースアーカイブ](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/archive/refs/tags/wporg-0.3.1-rc.2.zip)（インストール用ではない）
- [日本語README](../../RAADME-jp.md)・[導入ガイド](../../packages/markdown-m1/docs/user-guide-ja.md)・[限定確認結果](wordpress-org-checks.md)

今回のソース、同梱依存ライブラリ、構築スクリプトで候補を取得・検査できます。旧0.2.0外部キットの取得・導入は不要です。公開後の改善課題を申請条件には追加していません。

## 公開確認とmain反映

rc.1公開時の確認は[過去の公開確認記録](../../evidence-public/wordpress-org-031-publication.json)に保持しています。rc.2も公開ZIPを匿名ダウンロードし、上記SHA-256と一致することを確認しました。旧0.2.0リリースはSupersededと明示し、元のアーカイブは保持しています。

mainを利用者向けの公開版の入口とし、README・導入案内を0.3.1申請候補に統一しています。研究・試作時点の資産は `archive/research-before-wordpress-org`（b2968c7）に保全しています。

PR #59のマージ後に一度main側で取り消しましたが、公開版を訪れる利用者の混乱を避けるため、取り消しを打ち消して公開向けの内容を復元しました。履歴の強制書換えは行っていません。

申請したZIPに対応する固定ソースは `wporg-0.3.1-rc.2`（`6a45471e8e7c903a96b6ea90f4d4e1801df4e5b2`）です。送信後、mainと `release/wordpress-org` のREADME・申請記録に受付状態を反映しました。そのため現在のREADME表記は申請時のZIPと異なりますが、実行コードの変更はありません。申請済みZIP・rc.2タグ・旧候補は変更していません。

## 申請後の導入文書整理（2026年10月28日）

GitHub上の英日導入ガイドを、準備・設定・Baseline・保護開始確認の順に整理しました。更新手順を分離し、申請状態とAWSサンプル検証範囲の古い記載を訂正しています。実行コードと申請済みrc.2 ZIP・タグは変更していません。最新の案内はmainの利用ガイドを参照してください。文書リンク・画面項目との対応・ZIPハッシュを確認し、新しい動作試験は行っていません。

## 0.3.2更新候補の準備（2026年10月28日）

導入支援と日英管理画面を含む0.3.2 rc.1を用意しました。**更新候補は未送信**です。[更新候補・確認結果・送信内容](wordpress-org-032-candidate.md)を参照してください。上記0.3.1 rc.2の受付記録・ZIP・タグ・送信済み補足説明はそのまま保全しています。
