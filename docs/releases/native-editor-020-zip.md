# Native editor 0.2.0 final ZIP validation

The frozen plugin and matching external runtime kit were installed in dedicated
generated-data WordPress environments. Fresh installation and upgrade from PR #18's
verified 0.2.0 ZIP each passed 21 browser checks. Both also preserve settings, cron,
posts/meta, bridge records and history during installation; reinstall while a failed
save is pending and after completed saves preserves the same state.

The old runtime's generation remains readable after updating the worker, its four
existing immutable/configuration records retain their hashes, and the new runtime
extends it. The final ZIP runtime reconstructs the upgraded browser's final generation
after removing the source WordPress; request-derived Q matches, the target remains
private and external side-effect attempts are zero.

Final review also added four fragment regression checks and an explicit skip for the real-WordPress KSES test when its external code fixture is absent. CI provisions DOM and runs the asynchronous media checks. The old 12-second documentation was corrected.

The extracted kit passed 39 material, 6 native, 8 distribution, 5 PHP guard,
2 PHP rendering and 3 asynchronous media regression checks. All archive entries
were hash-checked, installed plugin files matched the archive, and frozen bytes
were rechecked after validation. Results in this document are post-freeze evidence;
they are not recursively included in the ZIP they describe.

These lifecycle tests use the filesystem S3 double. The preceding 19-check real-S3
native-editor test is separate evidence, not a claim that this ZIP lifecycle run
used live S3. Product fixes: shared KSES HTML canonicalization and asynchronous
media registration. Previously observed WSL/Docker startup issues and the scoped
IPv4 workaround are environment conditions. The extended media wait and native
queue assertion are test-harness changes. No new product failure was found here.

## Scope and remaining boundaries

Administrator-only explicit enrollment, basic static core blocks and PNG/JPEG.
Install the matching external kit; installation alone does not enable S3 protection.
Classic/Markdown plugins, custom/dynamic blocks, forms, taxonomy/custom fields,
scheduling and general plugin compatibility remain unsupported. Recovery targets
remain private, with no automatic public activation or production migration.
Existing legacy three-page data is not automatically converted. No production,
IAM, existing retention or existing demo changes were made. Owned trial containers
were removed; journals and earlier failed evidence were retained.

## 日本語

最終ZIPの新規導入と、PR #18の検証済み0.2.0 ZIPからの更新で、それぞれ21項目に成功しました。
設定・Cron・投稿・メタデータ・履歴・受渡し記録を保持し、保存失敗中の要求と完了済み世代が
再インストール後も変わらないことを確認しました。外部処理の旧世代も読め、既存記録を維持して
次の世代へ進めます。更新後に編集した最終世代を元WordPress撤去後に再構築し、Qと一致しました。

今回のZIP試験は模擬S3です。前回の実S3試験19項目とは区別します。製品側の修正はHTMLのKSES
正規化とメディア登録の非同期化です。WSL・Docker起動遅延や試験限定IPv4優先は環境問題、
待機時間とキュー完了検査の変更は試験基盤として記録しています。今回新たな製品不具合は検出していません。
英語READMEとRAADME-jp.mdに対応範囲・制限・外部キット更新条件を収録しています。
本番変更・自動公開は行っていません。

## Frozen artifact hashes

- `ozeki-wordpress-resilience-0.2.0.zip`: `84fb80d8303898fcdef18f1090edff8d77628331ad091e130f00b4202e10cfcb`
- `owr-development-kit-0.2.0.zip`: `1292aca61efcb7ec413381d933b4252b4d11bbd1109ed798aecb8a75562f3269`

[Machine-readable evidence](../../evidence-public/native-editor-zip-validation.json).
