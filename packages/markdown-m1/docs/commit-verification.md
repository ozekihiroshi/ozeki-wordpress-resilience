# Original read-back before formal-history confirmation

Included in save-verification-final candidate after PR #42; absent from the older application-rules-final ZIP. No publication.

`Store::commit()` now uses its existing S3 client to read the operation's original through fixed Version IDs. The existing original reader checks source, metadata, split parts and the reassembled digest. Referenced media are also read and hash-checked; repeated identical media references within the operation are checked once. Only after all reads and checks succeed does it PUT formal history. No history listing or site-wide resource scan was added.

The normal article save carries the Store instance from prepare to confirmation, reusing its SDK client. Shared queue flush already uses the same Store. A later resume necessarily creates a client in that new request, but reuses the frozen operation's references and verifies them again before committing. Existing pending/error handling remains. No new background worker, auto-resume or rollback mechanism.

Sequential GETs are used initially: the prior small-text measurement was about 55 ms median for two resources. This is not a latency guarantee for the new code, images or production workloads. Bounded parallel GETs remain a possible optimization; no new concurrency machinery is introduced here.

## Verification and limitations

The focused test creates complete structured text and image resources in a memory S3 fixture. Source index, metadata, split data and media each receive corrupted GET responses and read errors. Each case asserts **zero history PUTs**, pending payload retention and unchanged original objects; clearing the fault permits the same operation to confirm with fixed-version reads. This test passed locally and in the existing dm Docker PHP environment. S3, queue/options and lock services are test substitutes; this is not new real-AWS, real-WordPress transaction or browser acceptance. Existing native queue, editor, separated-original, comment/form/member/table contracts remain separate regression evidence.

No old history is rewritten or retroactively certified. History discovered in S3 can include records from earlier versions that did not perform this extra read-back. The status screen still does not re-read all referenced resources when displayed. This checks byte integrity at confirmation time, not absence of malicious content or permanent availability after external deletion/access changes. Initial snapshot/Checkpoint manifest creation is not changed by this history-commit change.

## 日本語

作業種類は保存時照合の追加と差分検証、状態は検証済み・制限ありです。今回保存した原本・付随情報・分離データ・参照画像を固定版から再取得し、一致した場合だけ正式履歴を確定します。通常投稿は保存時のクライアントを引き継ぎ、共有キューも同じクライアントを使います。後日の再開は新要求のクライアントで同じ固定版を照合します。

不一致・取得失敗では正式履歴を書かず、既存の未確定操作と失敗理由の扱いを使います。順次取得に限定し、新しいワーカーや自動再開は追加しません。初期スナップショット／Checkpoint作成や旧履歴の再認定は今回の対象外です。

既存dmコンテナ内のS3・キュー代替による試験で、4種の資源の照合失敗・読取り失敗時に履歴PUTが0件、未確定操作が保持されること、原因解除後に同じ操作を確定できることを確認しました。実AWS障害・実WordPressトランザクション・ブラウザ・新ZIPの検証ではありません。実S3資産・既存コンテンツの変更や公開はありません。
