# Selected-point site recovery — final 0.3.1 ZIP acceptance

2026-10-25. Candidate: [ozeki-wordpress-resilience-0.3.1-point-time-final.zip](../../release-candidates/20261025-point-time/ozeki-wordpress-resilience-0.3.1-point-time-final.zip).

SHA-256: `53ef447f1534f5adeb754cd7cdfb6a736b8e050f70e4f08b529915519702aedd`.
7,398,174 bytes; 3,814 files. Vendor unchanged from site-retention-final. All packaged product files match source. Earlier ZIPs are preserved; no formal release or shared-site deployment.

## Scope and browser evidence

Select a complete-site Checkpoint and inclusive formal-history end. The engine applies that range only and rejects a missing end, gaps or missing required resources before replacement. Results retain Checkpoint boundary, requested end, actual end and detailed JSON. Checkpoint-only recovery is supported. See [implementation acceptance](site-point-time-m1-031.md).

Prior standard Chrome acceptance used the existing dm dedicated namespace: Checkpoint33/end67 then end68 through Tools → Resilience → Restore complete site. Both displayed Success, requested=actual67/68, history34–67(34)/34–68(35), posts23 and files written0 (existing identical files reused). Detailed JSON matched. Read-only checks after each browser action matched the corresponding S3 article body and publish status. No CLI restore substituted for those browser actions. Local evidence: point-time-browser-20261025/RESULT.md, result-67.png, result-68.png and verify-67/68.json.

Selectors reset after completion; the result identifies the point actually applied. One formal record need not represent an entire edit. Unrecorded theme/menu/configuration changes require a new trusted baseline. This does not add adapter coverage, automatic public exposure or replication.

## Exact ZIP fresh installation and update

Reused dm Docker/core/DB and EC2-role SDK authentication. Separate content/table namespaces `owrptzip_20261025_fresh_` and `owrptzip_20261025_upgrade_` were checked unused before setup. Fresh installation used this ZIP; same-version update seeded fixtures under the preceding site-retention-final ZIP then extracted this ZIP over it. This is extraction/activation acceptance, not a repeated browser Upload/Replace test.

Both passed:

- All 3,814 installed files equal ZIP entries; new end selector and requested-boundary display render.
- Settings, stable identity, test content, comments, CF7/Flamingo records, WP-Members credentials/settings and TablePress IDs/cells/settings remain equal.
- Four synthetic shared pending records and their failure reason remain equal. No resume or S3 submission of these fixtures.
- Individual/site recovery result and failure-attempt state remain equal, including Checkpoint33/requested68/applied68 fixture fields.
- Real S3 history70 unchanged, serialized hash `cc3bac5abe027b212876ee8b24c44955d25e94dd91c726402987671e32b4ba56` in this harness. The browser harness uses a different serialization; compare hashes within each harness.
- Pending retention guard remains effective without S3 writes. No new Checkpoint schedule; verification mail calls zero; shared live-site probe unchanged.
- Tests against ZIP-extracted code pass: selected boundaries/update/deletion/Checkpoint-only/missing-end/gap/resource/later-record exclusion, recovery-result rendering and PHP syntax. Negative S3 cases use memory fixtures, not AWS fault injection.

No repeated cloud restore was needed: browser and real-S3 behavior were already accepted with the same product source; ZIP checks verified source equality, installability and preservation.

## Classification and limits

Product correction from earlier implementation: reused end-number variable collided with a file-path loop; `targetThrough` now preserves the requested number. Earlier harness corrections (admin template loading and shell argument transport) are test infrastructure issues, not product scope extensions. Existing duplicate DISABLE_WP_CRON warning in the live probe is environment configuration; it did not alter results. No new failures in this packaging acceptance.

The source role's missing ListBucketVersions still limits retention preview to current fixed versions; hidden older versions remain unassessed. No IAM change or actual deletion test. No new dependency, infrastructure or authentication helper. Existing S3 assets, members and content remain unchanged; no email delivery, scheduled execution or formal publication.

## 日本語

指定時点復旧入り0.3.1 ZIPの新規導入・旧site-retention-finalからの同一版更新に合格しました。設定、正式履歴70件、合成未確定キュー4件、失敗理由、復旧結果と境界番号を保持し、全ファイル一致を確認しました。今回のZIP確認は展開・有効化方式で、未確定キューの再開やブラウザZIP更新の再試験ではありません。

前回の標準ブラウザではCheckpoint33から終了67・68への復旧、結果表示、対応する本文・公開状態を確認済みです。終了後の選択欄は初期値へ戻りますが、結果は適用番号を保持します。1履歴が編集全体とは限らず、未記録のテーマ等の変更には基準状態の更新が必要です。追加の復旧試験は繰り返していません。

環境のCron二重定義警告・一覧権限不足と、以前修正した製品の変数競合、試験基盤の読込・引数処理は別の問題です。既存資産の変更、S3削除、メール送信、定期実行、正式公開は行っていません。

Local evidence: release-readiness/point-time-final-20261025/ (build-result.json, zip-contract-results.json, installation output, byte checks and live-site probes). Browser and prior boundary evidence are retained separately.
