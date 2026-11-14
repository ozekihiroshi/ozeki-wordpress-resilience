# Updating an existing installation / 既存環境の更新

Install WordPress, themes and required plugins separately from trusted distributors before recovery, and activate the required plugins. Resilience restores information assets and their supported relationships; it does not install or activate software from S3. It keeps the destination theme selection. Unknown settings are reported without being applied.

復旧先のWordPress・テーマ・必要なプラグインは、管理者が信頼できる配布元から別途インストールし、必要なプラグインを有効化してください。Resilienceが戻すのは情報資産と対応する関係情報です。S3からソフトウェアを配置・有効化せず、復旧先のテーマ選択も維持します。不明な設定は適用せず、結果に表示します。

**First installation?** Follow the [first-time setup guide](user-guide.md). **初めての導入は[初回導入ガイド](user-guide-ja.md)へ。** このページは既に導入済みの場合だけ使用します。

## English

**rc.14 preparation checks:** Update recovery destinations too. Missing language packs or required software are reported before content replacement; prepare them from trusted sources and recheck. Existing originals/history and protection/scheduling settings need no migration.

**rc.13 Flamingo correction:** Existing receipt originals need no migration. Update the recovery destination too. If a receipt was already re-saved with missing values, recover from an earlier original that still contains them; updating alone cannot recreate lost values.

**rc.12 compatibility:** Existing originals remain readable. After complete-site recovery, new saves retain the known earlier site/image locations without rewriting Markdown. Recovery points containing this new reference context require rc.12 or a later compatible reader; rc.11 rejects them. Prepare the updated version on recovery destinations too. Updating alone does not rewrite S3 history or require a new Baseline.

1. Download the ZIP linked in the [README](../README.md) and verify its checksum. Before updating, preserve the current plugin files, database and settings using your usual maintenance procedure. Pause editing and record settings, confirmed history, pending operations and recovery results.
2. If the old prerelease uses `ozeki-wordpress-resilience/`, deactivate it first. The current folder is `ozeki-resilience/`; do not activate both copies. Keep the old files until the switch is verified. Do not uninstall as an update method.
3. Use **Plugins → Add New Plugin → Upload Plugin**. For the same folder, choose **Replace current with uploaded**; for a new folder, install and activate the new copy. Wait for success.
4. Confirm activation and compare settings, pending operations, confirmed history and recovery results. If replacement fails, inspect the error and installed state before retrying.

Where possible, resolve pending operations before updating. Otherwise preserve them and compare after the update; do not clear queues to simplify the procedure. A plugin update does not require running site recovery. See [save resumption](save-resume.md) when needed.

## 日本語

**rc.14の準備確認：** 復旧先にも更新版を用意してください。不足する言語パックや必要なソフトウェアを内容の置換前に案内します。信頼できる配布元から準備し、再確認してください。既存原本・履歴、保護・定期保存設定の移行は不要です。

**rc.13のFlamingo修正：** 既存の受信原本の移行は不要です。復旧先にも更新版を用意してください。欠落した状態で再保存した受信は、値が残っている以前の原本から復旧します。更新だけで失われた値を補完するものではありません。

**rc.12の互換性：** 既存原本は引き続き読めます。サイト全体復旧後の新しい保存では、Markdownを書き換えずに過去のサイト・画像保存先の対応を引き継ぎます。この新しい参照情報を含む復旧点にはrc.12以降の対応版が必要で、rc.11は読み取りを拒否します。復旧先にも更新版を用意してください。更新だけでS3履歴を書き換えたり、Baselineを作り直したりする必要はありません。

1. [README](../RAADME-jp.md)のZIPを取得してハッシュを照合します。通常の保守手順で現行プラグイン・DB・設定を退避し、編集を一時停止します。設定・確定履歴・未確定操作・復旧結果を控えてください。
2. 旧試験版のフォルダーが `ozeki-wordpress-resilience/` なら先に停止します。現行は `ozeki-resilience/` です。同時に有効化せず、切替確認まで旧ファイルを残します。更新のためにアンインストールしません。
3. **プラグイン → 新規プラグインを追加 → プラグインのアップロード** を使います。同じフォルダーなら「アップロードしたもので現在のものを置き換える」、別フォルダーなら新しい方を導入・有効化し、成功表示を確認します。
4. 有効化・設定・未確定操作・確定履歴・復旧結果を更新前と照合します。置換に失敗した場合は、エラーと配置状態を確認してから再試行してください。

