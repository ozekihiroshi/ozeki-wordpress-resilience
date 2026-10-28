# 公開ライン受入レビュー / Public-line acceptance review

2026-10-28 JST / PR #60. Reviewed revision: `0cedd8874907b592da1d922e283a5482e6c54115`, followed by the small review fixes recorded in this commit.

- 前回のP1（シリアライズ形式に見えるテキストの型保持）とP2（ハイフン入りの名前）は修正済み。追加回帰試験をローカルPHP 8.3で再実行して成功。
- 実WordPress/ACFの7ケースは [review-regression.json](review-regression.json) を確認。これはPR提出者によるDB保存・読取り経路の記録で、今回のレビューで実S3・全サイト復旧を再実行したものではない。
- native-queue、application-rules、separated-assets、site-point-time、admin-language-unit、setup-readiness（php -n）も成功。
- 公式Plugin Check **2.1.0: 0 errors / 117 warnings**。一時WordPress/MariaDBコンテナで、提出済み候補の依存ライブラリを再利用し、PRの製品ソース・文書を重ねて検査。提出済みZIPの変更や新しい配布ZIPの生成は行っていない。
- 初回6エラーに対し、RecoveryRulesに直接アクセス防止を追加。内部例外の表示時エスケープは既存経路で行われるため、AcfHistoryの5箇所に用途を説明した行単位の検査注記を追加。警告の一括抑制は行っていない。
- 既存109警告との差分8件は、ACFのDB照会/キャッシュ4件、メタデータキー/値に関する4件。固定した原本の取得・定義の永続化確認、および復旧メタデータ作成に使用。全件は [plugin-check.json](plugin-check.json)。
- 既存サイト、AWS、未コミットの研究作業、提出済みZIP・タグは変更していない。WordPress.orgの申請は審査待ちのまま。ACF対応の取り込みは、新版の公開・再申請完了を意味しない。

Both earlier findings are fixed: literal serialization-shaped text retains its string type, and hyphenated field names recover with their key references. Focused local contracts passed. The submitter's seven real WordPress/ACF DB cases were reviewed; no new live-S3 or whole-site recovery claim is made. Official Plugin Check 2.1.0 returned **0 errors / 117 warnings** in disposable isolated containers after the direct-access guard and five narrowly justified exception annotations. The eight additional warnings concern DB access/cache and metadata keys/values; all findings are retained in the linked JSON. Submitted archives and tags remain unchanged. Main-line integration does not publish a new version or update the pending WordPress.org submission.
