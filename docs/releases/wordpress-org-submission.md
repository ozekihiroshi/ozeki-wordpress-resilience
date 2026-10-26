# WordPress.org申請準備 — Ozeki Resilience 0.3.1

**未送信・未承認。申請対象は現在mainの0.3.1系です。旧0.2.0候補は撤回された申請候補として履歴保全し、今回の対象・依存キット・検証証拠には使いません。**

## 入力・アップロード内容

| 項目 | 内容 |
|---|---|
| WordPress.orgユーザー名 | ozekihiroshi |
| 製品名 | Ozeki Resilience |
| 希望slug | ozeki-resilience（割当未確定） |
| バージョン | 0.3.1 |
| アップロードZIP | ozeki-resilience-0.3.1.zip |
| 容量 | 7,423,154 bytes |
| SHA-256 | `3882dfbf364961e816efd6069e1b8e118d9d54b6587d2cc3733fba176980d2bf` |
| Requires at least / PHP | WordPress 6.4 / PHP 8.1（既存の宣言値。全組合せ試験は主張しない） |
| Tested up to | 7.1（今回の環境7.1.3） |
| Contributors | ozekihiroshi |
| ライセンス | GPLv2 or later |

短い説明：Preserve supported site content and confirmed history in Amazon S3, then reconstruct it on a prepared WordPress.

上記の一部はreadme/headerから読み取る情報で、フォームの独立入力欄とは限りません。[公式申請ページ](https://wordpress.org/plugins/developers/add/)はログイン前の表示を確認済み。実アカウントでの入力欄・登録メール・同意チェック・ZIPアップロード・送信は未実施です。

## 審査担当者へ添える説明（英語）

Ozeki Resilience 0.3.1 preserves supported site originals and confirmed history in a user-controlled Amazon S3 bucket and reconstructs them on a prepared WordPress. This submission is based on main b2968c7, not the obsolete 0.2.0 worker-based candidate. The current product source is packages/markdown-m1/. All runtime libraries are included; no Python worker, SSH helper or external runtime kit is required. AWS credentials use the standard SDK provider chain. External service terms, privacy and transmitted data are disclosed in readme.txt.

Native-only Baseline/recovery does not require Markdown Documents. It is required when Markdown content exists. Optional adapters and tested versions are documented. Recovery restores publication states, including publish, and can restore selected theme/plugin files from the administrator's captured backup. This is an explicitly requested backup/recovery operation, not a developer-hosted code distribution channel. It does not certify restored content/code as malware-free.

The public name/directory are Ozeki Resilience / ozeki-resilience. The main PHP filename and existing option/queue keys are retained. The restore activation path now derives from the installed plugin location. Old prerelease installations must be deactivated before switching directories.

Plugin Check 2.1.0 on WordPress 7.1.3/PHP 8.3 reported 0 errors and 103 warnings. Warning dispositions and scoped annotations are documented in wordpress-org-checks.md. PHP syntax, five existing focused checks, generated-data native recovery, directory switching, active reinstall and installed-file hashes passed. Existing AWS acceptance remains linked separately; this packaging work did not repeat live AWS tests.

## 公開資料

- [0.3.1候補リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.1)
- [インストール用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.1-rc.1/ozeki-resilience-0.3.1.zip)
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.1-rc.1/packages/markdown-m1)
- [ソースアーカイブ](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/archive/refs/tags/wporg-0.3.1-rc.1.zip)（インストール用ではない）
- [日本語README](../../RAADME-jp.md)・[導入ガイド](../../packages/markdown-m1/docs/user-guide-ja.md)・[限定確認結果](wordpress-org-checks.md)

今回のソース、同梱依存ライブラリ、構築スクリプトで候補を取得・検査できます。旧0.2.0外部キットの取得・導入は不要です。公開後の改善課題を申請条件には追加していません。

## 公開確認とmain反映

0.3.1候補リリースを公開し、匿名ダウンロードしたZIPのSHA-256とタグ上のreadmeがローカル候補に一致することを確認しました。[公開確認記録](../../evidence-public/wordpress-org-031-publication.json)。旧0.2.0リリースはSupersededと明示し、元のアーカイブは保持しています。

mainを利用者向けの公開版の入口とし、README・導入案内を0.3.1申請候補に統一しています。研究・試作時点の資産は `archive/research-before-wordpress-org`（b2968c7）に保全しています。

PR #59のマージ後に一度main側で取り消しましたが、公開版を訪れる利用者の混乱を避けるため、取り消しを打ち消して公開向けの内容を復元しました。履歴の強制書換えは行っていません。

申請用ZIPに対応する固定ソースは上記の0.3.1候補タグです。mainと `release/wordpress-org` の製品ファイルはそのZIPに一致しています。公開済みZIP・タグは変更しておらず、WordPress.orgへの申請送信も行っていません。
