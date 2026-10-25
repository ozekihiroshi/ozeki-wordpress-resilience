# Separated originals: implementation and focused acceptance

Date: 2026-10-25. Work: storage-format implementation, focused existing-function verification, and one necessary option-persistence correction. Status: verified with limits, not packaged or released. Completion condition: normal save, initial snapshot and Checkpoint use shared separation; standalone content is readable; supported state and unknown captured information survive reconstruction without old resources. Contribution: preserve irreplaceable recovery originals independently.

## Evidence

- `packages/markdown-m1/tests/separated-assets.php`: plain Markdown/Mermaid/math/code, HTML, table cell JSON, inquiry named-field JSON, comments; metadata separated; unknown information preserved; old originals read without writes; partial writes do not confirm; damaged parts rejected; independent site Checkpoint after removal of all older test objects; structured confirmed tail replay.
- Existing offline contract suite: Checkpoints, selected points, comments/forms/members/tables, native detail/queue, retention preview, save/result reporting and failure reporting. Comment tests now use the new original reader instead of assuming adapter `source.json` is a monolithic operation. Existing legacy originals remain a read path.
- Existing dm WordPress/DB container, separate `owrsep_20261025_source_` and `owrsep_20261025_target_` tables and `/tmp/owr-separated-assets-20261025` content. No new infrastructure or authentication helper. S3 is a fixture, never the AWS bucket.
- Source trial: actual initial capture, page original saved before applying the update and confirming history 1, independent complete Checkpoint. Direct resource reads match page text, Markdown and table values. Removed ancestor objects only from the in-memory fixture.
- Destination: source directory renamed out of use; any source-table query rejected. Restored Checkpoint 1 into isolated WordPress. Result: 7 post records, correct page body and `publish`, exact Markdown bytes, image file, comment, table values/options, inquiry fields and unknown nested metadata. Mail attempts zero. Existing shared-site before/after probe identical.

## Findings and limits

The initial restore stopped at absent `WPLANG=false` and did not return success. This was a product option-persistence edge case exposed by a real full initial capture, not an S3/format fault. The minimal helper correction explicitly adds an absent option only after error-free write/read, then verifies persistence. The separate corrected run succeeded. Existing duplicate `DISABLE_WP_CRON` warning is an environment bootstrap issue; both trial namespaces explicitly disable scheduling. Initial shell quoting/line-ending and missing standalone test configuration were harness issues, not product faults.

Actual WordPress database/file restoration and offline S3 contracts are distinct evidence. No real AWS failure/upload, UI editing, CF7 mail, TablePress interactive rendering, WP-Members login or packaged upgrade is claimed for this change. New schema requires the new reader; frozen 0.3.1 ZIP and existing S3 assets are untouched. Unknown metadata is retained, not newly certified. This does not complete a software certification allowlist or change the existing initial software bundle policy.

Local evidence: `release-readiness/separated-assets-20261025/` (trial.php, run.sh, wp-result.txt, wp-corrected.txt). Initial failed output retained. No live deployment, existing-content/member changes, S3 deletion, scheduled execution, ZIP rebuild or formal release.

## 日本語

通常保存・初期取得・Checkpointの共通分離形式を実装し、原本の単独読取りと、元環境を使わない実WordPressへの復旧を試験用データで確認しました。未知の付随情報も保持します。S3はメモリ代替であり、実AWSの検証とは区別します。今回の修正は固定済みZIPへ収録していません。

初回は未設定の言語設定を保存できない既存不具合で停止しました。原因を修正した別の試行で復旧成功を確認し、自動続行・自動再開は追加していません。認定一覧の強制や、認定外情報の自動適用方針の変更は今回の対象外です。

## Real S3 follow-up — 2026-10-25

Work: existing-feature verification; completed with limits. The earlier evidence above used a fixture. A separate, minimal real-AWS trial now passed using the same implementation and existing community/dm Docker hosts, isolated WordPress tables/content and a new unused prefix inside the authorized M1 lab scope. Authentication is the AWS SDK default EC2-role chain; no helper, new infrastructure or IAM change.

An ordinary WordPress page update through product hooks produced one confirmed history. Direct S3 retrieval matched normal-save HTML, initial-snapshot HTML/Markdown, and Checkpoint HTML/Markdown/table JSON. Restoring the Checkpoint through history 1 on dm reproduced seven post records, body, exact Markdown including Mermaid/math/code, publish state, image, comment, table values/settings, inquiry fields and unknown nested metadata. All 24 GetObject requests used fixed Version IDs inside the Checkpoint directory. Recovery used no source DB/files or ancestor objects; the reference/expected-value handoff was used for selection and assertions, not data import.

Existing 667 current S3 objects outside the dedicated scope had identical before/after inventory digest; the existing dm site probe was unchanged. No S3 deletions, mail, scheduling or release. The existing duplicate cron-constant warning remains an environment issue. No product change was needed in this follow-up. Browser interactions, every adapter's normal-save permutations, plugin rendering and packaged installation were not repeated. Working-tree reader still required; frozen ZIP unchanged.

実S3の専用範囲で通常更新・初期スナップショット・Checkpointの原本単独取得と、別ホストdmへの復旧が成功しました。取得24件はすべてCheckpoint内部の固定版で、過去資産を削除せず独立性を確認しました。通常保存は標準WordPress APIと製品フックの確認であり、ブラウザ検証の追加ではありません。未知情報も保持されました。製品の追加修正、既存S3資産変更、ZIP更新、正式公開はありません。

Local evidence: `release-readiness/separated-assets-s3-20261025/RESULT.md`, source-result.json, result.json, reads.json and before/after inventory records. Trial scripts use isolated namespaces and are single-use.
