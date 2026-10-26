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
| 容量 | 7,423,450 bytes |
| SHA-256 | `537504d9b5be632a277c084ddfacf2a4f8a220498f940b6dde32c9e7bf650dbe` |
| Requires at least / PHP | WordPress 6.4 / PHP 8.1（既存の宣言値。全組合せ試験は主張しない） |
| Tested up to | 7.1（今回の環境7.1.3） |
| Contributors | ozekihiroshi |
| ライセンス | GPLv2 or later |

短い説明：Preserve supported site content and confirmed history in Amazon S3, then reconstruct it on a prepared WordPress.

上記の一部はreadme/headerから読み取る情報です。ログイン済みの申請フォームへZIPと補足説明を準備し、確認チェック・最終Uploadは行わずユーザーの最終確認を待ちます。未送信です。

## 審査担当者へ添える説明（英語）

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

0.3.1候補リリースを公開し、匿名ダウンロードしたZIPのSHA-256とタグ上のreadmeがローカル候補に一致することを確認しました。[公開確認記録](../../evidence-public/wordpress-org-031-publication.json)。旧0.2.0リリースはSupersededと明示し、元のアーカイブは保持しています。

mainを利用者向けの公開版の入口とし、README・導入案内を0.3.1申請候補に統一しています。研究・試作時点の資産は `archive/research-before-wordpress-org`（b2968c7）に保全しています。

PR #59のマージ後に一度main側で取り消しましたが、公開版を訪れる利用者の混乱を避けるため、取り消しを打ち消して公開向けの内容を復元しました。履歴の強制書換えは行っていません。

申請用ZIPに対応する固定ソースは上記の0.3.1候補タグです。mainと `release/wordpress-org` の製品ファイルはそのZIPに一致しています。旧rc.1のZIP・タグは保全し、説明改訂版を別タグrc.2として公開します。WordPress.orgへの申請送信は行っていません。
