# WordPress.org 初期レビューへの対応 / Initial review response

初期指摘の対象は2026-10-28提出の **0.3.2 rc.1**。対応版 **0.3.3 rc.3の更新受付と元の審査メールへの返信が完了**し、審査担当者の回答待ちです。公開承認済みではありません。0.3.3 rc.1・rc.2は未提出の記録として残しています。
The initial findings concerned **0.3.2 rc.1**. The **0.3.3 rc.3 update was received and our reply was sent in the original review thread**. We are awaiting the reviewer's response; publication has not been approved.

## 指摘との照合 / Disposition

| 指摘 / Finding | 対応 / Disposition |
|---|---|
| Archived theme/plugin code restoration | 維持。管理者自身の信頼した初期保存からの復旧であり、コード入力欄・開発者配信の更新ではない。適否は審査担当者へ確認。ホストがWordPressのファイル変更を禁止していれば復旧を拒否。Retained; ask the reviewer to assess this recovery workflow. Host file-modification restrictions are respected. |
| Recovery reference JSON | 保存・S3読取り前に型、3項目のみ、manifestパス、固定version、SHA-256を検証。不正な値を補正して別の参照にせず拒否。Validate before persistence or S3 access; reject malformed references. |
| Nonce / related inputs | 文字列型を確認し、wp_unslashとsanitize_text_field後にwp_verify_nonceへ渡す。Type-check, unslash and sanitize before verification; apply appropriate sanitization to related operation/settings/version-selection inputs. |
| Markdown source | 文字列、UTF-8、NUL禁止、5 MiB上限を検証。原文は実行・HTML出力せず独立原本として保存。コード例を含む原文を一律削除しない理由を説明。Validate archival text without changing original bytes; explain the separate rendering boundary. |
| Output callback | HTML全体の文字列置換を廃止。WordPress HTML Tag ProcessorでURL属性だけ変更し属性エスケープ。フォーム・埋込みなど他のフィルター出力を一律削除しない。Use core attribute escaping, preserving unrelated shortcode output. |
| Prefixes | 宣言の名前空間をOzekiResilience\M1へ変更。既存owr_設定・履歴・hook識別名は互換性のため維持し、審査担当者に扱いを確認。Persistent identifiers and existing hooks remain a clarification item, not a claimed exemption. |
| AWS SDK | 3.401.5へ更新。依存lockを更新しComposer auditを実施。Updated to 3.401.5 with dependency audit. |
| Admin notices | 長い障害詳細はプラグイン画面へ限定。他画面では管理者への短い対処リンク。販促・評価依頼・リダイレクトなし。Detailed notices confined to the plugin screen; concise actionable status elsewhere. |

## 更新受付と返信 / Update receipt and reply

2026-10-28 JST。利用者の確認・送信指示に基づき既存申請を更新しました。別の申請は作成していません。

- WordPress.org画面で「New version of Ozeki Resilience uploaded for review.」を確認。
- 同日20:44 JSTの自動受付メールでversion 0.3.3、rc.3の説明と下記SHA-256の一致を確認。
- 元の「[WordPress Plugin Directory] Review in Progress: Ozeki Resilience」スレッドでplugins@wordpress.orgへ返信し、Gmailの「メッセージを送信しました」を確認。
- 復旧機能の趣旨、保存済みデータや連携との互換性のため既存の保存名・hookを維持する理由、Markdown原本とHTML出力の扱いを説明。

Following the owner's approval, the existing application was updated on October 28, 2026. The upload success page and the 20:44 JST automated receipt confirm version 0.3.3 with the rc.3 description and SHA-256 below. Gmail confirmed sending the reply to plugins@wordpress.org in the original review thread. No duplicate application was created.

復旧機能の審査上の扱いと既存識別名の維持については、審査担当者の判断待ちです。受領・送信の確認は、全指摘の解消や公開承認を意味しません。
Recovery-policy and legacy-identifier questions remain for the reviewer. Receipt and sending confirmations do not establish that all findings are cleared or that publication is approved.

[送信済み返信本文 / Sent reply](wordpress-org-review-reply-20261028.txt).

提出済みZIP・タグは変更していません。対応する製品ソースはタグ [wporg-0.3.3-rc.3](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/tree/wporg-0.3.3-rc.3)、commit 2ff4306a0c8715467100866b1aa9185d708e3402です。
The submitted ZIP and tags remain unchanged. The matching product source remains at that tag and commit; this documentation-only update records submission status.

## 確認結果 / Candidate validation

2026-10-28 JST。**0.3.3 rc.3、更新受付・返信完了 / update received and reply sent**。

- ZIP: `ozeki-resilience-0.3.3.zip` / 8,590,043 bytes / 3,922 files.
- SHA-256: `066c4ae4f47f943a8b7cb4fa31efd6e256ad47772bdb1f4bd99c22a39804973e`.
- [Exact ZIP validation](../../evidence-public/wordpress-org-033-rc3/validation.json): WordPress 7.1.3 / PHP 8.3.35 / MariaDB / simulated S3.
- 新規導入、初期保存、保護開始、0.3.2 rc.1からの更新と状態保持・保存継続が成功。Fresh install and active update from the submitted 0.3.2 ZIP passed.
- 隔離復旧先へ保存記事とテーマファイルを復旧し、テーマのハッシュ一致を確認。Native content/theme recovery passed on a disposable destination. This is not a new full ACF recovery or live-AWS trial.
- ACF無料版6.8.10の初期保存判定と日英表示を確認。Real ACF free readiness and bilingual rendering passed.
- 不正入力拒否、原文保持、HTML属性出力、フォーム保持、srcset、ホストのファイル変更禁止を確認。Input/output regressions passed in real WordPress; interactions used CLI, not browser automation.
- [Plugin Check 2.1.0](../../evidence-public/wordpress-org-033-rc3/plugin-check.json): **0 errors / 104 warnings**. This does not imply manual review approval.
- [34 local contract checks](../../evidence-public/wordpress-org-033-rc3/contract-checks.json): all passed.
- [Source/vendor ZIP comparison and audit](../../evidence-public/wordpress-org-033-rc3/static-validation.json): all files match; no known Composer advisories or abandoned dependencies reported.

残る入力警告は、Markdown原文・GFSの厳格な正規化・復旧参照JSONの専用検証・履歴番号の数値検証に関するものです。legacy hookの接頭辞警告は上記の確認事項として残しています。既存の直接DB読取り・復旧ファイル操作等の警告も全件を添付しています。警告を一括して「問題なし」と扱ってはいません。
Remaining input warnings involve dedicated validators for archival Markdown, GFS settings, fixed snapshot references and formal-history bounds. The legacy hook prefix remains a reviewer question. Existing database/filesystem findings are included in the full report, not silently dismissed.

試験用S3のStartAfter未実装が復旧試験を妨げたため、試験側だけを修正して再実行しました。旧候補の検証範囲を拡大して主張するものではありません。
The simulated S3 transport was corrected to honor StartAfter before the final recovery run; earlier evidence retains its original scope.

以前のZIP・タグ、研究用ディレクトリの未コミット7ファイル、既存サイトは変更していません。依存ライブラリは今回更新しているため、以前の提出ZIPと同一ではありません。
Earlier ZIPs/tags, the seven uncommitted research files and existing sites were preserved. This candidate intentionally contains updated vendor dependencies.
