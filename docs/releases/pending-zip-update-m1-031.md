# Nonempty pending queue: browser ZIP update and resume — 0.3.1

Acceptance date: 2026-10-25. This records a completed trial; no product change or ZIP rebuild.

## Result

The existing community isolated WordPress and trial article 37 were reused. Chrome's standard Upload Plugin → Install Now → Replace current with uploaded updated the existing installation to the validated ZIP. Both displayed 0.3.1; this is not cross-version migration acceptance.

| Stage | Confirmed history through | Pending operations |
| --- | ---: | ---: |
| Before trial | 68 | 0 |
| After test-only history PUT refusal | 68 | 2 |
| After measured browser replacement | 68 | 2 |
| After browser Resume history | 70 | 0 |

The article operation `c2f9d408-bad9-4d60-b83f-44a01f9c5087` became history 69; native-detail operation `f6bf2135-b516-426a-9956-146f719caeee` became 70. Both IDs were adopted once. The queued article, shared queue, notice and error matched exactly across the measured update. Resume confirmed the same operations, cleared pending/errors and restored the display. The article body matched its S3 original.

Validated artifact: `release-candidates/20261025-editor-save/ozeki-wordpress-resilience-0.3.1-editor-save-final.zip`.
SHA-256: `901950f74d02d40bb4c21f92cecb6f7a80d30192f211a84191857f4e2bd3e5d2`. All 3,813 installed files matched.

## Test timing correction, not product data loss

The existing test used `wp_update_post` and product hooks to append one trial paragraph. Only that CLI request's AWS SDK handler rejected `/history/` PUT before transmission; originals used real S3. This was an injected failure, not an AWS outage, response loss or browser-edit acceptance. The handler disappeared when the request ended. Browser resume used standard AWS authentication with no credential helper or IAM change.

The first `pending.json` was captured before request shutdown, so it did not yet include the native-detail queue created at shutdown. The first comparison therefore could not establish preservation of that queue. The original evidence was retained. After the request and first update had completed, `after-update.json` captured both operations. The same ZIP was replaced again through the standard browser flow; comparison with `after-second-update.json` established exact preservation of both queues and recorded errors before resume. No replacement trial operations were created.

Operational lesson: capture an update baseline only after the save request and its completion callbacks have finished. Do not interpret a premature sample as product queue loss or conceal it behind the final successful result.

## Environment and preservation

- Trial `DISALLOW_FILE_MODS` was temporarily permitted with a backup, then restored byte-for-byte. Existing 128 MiB upload limits required no change.
- Mixed ownership was normalized only inside the isolated Resilience plugin tree. This was deployment configuration, not a product-code fix.
- Existing posts/postmeta outside trial article 37 and its child records, users/usermeta, comments/commentmeta, taxonomy tables, S3 settings, active plugins, member settings and recovery result/attempt records matched their baseline hashes. The authorized test paragraph remains in article 37.
- WordPress cleaned the temporary ZIP attachment during normal replacement. The whole Cron option was not tested for invariance; event registration is distinct from execution. `DISABLE_WP_CRON=true` and mail blocking remained enabled.
- No product defect was identified. No product source, frozen ZIP, IAM, dm or main-site content was changed. No mail, scheduled execution, repeat site recovery or formal release occurred.

This closes the browser-update gap for **one pending article plus one pending native-detail operation**. It does not cover arbitrary adapter mixtures, forced process termination, concurrent editing, all version migrations or every failure mode. Earlier empty-queue browser acceptance and synthetic file-overwrite tests remain separate evidence.

## 日本語

既存community隔離環境の試験記事37を使い、本文と付随情報の未確定2件を保持したまま、標準管理画面から検証済み0.3.1 ZIPへ更新しました。要求終了後に採取した基準と更新後の操作ID・内容・notice・errorが完全一致し、履歴は68のままでした。画面のResume historyにより同じ操作が69・70へ一度ずつ確定し、未確定0件・エラー解消・表示回復、本文とS3原本の一致を確認しました。

最初の記録はshutdown前で付随情報キューを含まず、その比較では保持を判定できませんでした。これは採取タイミングの問題で、製品のデータ消失ではありません。初回記録を残し、2件揃った基準から同一ZIPを再度標準画面で更新して照合しました。新しい試験操作で置き換えてはいません。

ファイル変更禁止の一時解除と復帰、隔離プラグインの所有権統一は環境設定の対処です。製品修正はありません。試験記事以外の既存データ・会員・設定・復旧結果を保持し、メール送信・定期実行・正式公開は行っていません。確認範囲は本文＋付随情報2件であり、全連携の任意キュー、強制終了、同時編集、全版移行を保証しません。

## Evidence and procedure

Local record: `release-readiness/pending-zip-update-20261025/RESULT.md`; `pending.json`, `after-update.json`, `after-second-update.json`, `final.json`, `files-result.json` and screenshots. Trial mutation scripts are not replay instructions. See the [installation/update procedure](../../packages/markdown-m1/docs/install-update.md). These documentation changes do not repackage the validated ZIP.
