# Application rules — 0.3.1 candidate validation

Work: packaging, focused installation/update verification and evidence documentation. State: verified with the limits below; not a formal release. Completion criterion: the candidate includes the recognized recovery rules and preserves configuration, confirmed history, pending records and recovery results across fresh activation and replacement of the previous candidate. This supports independent original preservation and reconstruction according to explicit rules.

## Exact artifact

- [ozeki-wordpress-resilience-0.3.1-application-rules-final.zip](../../release-candidates/20261025-application-rules/ozeki-wordpress-resilience-0.3.1-application-rules-final.zip)
- SHA-256: `90581ce758ab714a75e8afcd763ca9fc6287216078a774fc95be14b79c73c9df`
- 7,424,768 bytes; 3,820 files; version header 0.3.1. Identify by full filename/hash, not the version alone.
- Previous separated-assets-final ZIP remains unchanged: `eabb776970a057253d6ae58650f1e732f8ee4308b153bc450435ec8724c168eb`.
- Vendor dependencies unchanged; all packaged product files match source. No new infrastructure or authentication helper.

## Scope and limits

The [common application rules](../../packages/markdown-m1/docs/application-rules.md) apply after baseline/history replay and before destination mutation. Unknown information stays in S3, while unrecognized attributes/settings are withheld from automatic application. The result lists paths and reasons without values. Invalid recognized types stop recovery. Custom settings, widgets and unrecognized theme options can be omitted, so full visual/behavioural equivalence is not guaranteed for such configurations. Software activation policy is unchanged. No new rollback, automatic retry, migration or S3 deletion was added.

## Separate verification layers

1. **Rule/code contracts:** extracted candidate code passed application-rules (including separated originals), recovery-result and recovery-errors contracts; PHP syntax passed. Recognized adapter settings, baseline/tail rule equivalence and malformed known-type rejection use fixtures, not a new AWS outage or browser test.
2. **Existing real S3 acceptance:** before packaging, the identical product sources restored seven records through history 1 using 24 fixed Checkpoint reads. Originals stayed unchanged; 21 omitted paths/reasons were displayed by the administration renderer. This does not newly certify every adapter's runtime, browser UI or rendering.
3. **ZIP installation/update:** existing dm Docker/core/database services reused with isolated table prefixes and content directories. Fresh activation and old separated-assets-final → new candidate extraction/replacement preserved settings, read-only S3 history 1, two synthetic nonempty pending records, errors, individual/site results (including omission report), failed-attempt state and fixture content. Both installations read the existing S3 original and matched all 3,820 ZIP files. Shared-site probe unchanged; no mail or trial scheduled execution.

The ZIP check is programmatic extraction/activation/replacement, not standard-browser upload. Synthetic pending records are preserved, not resumed. Complete real-S3 restoration was not repeated as a packaging test. A final bilingual README wording correction changed only two documentation files; tested code stayed identical, and both installed copies were rechecked against the corrected final ZIP and their saved state.

## Environment and harness findings

No new product defect was found during packaging. The existing duplicate DISABLE_WP_CRON warning comes from the shared-site probe bootstrap. The preceding real-S3 trial's binary-file JSON digest error was corrected in its test recorder before restoration; it was not a product failure. Existing S3 resources, live content and IAM settings were not changed. No formal release or PR was created by this packaging task.

## 日本語

作業種類は最終ZIP化・導入更新の差分検証・文書整理、状態は検証済み・制限ありです。完成条件は、適用規則を収録した候補の新規導入と旧候補からの更新で、設定・正式履歴・未確定記録・復旧結果が保持されることです。

既存dmの隔離DB接頭辞と専用ファイル領域を使い、新規有効化・旧ZIPからの置換更新で保持を確認しました。非空の未確定記録2件は合成試験データで、再開は実行していません。S3履歴と原本は読取りだけです。全3,820ファイルを最終ZIPと照合し、既存サイトの確認値は不変でした。

実S3復旧、ローカル契約試験、ZIP導入更新は別の検証範囲です。今回はブラウザ更新・全連携の実動作・未確定操作の再開を新たに検証していません。未知情報をS3に残す一方、認定していない設定は自動適用しないため外観・動作が変わり得ます。メール送信・定期実行・S3変更／削除・正式公開は行っていません。
