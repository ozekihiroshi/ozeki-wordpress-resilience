# Ozeki Resilience 0.3.3 rc.19 — 申請前の本番確認用候補

2026-11-24。**GitHubでの候補配布です。WordPress.orgへは未提出で、公開承認済みではありません。community本番への導入もまだ行っていません。** 提出済みrc.18と既存ZIP・タグは保全しています。

## 変更内容

- 原文の保全と安全な表示を分け、復旧時に実行につながるHTMLを除外します。認識しないショートコード・動的ブロックは文字として扱い、通常の編集・保存後もこの境界を維持します。
- CF7の入力定義、Flamingo受信項目、表のセル、会員項目、ACFの値をHTML本文と区別し、通常の値を一括変換しません。URL置換は明示したURL項目に限定します。
- 復旧作業領域は非公開の専用ディレクトリとし、正常終了・通常の失敗時に所有する一時ファイルを整理します。不完全な切戻しや中断の記録は確認できる形で残します。
- 閲覧条件が変わらず保留作業もない通常操作では、不要な添付本体照合とS3アクセスを避けます。
- README・readme.txt・導入/復旧ガイドの日英説明を揃えました。ソフトウェアのインストール・初期化は行わず、復旧先の準備済み設定を維持する方針は継続します。

[審査指摘への対応記録](../review/safe-recovery-20261124/RESULTS.txt) / [編集・中断の継続確認](../review/safe-recovery-20261124/EDITOR-AND-INTERRUPTION.txt) / [限定横断調査](../review/boundary-audit-20261124/RESULTS.txt)

## ZIPと対応ソース

- [ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.19/ozeki-resilience-0.3.3.zip)
- [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.19)
- SHA-256: `6651029403cabd57c69e5aba7febe582b5784cfa800687ca7dc8e0182c2a6d9d`
- 8,320,663 bytes、3,820ファイル。ビルド元コミット `014a057`。タグまでの後続変更は公開記録のみで、同梱製品ファイルは同一です。
- 依存ライブラリはrc.18と同一。開発資料・試験コードは同梱せず、8ガイド・相対リンク86件を確認しました。

## 完成ZIPの確認結果

| 確認 | 結果 |
|---|---|
| Plugin Check 2.2.0 | エラー0・警告123。rc.18の116件から、DB直接操作3・キャッシュ3・メタ値検索1が増加。警告を隠さず全件記録 |
| 新規導入・rc.18からの更新 | 成功。設定・記事・会員等のDB状態、有効化状態を照合 |
| 日英管理画面 | PHP描画で表示を確認、警告なし |
| 製品ファイル | ZIPと全ファイル一致。試験後も不変 |
| 実S3 | 保存→復旧後の利用→編集・再保存→再復旧に成功 |
| 対応データ | 記事、未編集Markdown原文、CF7、Flamingo、TablePress、WP-Members、ACFの既存合成例で確認 |
| 原本・履歴 | 各復旧前後のS3版一覧を照合し、不変を確認 |
| 境界の回帰確認 | CF7の正常値、会員定義、同期パターン編集後の実行防止、記事の編集後の保護が合格 |

実行環境はdmの専用Docker、WordPress 7.1.5 / PHP 8.3。非公開・ネットワーク分離したWordPressから、既存EC2ロールを持つホストの制限付き中継で実S3へ接続しました。認証情報はWordPressへ渡していません。新しいランダムな試験専用プレフィックスだけに書込み、本番保存先・既存原本と履歴には触れていません。メール送信・定期保存・自動削除は行いません。

未適用68件は合成例に対する適用規則・準備済み設定維持・安全化等の報告です。全設定を復元したという意味ではありません。今回の完成ZIP確認はWP-CLI、PHP/APIと表示結果の照合であり、全操作を人がブラウザで確認したものではありません。実サイトの通常利用確認は次のcommunity導入段階です。

[ZIP監査](../../evidence-public/wordpress-org-033-rc19/package-audit.json) / [ソース一致](../../evidence-public/wordpress-org-033-rc19/rc19-source-match.json) / [導入・更新](../../evidence-public/wordpress-org-033-rc19/rc19-install-update.json) / [Plugin Check](../../evidence-public/wordpress-org-033-rc19/rc19-plugin-check-final.json) / [実S3](../../evidence-public/wordpress-org-033-rc19/real-s3-result.json) / [境界確認](../../evidence-public/wordpress-org-033-rc19/rc19-boundary-checks.json)

## 互換性と次の段階

今回の変更で保存形式は変わりません。既存原本・履歴の移行や上書きは不要です。ただし旧版には新しい安全な適用規則がないため、復旧先にもrc.19を用意してください。以前に復旧済みで識別情報のないブロック文書への遡及適用は行いません。rc.17以降の添付形式等の既存互換性条件は継続します。

次は結果の確認後、この同じZIPをcommunity本番へ導入して通常利用を確認します。その後、必要に応じて本番で保存された内容を隔離環境へ復旧し、申請更新を判断します。今回は本番導入、WordPress.orgへの送信、メール返信を行っていません。
