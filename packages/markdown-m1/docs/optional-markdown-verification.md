# Optional Markdown Documents dependency — differential verification

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

2026-10-26. Unreleased source change; published pre.2 remains unchanged.

## Work and completion

Type: defect correction and differential verification. State: verified in the existing dm isolation environment with an in-memory S3 double; not a new real-S3 or browser acceptance. Completion: native-only Baseline/Checkpoint/recovery does not require a loaded Markdown runtime, active Markdown is bundled and restored, and inactive Markdown with retained documents/originals stops before any save. All completed.

## Change

- The admin Baseline call no longer unconditionally supplies Markdown Documents as a required plugin.
- SiteSnapshot capture includes active Markdown Documents alongside the existing active supported adapters. The same rule applies to other callers of capture.
- If ozmd_document rows or _ozmd_source metadata exist without an active Markdown Documents plugin, capture stops with an explicit instruction before saving. Original data is not discarded.
- Existing plugin-file checks, resource verification, manifest confirmation, Checkpoint copying and recovery implementation are unchanged. The legacy individual-document route is unchanged.

## Evidence

Existing dm Docker/DB services were reused. Separate copies of the prior onboarding fixture were created under /tmp/owr-optional-md and owromd_20261026_source_/target_ tables; original trial and live content were not changed. PHP 8.3.36, existing WordPress 7.1.3, existing Markdown Documents 0.1.1. No new infrastructure, IAM changes, real S3 writes/deletes or release actions.

- Native capture: Markdown class absent and plugin inactive; complete Baseline and independent Checkpoint confirmed. Manifest/plugin software excludes Markdown Documents.
- Native restore: separate copied WordPress, Markdown class absent; restore succeeds and native post remains publish. 4 post records.
- Markdown capture: active plugin automatically included with its software; complete .md original matches.
- Inactive Markdown with content: explicit error, memory object count unchanged (no writes).
- Markdown restore: recorded .md original, publish state and active plugin match. Existing recovery prerequisite of an available Markdown runtime was retained in this fixture; this does not claim same-request loading of a previously unavailable class.
- The first test string accidentally interpolated `$x` in PHP. Corrected the test fixture and reran only Markdown capture/recovery, confirming literal math and Mermaid source equality. This was a test-data issue, not a product fix.

The test used actual isolated WordPress DB/file capture and restore with an in-memory versioned S3 transport. No actual AWS persistence or standard admin browser operation was repeated. The admin call change is reviewed statically. Real-S3 and browser evidence for the unchanged paths remains historical evidence, not a new acceptance of this candidate.

Local records: release-readiness/optional-markdown-20261026/output.txt and recheck.txt; setup and runner scripts are single-run fixture tools, not product dependencies.

## 日本語

作業種類は不具合修正・差分検証。状態は既存dm隔離環境で検証済み・制限ありです。管理画面の固定指定を外し、共通Baseline処理で有効なMarkdown Documentsだけを収録します。文書や原文が残るのに無効なら、保存前に停止します。原本の破棄や復旧方式の変更はありません。

通常投稿のみのBaseline・独立Checkpoint・別WordPressへの復旧、Markdown使用時の収録・原文一致・公開状態再現、無効化残存時の保存前停止を確認しました。S3はメモリー代替であり、実S3やブラウザ操作を今回再検証したものではありません。復旧側のMarkdownクラスは従来の前提どおり利用可能にして確認し、未ロードクラスの自動読込みは保証を追加していません。

公開済みpre.2とその利用ガイドの必須条件は、その配布版については引き続き正しい記述です。新しい候補の配布時に、版を区別してガイドを更新する必要があります。既存S3資産・コンテンツ・公開済みZIPは不変です。

## Follow-up: standard administration and real S3 (2026-10-26)

Type: differential verification and evidence recording. State: verified with the limitations below. Completion achieved: native-only and Markdown-enabled Baselines were created through the standard admin UI and restored on a separate WordPress using the dedicated real-S3 prefix.

Existing community/dm containers and onboarding fixtures were reused as separate copies under `/owr-md-run`. Scheduled work, updates, mail, daily protection and cleanup were disabled. Only the two previously modified product files were applied to the copies; no further product correction was needed.

- Native-only: Markdown inactive at capture and recovery. The confirmed Baseline required no Markdown plugin and its software archive contained no Markdown files. Admin recovery succeeded (6 post records).
- Markdown-enabled: a test document was published using the normal Markdown editor. Its Baseline included Markdown Documents 0.1.1 and 516 plugin archive entries. Admin recovery succeeded (8 post records).
- The source original, fixed S3 version of `markdown/8.md`, and restored original matched exactly, including Mermaid, math and code source. SHA-256: `5d9bdf850215e783ed00e527ce807b5a0b45b65caf902fe1faefea9d23913e2c`. Browser-input comparison alone normalized line endings; the three saved originals were compared without normalization.
- Selected native post, page and Markdown document fields (body/title/status/type) matched. Both fixed software archives matched their recorded hashes. Browser display confirmed the restored body and Mermaid; math appeared as literal source, not a newly accepted typesetting guarantee.

Both Baselines were through history 0. This follow-up did not repeat subsequent-history, Checkpoint or ZIP installation tests. Markdown was installed but inactive for the native case; the earlier isolated test additionally covered an absent runtime class. For Markdown recovery, the existing 0.1.1 plugin was activated beforehand. Identical files were already present in the target copy (0 file rewrites); this does not claim a new empty-disk software deployment test.

The dedicated prefix was empty before writes, including versions and delete markers on community. Standard EC2 role authentication was used. dm's version-list permission denial did not prevent ordinary listing or fixed-version recovery. A copied-admin role setup issue was fixed only in the fixture; it was not a product defect. Existing S3 assets, live content, IAM and published pre.2 ZIP remained unchanged. No deletion or release.

Local evidence: `release-readiness/optional-markdown-s3-20261026/RESULT-ja.md`, `comparison.json`, source/target readbacks and browser records. This section supersedes the earlier statement that browser/real-S3 acceptance had not yet occurred, while retaining the distinct scope of those earlier tests.

### 日本語：実S3・標準管理画面での追試

既存community/dmの試験データを別領域に複製し、未使用・使用の両条件で標準管理画面からBaseline作成と復旧に成功しました。未使用時はMD収録0件、使用時はMD依存と516ファイルを収録し、保存元・S3固定版・復旧先の原文が完全一致しました。通常投稿・固定ページ・MDの本文、タイトル、公開状態、型も一致しました。

使用時は復旧先でMD 0.1.1を事前有効化しています。through=0のBaseline差分試験であり、後続履歴・Checkpoint・ZIP導入更新を再検証したものではありません。同一ファイルが復旧先にあるため書換0件で、空ディスクへのソフトウェア展開を新たに保証しません。数式は原文保持を確認し、組版表示の保証は追加しません。

既存S3資産・コンテンツ・IAM・公開済みZIPは不変です。dmの全版一覧権限と複製管理者ロールの準備問題は環境条件として区別しました。追加の製品修正・削除・公開は行っていません。
