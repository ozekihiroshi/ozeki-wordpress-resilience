# Separated recovery originals / 原本と付随情報の分離

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

Status: included in the 0.3.1 separated-assets-final candidate, verified with the limits below; absent from the earlier recovery-errors-final ZIP. No release or existing S3 migration.

## English

The storage codec `owr-separated-assets-1` is shared by normal structured saves, initial snapshots and Checkpoints. Markdown/HTML remain complete plain files. Known content fields in JSON records become separate UTF-8 files: post bodies/excerpts, comment bodies, table cell JSON, Markdown source, Flamingo submitted-field JSON and member identity text. Images/PDFs remain independent binary files. The metadata records the mapping, attributes and remaining structure; existing replay adapters consume a losslessly reassembled operation in memory. The mixed `content.json` is no longer written by new complete-site snapshots; it is assembled only for the existing internal replay/import implementation.

- Normal originals use `owr-md-original-2`: raw `source.md`/`source.html`, or a `source.json` index plus `data/*.html|md|txt|json`, and `metadata.json`. Each data part has its own fixed Version ID and SHA-256. The original operation digest is also checked after reassembly.
- Complete-site snapshots keep their manifest format with `asset_format: owr-separated-assets-1`, `resources/assets/data/*` and `resources/assets/metadata.json`. All required files are copied into the Checkpoint's own resource scope. Software and media remain separate resources. Assets do not depend on an earlier snapshot.
- A plain text/JSON reader can read each content file without Resilience, WordPress or a DB. Metadata is still needed to associate identity, status, relationships and rendering settings for site reconstruction. Plain readability does not mean that HTML or table cells should be executed or rendered without the existing content policy.
- Unknown fields are retained unchanged in the remaining metadata, not discarded, newly certified or newly enabled. Classification is deliberately limited to known fields. PHP-serialized submitted fields are exported as readable JSON when they contain plain values; unusual serialization is preserved if needed for lossless reconstruction. Settings-only operations can have no data parts. Authentication hashes and approval/settings data are not presented as ordinary content text.
- Legacy originals and complete-site snapshots remain readable without rewriting S3. Newly written records require this reader; **the earlier recovery-errors-final ZIP cannot be used as a downgrade reader for the new format**. No claim of compatibility with old external scripts that read adapter `source.json` as a monolithic operation. Use `Store::originalSource()` for typed replay. Existing unchanged legacy asset Checkpoints are not silently migrated.
- This change does not introduce a certification allowlist or change the existing software/metadata activation policy. Retaining unknown information is distinct from approving its use. It does not add deletion, automatic retry, automatic rollback or server infrastructure.

## 日本語

通常保存・初期スナップショット・Checkpointで、共通の分離処理を使います。Markdown／HTMLは完全な原文ファイルです。JSONにまとめていた既知の本文・コメント・表のセル・問い合わせの入力値・会員識別の文字情報を独立ファイルに分け、属性・関連情報・表示設定等は対応表とともにメタデータへ残します。画像・PDF・ソフトウェアも別資源です。新しいサイト全体保存では、混在した`content.json`をS3へ書かず、従来の復旧処理に渡す時だけメモリ上で組み戻します。

独立ファイルは通常のテキスト／JSON読取りで利用できます。サイトとしてのID・公開状態・関係・表示を再現するにはメタデータも必要です。未知の項目は削除せず残し、今回新しく認定・有効化するわけではありません。分類できない項目を独断で原本扱いへ変更しません。保存形式の分離と、認定範囲を適用する規則の整備は別の作業です。

既存S3資産を移行・上書きせず旧形式を読み取れます。ただし、新形式を記録した後に旧recovery-errors-final ZIPへ戻しても、新形式の復旧はできません。今回のコードはseparated-assets-final候補に収録し、正式公開はしていません。認定範囲外の情報を削除する処理、実削除、自動再開、巻戻し機構の追加はありません。

## Verification / 検証範囲

See [acceptance](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/separated-assets-m1.md). Memory-S3 contracts verify standalone content, unknown-field preservation, legacy reads, missing/corrupt data rejection, independent Checkpoints after ancestor removal and history replay. An actual WordPress/DB trial on existing dm uses new isolated table prefixes and content directories with a disk-persisted memory-S3 fixture: initial capture, normal page original/confirmation, independent Checkpoint, source directory unavailability, blocked source DB access and destination reconstruction. This is not actual AWS acceptance or browser/plugin-rendering acceptance. No cloud objects are touched.

During actual initial-snapshot restore, an absent `WPLANG=false` exposed an existing option-write edge case: WordPress `update_option` can return without creating an absent option equal to its default. The persisted-value helper now adds only an absent option after an error-free update/read, then checks storage again. Errors still stop recovery. A separate, manually initiated trial after the cause was corrected passed; there is no automatic retry.

A subsequent real-S3 trial also passed: existing community writer and dm reader, standard SDK EC2-role authentication, isolated WordPress data and a new dedicated lab prefix. Normal page-save HTML, initial HTML/Markdown and Checkpoint HTML/Markdown/table originals were directly readable. Recovery read 24 fixed versions exclusively inside the Checkpoint and matched the supported fixture state and unknown captured metadata. Existing S3 current-object inventory and dm shared-site probe were unchanged. This adds real storage/cross-host evidence, not new browser, all-adapter or ZIP acceptance. See the acceptance document above for exact limits.

その後の実S3検証も成功しました。既存communityで保存、dmで復旧し、標準EC2ロール認証を使用しています。通常保存・初期取得・Checkpointの原本単独取得と、Checkpoint内部の固定版24件だけによる再構築を確認しました。既存資産は変更せず、ブラウザ・全アダプター・ZIPの試験を追加したものではありません。
