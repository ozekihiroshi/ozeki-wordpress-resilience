# Native article details — standard browser acceptance

PR #28 product code reused unchanged. Existing community/dm isolated TablePress integration namespaces and S3 prefix were reused. Chrome standard WordPress editor and Posts/Trash screens were used; no content-update API/script substituted for these browser actions.

## Successful sequence
- Existing trial article21: remove featured image; replace category assignment with child category4 and tag with `試験：ブラウザ分類確認`. Standard Save succeeded. Existing Checkpoint33 plus confirmed history45 restored matching state on dm.
- Set existing trial image20 (version1) from standard Media Library; Save. Recovery through49 matched image ID/bytes and classification.
- Replace with existing image28 (version2); Save.
- Existing trial article10 (`テスト書き込み：追加表を含む活動報告`) moved to Trash and permanently deleted using standard Posts screen. No other article was deleted.
- Recovery from the same Checkpoint33 plus confirmed history56 matched article21 featured image28 bytes, category4/tag8 and published state; article10 absent. No pending history remained. Article21 body hash unchanged.
- Read-only display on the existing wp-backup trial path visibly showed recovered version2 image, category/tag and article10 absence. Source DB/queue were not recovery inputs; source inspection was assertions only. Recovery was invoked by existing product PHP class, not a new UI reconstruction action.

## Boundaries and issues
- Small trial theme originally omitted post-thumbnails support. A test-only MU declaration, conditional on the trial theme, exposes the standard control. Product and live themes unchanged. A CRLF at the end of a deployment shell command initially left the fixture filename with a trailing carriage return; the correct fixture filename was then deployed. This was harness-only.
- The source body still contains its earlier fictitious table-source.invalid image URL; source browser body image was broken, while Media Library and recovered featured-image bytes/display worked. Body was deliberately not rewritten in this attributes-only acceptance.
- Destination trial administrator login initially failed with WP-Members `User has not been activated`. This failure is preserved as an initial result. Follow-up identified missing trial-administrator activation under restored moderation settings; targeted activation subsequently allowed fresh standard-admin login on both sites. See [investigation and acceptance](administrator-activation-acceptance.md). Product recovery code and the verified ZIP were unchanged.
- WP-Members emitted null/non-subscriber administrator records during source browser activity; record count includes these and unchanged-body save records. Do not equate56 records with56 unique content edits.
- Existing live dm probe hashes unchanged. Source modifications limited to trial articles21/10 and trial taxonomy assignment. Mail was blocked by the existing MU guard; CLI comparison/recovery mail attempts0. Cron disabled. No IAM/new infrastructure/live plugin deployment, scheduled execution or formal release. Frozen ZIP unchanged.

## 日本語
標準画面で試験記事21のアイキャッチ解除→設定→差替え、カテゴリー・タグ変更を保存し、試験記事10を完全削除しました。各段階を既存S3のCheckpoint33＋後続履歴からdmの隔離試験WordPressへ復旧し、状態一致を確認しました。最終履歴56、保留なし。復旧画像・分類・記事不在を読取り専用画面でも確認しました。

初回は復旧先試験管理者の未有効化でログインに失敗しました。その後、会員承認制に対する試験管理者の有効化漏れを確認し、対象管理者だけを有効化して両サイトで標準画面の再ログインに成功しました。経緯は[管理者有効化の確認結果](administrator-activation-acceptance.md)を参照してください。試験テーマのアイキャッチ宣言不足と配置スクリプトの改行問題は試験基盤の問題です。製品コード・検証済みZIPは変更していません。