未確定操作は可能なら更新前に解消します。残す場合は保全して更新後に照合し、更新の都合でキューを消しません。プラグイン更新の確認のためにサイト復旧を行う必要はありません。必要時は[保存再開手順](save-resume.md)を参照してください。

## Updating from 0.3.1 / 0.3.1からの更新

Existing storage settings and enabled protection are retained. Older initial saves may show **Not checked** in the new checklist; this does not mean they were lost. Confirm the terms when next saving settings. If you turn protection off and restart it, first create a trusted initial save with 0.3.2 or later for that storage destination. See [preparation](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/setup-readiness.md).

保存先設定と有効な保護は引き継ぎます。過去の初期保存が新しい準備画面で「未確認」でも、消失した意味ではありません。次に設定を保存するときに利用条件を確認してください。保護を停止して再開する場合は、その保存先へ0.3.2以降で信頼できる初期保存を作成します。[準備状況の案内](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/setup-readiness-ja.md)も参照してください。

## 0.3.3 / ACF free

Updating from 0.3.2 retains existing settings, history and pending saves. Existing article protection continues. To add ACF fields to protection, activate the supported free version and create a new trusted Baseline while editing is paused. Earlier captures do not acquire ACF coverage retroactively. See [ACF scope](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/acf-free.md).

0.3.2からの更新では、設定・履歴・未完了の保存を保持し、既存の記事保護を継続します。ACFフィールドを保護に加える場合は、対応する無料版を有効化し、編集を止めて新しい信頼済みBaselineを作成します。過去の保存が自動でACF対応になるわけではありません。[ACF対応範囲](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/acf-free-ja.md)。

## Review-response update / 審査対応版への更新

Settings, pending saves, recovery mappings and scheduled Checkpoints are carried over automatically. Open **Tools → Resilience** after updating and confirm the settings and protection status. Existing S3 originals and history are not rewritten; a new initial save is not required solely for this update.

設定・未完了の保存・復旧用の対応情報・Checkpointの予約は自動で引き継ぎます。更新後は **ツール → Resilience** から設定と保護状態を確認してください。S3の既存原本と履歴は書き換えず、この更新だけを理由に初期保存をやり直す必要はありません。

If the settings update cannot finish, public pages and administrator sign-in remain available, while saving is paused. Open **Tools → Resilience**, ask your hosting administrator to check database write access and locks, then select **Retry**. Do not delete pending saves or recreate the Baseline.

設定の引き継ぎに失敗した場合も、公開ページの閲覧と管理者ログインは利用できますが、保存は一時停止します。**ツール → Resilience** の案内に従い、サーバー管理者にDBの書込みとロックを確認してもらい、**再試行**を押してください。未完了の保存の削除やBaselineの作り直しは不要です。

## rc.11: ACF definitions and member fields / ACF定義・会員項目

rc.11 includes WP-Members field definitions and standalone ACF definition history. Existing originals remain readable and are not rewritten. After enabling protection, confirm definition changes in formal history. New ACF definition records and the Baselines/Checkpoints containing them require rc.11 or a later compatible recovery implementation; keep that version available for the recovery destination. An update alone does not require a new Baseline when the existing one already covers the installed ACF version.

rc.11はWP-Membersの会員項目定義と、ACF定義単独の履歴保存に対応します。既存原本は変更せず引き続き読めます。保護中の定義変更後は正式履歴への確定を確認してください。新しいACF定義履歴と、それを含むBaseline・Checkpointにはrc.11以降の対応する復旧処理が必要です。復旧先にも用意できるよう、この版を保管してください。既存Baselineが現在のACF版を含む場合、更新だけを理由に作り直す必要はありません。

## rc.15: file access / ファイル閲覧条件

rc.15 introduces new media-bearing originals and site recovery points that require the rc.15-compatible reader; older versions reject them. Existing originals remain unchanged and readable; files without recorded access conditions are held rather than published. After updating the source, record file access conditions and confirm formal history. Keep the updated reader for recovery. See [the contract and verification scope](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/media-access-contract.md).

rc.15の新しい画像付き原本と復旧ポイントには、rc.15対応の復旧処理が必要で、旧版は読み取りを拒否します。既存原本は変更せず読めますが、閲覧条件の記録がないファイルは公開配置を保留します。保存元の更新後はファイルの閲覧条件を再確認・記録し、正式履歴への確定を確認してください。復旧用にも更新版を保管します。[動作と確認範囲](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/media-access-contract.md)を参照してください。
