# History display metadata correction — 2026-11-14

The rc.15 media-access history is valid without article title/status attributes. The history table read both fields unconditionally, causing warnings and potentially interrupting the displayed list. The save-status summary and recovery-end selector now share the same read-only display helper. Missing or null fields have localized fallbacks; existing strings (including empty strings) are preserved and escaped at output. File-access records have an English/Japanese name. No original or history record is rewritten, and no format migration is needed.

Review of the producers found that comment, form, membership, table, article-detail and ACF records normally supply both fields. The display nevertheless accepts missing metadata for these and unknown future kinds, without inferring a publication status. The two supplementary Markdown recovery paths also reject media-access records using the existing complete-site-recovery guard; these records are not Markdown documents.

## Verification

- Disposable WordPress 7.0 / PHP 8.3 container on community, separate DB and internal-only network; no public ports, production mounts or AWS credentials. CPU/memory limited. Containers and network removed after testing. dm did not have Docker available, so it was used only for the standalone PHP check.
- Submitted rc.15 ZIP first reproduced the undefined-title warning. The source overlay then rendered the complete admin page in English and Japanese with zero PHP warnings.
- 36 synthetic historical records: 9 kinds × present / missing / null / empty display attributes. Existing strings and escaping retained; all records rendered. `Store::history()` returned identical records before/after, and the backing fixture files retained identical hashes. These were isolated fixture objects, not copied production history or a live-S3 run.
- A media-access record was rejected before the individual Markdown recovery path fetched its original.
- `tests/save-status.php` adds missing-field coverage to the existing GitHub Actions PHP 8.1/8.3 check. `tests/history-display.php` is the WordPress integration regression. [Isolated results](../../evidence-public/history-display-20261114/result.json).

Production remains at submitted rc.15. No production settings, existing S3 originals/history, submitted ZIP or tag were changed. This source fix is not yet in a new release ZIP.

## 日本語

記事用のtitle／statusを持たない閲覧条件の記録を、履歴一覧が記事と同じ前提で表示したことが原因です。表示だけに共通の補完処理を設け、欠けた状態を公開・非公開と推測せず「未記録」とします。既存の文字列と空欄はそのまま表示し、閲覧条件には日英の名称を付けます。原本・履歴の補完や書換えは行いません。

他の対応記録と未知の種類も含む36件で、日英の管理画面表示・履歴読取り・保存済み値の保持を確認しました。閲覧条件をMarkdown文書として個別復旧する経路の判定漏れも防止しました。本番・提出済みrc.15には反映していません。
