# 0.3.3 rc.12 — 更新受付・返信完了、審査担当者の回答待ち

今回の候補はTablePressとMarkdownの復旧継続性の修正を含みます。**申請者からrc.12のWordPress.org更新受付と元の審査メールへの返信完了の報告を受けました。審査担当者の回答待ちであり、公開承認済みではありません。**

## 変更と互換性

- TablePressの復旧先に必須のカスタム命令欄を、安全な空文字で用意します。保存された実行用設定は持ち込みません。
- サイト全体復旧で確認したサイト・画像の参照元を次の保存へ引き継ぎ、未編集Markdownも次の復旧後に利用できるようにします。原文は書き換えません。
- 対応する保存値、安全な復旧先の状態、次の世代に必要な関係情報を分けて扱い、独立した期待値で欠落を検出します。[修正と構築方針・前段の確認結果](../review/recovery-runtime-results-20261111.md)。
- 既存原本は読めます。新しい参照情報を含む原本・Baseline・Checkpointにはrc.12以降の対応版が必要です。旧readerは新形式を拒否し、誤った参照を黙って復元しません。復旧先にも更新版を用意してください。
- 既存S3原本・履歴の移行や書換えは行いません。更新だけを理由としたBaseline再作成も不要です。過去に失われた参照元情報は本文から推測しません。旧Markdown個別復旧の保証範囲は拡張しません。
- WordPress本体・テーマ・プラグインは引き続き管理者が信頼できる配布元から別途導入します。

## 候補と確認結果

- [導入用ZIP](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/download/wporg-0.3.3-rc.12/ozeki-resilience-0.3.3.zip) / [対応ソース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.12)。ヘッダー・Stable tagは0.3.3、候補識別子はrc.12。
- SHA-256: `8084a992fb593a65ca239fc8dc5b30b01061237424d768f106a2d1c63788ac6b`。

- 8,288,605 bytes / 3,814 files。[パッケージ監査](../../evidence-public/wordpress-org-033-rc12/package-audit.json)：製品ファイルとソースが一致。vendor変更なし。同梱8ガイド・相対リンク80件が解決。開発資料・試験コードの混入なし。
- WordPress 7.1.3 / PHP 8.3.36の新設隔離サイトへ最終ZIPを導入・有効化。全配置ファイル一致、別プロセスで管理画面の描画成功。
- 更新元が提出済みrc.11と全3,813ファイル一致することを確認して、通常のプラグイン置換で更新。全3,814配置ファイルが候補ZIPと一致。有効化状態、設定、投稿21件、記録対象の状態ハッシュを保持。未確定操作・復旧結果は元々空／未記録であり、それらが存在する更新の実証とは区別する。
- 前段で実S3の二世代復旧を済ませた2サイトへも最終ZIPを配置し、表の表示・検索・並べ替え・ページ送り、編集／未編集Markdownのリンク・画像ハッシュを実ブラウザで再確認。10チェック成功、旧サイトへの要求・スクリプトエラーなし。今回は新しい実S3復旧サイクルを再実行したのではなく、既存の復旧済み資産の利用確認。
- 最終ZIPのコードで共通適用規則、参照URL境界、旧形式読取り、新しい原本・Checkpointの参照情報、未変更rc.11 readerによる新形式拒否の契約確認が成功。これらの形式試験はメモリS3。
- Plugin Check 2.1.0：**エラー0／警告100**。[結果](../../evidence-public/wordpress-org-033-rc12/plugin-check.json)。rc.11の99件に対し、追加1件は配列内meta_valueのJSON処理を低速DB問い合わせとみなす静的警告。該当行はDB問い合わせを行わない。警告ゼロ・審査承認とは扱わない。
- [確認サマリー](../../evidence-public/wordpress-org-033-rc12/validation.json)。導入・更新はCLI、管理画面は別プロセス描画、利用確認はChromium。管理画面でのアップロード操作や全連携の再検証ではない。

## 保全と送信状態

提出済みrc.11のZIP・タグは変更しません。rc.11 ZIP SHA-256: `0fcbbac0a7e8dcadbbb5d5b247248a3c8081ceb1b4ee6c2771f7e19cc5233c1c`。研究側の未コミット変更は含めません。

**rc.12の更新受付・審査メール返信は完了しています。** 受付・送信完了の根拠は申請者からの報告であり、エージェントによる画面の独立確認ではありません。公開承認ではなく、審査担当者の回答待ちです。

## Supplementary explanation / 補足説明の要旨

This candidate retains the previous review-response fixes. Follow-up recovery checks corrected two usability issues: TablePress receives its required safe empty runtime setting without executing archived custom commands, and complete-site recovery carries verified site/image origins into subsequent saves so untouched Markdown links and images remain usable after another recovery.

Existing originals and formal history remain unchanged and readable. New recovery points containing reference context require this updated reader; older readers reject them rather than silently restoring stale links. Administrators install trusted WordPress, themes and plugins separately. Recovery does not deploy archived executable software.

The exact candidate ZIP is verified separately from the earlier development checks. See the results above and the release assets. The author confirmed rc.12 upload acceptance and sending the reply to the original review email. We are awaiting the reviewer response; publication is not approved.

## 更新受付・返信完了の記録

申請者が手動でrc.12をアップロードし、元の審査スレッドへ返信しました。本チャットで申請者から両方の完了報告を受けたことを根拠に記録を更新しています。操作ツールで申請画面を取得できなかったため、受付画面や送信済みメールを独立に確認したとは扱いません。

今回変更したのはmain上の説明とGitHubリリース説明のみです。提出済みrc.12および以前のZIP・タグ・対応ソースは変更しません。タグ内文書・ZIP内READMEの未提出表記は作成時点の記録として残り、現在の状態はmainの本記録を参照してください。

The author manually uploaded rc.12 and replied in the original review thread, then confirmed both actions in this chat. This record relies on that confirmation, not an independent inspection of the receipt or sent email. The submitted ZIP, tag and matching source remain unchanged. Submission-time status is maintained on main and in the release description; packaged/tagged documents retain their build-time status.
