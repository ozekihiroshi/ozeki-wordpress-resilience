# Updating an existing installation / 既存環境の更新

**First installation?** Follow the [first-time setup guide](user-guide.md). **初めての導入は[初回導入ガイド](user-guide-ja.md)へ。** このページは既に導入済みの場合だけ使用します。

## English

1. Download the ZIP linked in the [README](../README.md) and verify its checksum. Before updating, preserve the current plugin files, database and settings using your usual maintenance procedure. Pause editing and record settings, confirmed history, pending operations and recovery results.
2. If the old prerelease uses `ozeki-wordpress-resilience/`, deactivate it first. The current folder is `ozeki-resilience/`; do not activate both copies. Keep the old files until the switch is verified. Do not uninstall as an update method.
3. Use **Plugins → Add New Plugin → Upload Plugin**. For the same folder, choose **Replace current with uploaded**; for a new folder, install and activate the new copy. Wait for success.
4. Confirm activation and compare settings, pending operations, confirmed history and recovery results. If replacement fails, inspect the error and installed state before retrying.

Where possible, resolve pending operations before updating. Otherwise preserve them and compare after the update; do not clear queues to simplify the procedure. A plugin update does not require running site recovery. See [save resumption](save-resume.md) when needed.

## 日本語

1. [README](../RAADME-jp.md)のZIPを取得してハッシュを照合します。通常の保守手順で現行プラグイン・DB・設定を退避し、編集を一時停止します。設定・確定履歴・未確定操作・復旧結果を控えてください。
2. 旧試験版のフォルダーが `ozeki-wordpress-resilience/` なら先に停止します。現行は `ozeki-resilience/` です。同時に有効化せず、切替確認まで旧ファイルを残します。更新のためにアンインストールしません。
3. **プラグイン → 新規プラグインを追加 → プラグインのアップロード** を使います。同じフォルダーなら「アップロードしたもので現在のものを置き換える」、別フォルダーなら新しい方を導入・有効化し、成功表示を確認します。
4. 有効化・設定・未確定操作・確定履歴・復旧結果を更新前と照合します。置換に失敗した場合は、エラーと配置状態を確認してから再試行してください。

未確定操作は可能なら更新前に解消します。残す場合は保全して更新後に照合し、更新の都合でキューを消しません。プラグイン更新の確認のためにサイト復旧を行う必要はありません。必要時は[保存再開手順](save-resume.md)を参照してください。

## Updating from 0.3.1 / 0.3.1からの更新

Existing storage settings and enabled protection are retained. Older initial saves may show **Not checked** in the new checklist; this does not mean they were lost. Confirm the terms when next saving settings. If you turn protection off and restart it, first create a trusted initial save with 0.3.2 or later for that storage destination. See [preparation](setup-readiness.md).

保存先設定と有効な保護は引き継ぎます。過去の初期保存が新しい準備画面で「未確認」でも、消失した意味ではありません。次に設定を保存するときに利用条件を確認してください。保護を停止して再開する場合は、その保存先へ0.3.2以降で信頼できる初期保存を作成します。[準備状況の案内](setup-readiness-ja.md)も参照してください。

## Verification records / 検証記録

Past checks describe their specific builds and environments; they are not extra installation steps. 過去の確認範囲は以下に分けて記録しています。

- [Browser ZIP update](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/browser-zip-update-m1-031.md)
- [Update with pending operations](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/pending-zip-update-m1-031.md)
- [WordPress.org candidate checks](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/wordpress-org-checks.md)

## 0.3.3 / ACF free

Updating from 0.3.2 retains existing settings, history and pending saves. Existing article protection continues. To add ACF fields to protection, activate the supported free version and create a new trusted Baseline while editing is paused. Earlier captures do not acquire ACF coverage retroactively. See [ACF scope](acf-free.md).

0.3.2からの更新では、設定・履歴・未完了の保存を保持し、既存の記事保護を継続します。ACFフィールドを保護に加える場合は、対応する無料版を有効化し、編集を止めて新しい信頼済みBaselineを作成します。過去の保存が自動でACF対応になるわけではありません。[ACF対応範囲](acf-free-ja.md)。
