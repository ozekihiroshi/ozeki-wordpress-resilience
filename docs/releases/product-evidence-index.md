# Product evidence and detailed scope / 製品の検証記録・詳細範囲

This index keeps the README focused on purpose and architecture while preserving traceable evidence. It does not create new acceptance claims. Records refer to different candidates and environments: read each record's scope before applying it to the current release.

READMEは目的と構成を説明し、詳細な実証はこの索引から参照します。新たな受入を宣言する文書ではありません。記録ごとに対象候補・環境・検証範囲が異なります。

## Current package / 現在の配布物

[GitHub v0.3.1-pre.1](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/v0.3.1-pre.1) · [Package identity, checksum and actual S3 write acceptance / 配布物・実S3書込み](prerelease-package-m1-031.md)

The latest representative protected page/image test used real original PUTs, fixed-version GETs and a real history PUT. The preceding [save-verification candidate](save-verification-final-m1-031.md) used real GETs but an intercepted history PUT; those are separate tests. Its installation/update tests were programmatic extraction/replacement, not browser upload. The release changes four documentation files from that tested candidate; all executable entries match. This README-only reorganization does not replace any released ZIP.

最新の代表的な記事・画像の確認は実PUT・実GET・正式履歴の実PUTです。先行する保存時照合試験の履歴PUTは模擬でした。両者を混同しません。導入・更新はプログラムによる展開・置換で、ブラウザからの更新とは別です。公開版は検証済み候補から文書4ファイルだけの差であり、今回のREADME再構成によって公開ZIPを差し替えることはありません。

## Verification map / 検証の索引

[Unpublished GFS candidate: implementation, real-S3 and ZIP evidence / 未公開GFS候補の実装・実S3・ZIP検証](gfs-final-m1-031.md). This is separate from the published Pre-release; no actual deletion acceptance is claimed. 公開済み版とは別の候補であり、実削除の受入は主張しません。

| Topic / 項目 | Records / 記録 | Boundary / 読取り上の注意 |
|---|---|---|
| GFS configured-time execution / GFS設定時刻の取得 | [Timed execution and environment incident](gfs-timed-acceptance.md) | One real weekly slot via standard server-invoked wp-cron.php; not HTTP loopback, long-term recurrence or actual deletion / 標準入口の一回、HTTP起動・長期反復・実削除は未確認。本体更新処理は試験環境の事象 |
| Originals and separation / 独立原本・分離 | [Format](../../packages/markdown-m1/docs/separated-assets.md), [ZIP](separated-assets-final-m1-031.md) | Original extraction, baseline and Checkpoint reconstruction; not universal format/plugin support / 原本取出し・基点・Checkpointの確認で、全形式の保証ではない |
| Save confirmation / 履歴確定 | [Read-back contract](../../packages/markdown-m1/docs/commit-verification.md), [Failure visibility](../../packages/markdown-m1/docs/save-confirmation.md), [Resume](save-resume-acceptance.md), [Editor failure](editor-save-final-m1-031.md) | Injected failures are not actual AWS outages / 異常注入と実AWS障害は別 |
| Combined reconstruction / 同居再構築 | [Acceptance](combined-site-acceptance.md), [ZIP](combined-final-m1-031.md) | Recorded supported combinations, not arbitrary installed plugins / 記録した組合せの範囲 |
| Selected recovery point / 指定時点 | [Acceptance](site-point-time-m1-031.md), [ZIP](point-time-final-m1-031.md) | Browser selector evidence and package checks are separate / 画面操作と導入試験を区別 |
| Recovery rules / 適用規則 | [Current rules](../../packages/markdown-m1/docs/application-rules.md), [Evidence](application-rules-final-m1-031.md) | Unknown captured information retained; omissions can change appearance / 未知情報は保持、未適用による外観差あり |
| Failure/result reporting / 失敗・結果表示 | [Failure detection](recovery-errors-m1-031.md), [ZIP](recovery-errors-final-m1-031.md), [Result display](recovery-result-final-m1-031.md), [Save status](save-status-final-m1-031.md) | Failure is not proof of zero changes or completed rollback / 失敗は無変更・巻戻し完了の証明ではない |
| Native editing / 通常編集 | [Editor/images](native-m1-031.md), [Article details](native-details-browser-acceptance.md), [ZIP](native-details-final-m1-031.md) | Chrome evidence does not resolve the in-app browser issue / Chrome確認とアプリ内ブラウザ問題は別 |
| Adapter acceptance / 連携 | [Comments](comments-m1-031.md), [Forms](forms-m1-031.md), [Form lifecycle](form-lifecycle-m1-031.md), [Members](members-m1-031.md), [Tables](tablepress-m1-031.md), [Table browser](tablepress-browser-acceptance.md) | Consult current application rules before interpreting older presentation tests / 過去の表示試験は現行適用規則と合わせて読む |
| Install/update / 導入更新 | [Browser ZIP](browser-zip-update-m1-031.md), [Nonempty queue](pending-zip-update-m1-031.md), [Latest baseline candidate](save-verification-final-m1-031.md) | Different candidate hashes and queue fixtures; not every migration / 候補ハッシュ・試験キューを区別 |
| Retention / 保持 | [Site preview](site-retention-final-m1-031.md), [Legacy asset-only path](../../packages/markdown-m1/docs/checkpoints.md) | Site-wide preview is not complete-site deletion acceptance / サイト全体プレビューと実削除の受入は別 |
| Environment preparation / 環境準備 | [Administrator activation](administrator-activation-acceptance.md), [History 68 preflight](history68-recovery-preflight.md) | Destination-only test data and account setup are environment concerns, not new preservation requirements / 復旧先だけの作業データやアカウント設定を製品要件にしない |

## Historical explanations / 過去の説明の保全

The former feature/test-heavy READMEs are preserved with relocated links: [root English](../archive/readme-before-philosophy-20261025/root-en.md), [root Japanese](../archive/readme-before-philosophy-20261025/root-ja.md), [package English](../archive/readme-before-philosophy-20261025/package-en.md), [package Japanese](../archive/readme-before-philosophy-20261025/package-ja.md). They are historical records, not the current scope specification. In particular, the old TablePress inline-CSS statement is superseded by the current application rules, which withhold custom CSS.

旧READMEの詳細説明は上記に保全しました。現行仕様ではありません。特に旧TablePress欄のinline CSS復旧の説明より、カスタムCSSを自動適用しない現在の適用規則を優先します。

Earlier 0.2.0 worker/signing/private-preview research is preserved in the [previous research archive](../archive/readme-before-product-consolidation-20261024/root-en.md) / [日本語](../archive/readme-before-product-consolidation-20261024/root-ja.md). Research constraints do not redefine the standard product architecture.
