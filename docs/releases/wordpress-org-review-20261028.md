# WordPress.org 初期レビューへの対応 / Initial review response

審査対象は2026-10-28提出の **0.3.2 rc.1**。0.3.3 rc.2は未提出です。WordPress.orgの状態は **Being Reviewed / applicant action required**。公開承認ではありません。
The review concerns submitted **0.3.2 rc.1**, not the unsubmitted 0.3.3 rc.2. Publication has not been approved.

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

## 送信前の判断 / Before resubmission

復旧機能の適否と既存識別名の互換性は、技術試験の成功だけでは解消しない審査上の確認事項です。「全指摘解消済み」とは扱いません。ZIPの送信と元の審査メールへの返信は、利用者による確認後に行います。再申請は作成しません。
Recovery-policy and legacy-identifier questions remain for the reviewer. Tests do not establish policy approval. Upload and reply to the original email thread only after the owner's review; do not create a duplicate application.

[English reply draft](wordpress-org-review-reply-20261028.txt). The draft is unsent.

## 確認結果 / Candidate validation

2026-10-28 JST。**0.3.3 rc.3、未送信 / not submitted**。

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
