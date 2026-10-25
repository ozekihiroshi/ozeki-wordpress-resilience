# Installation and ZIP update / 導入・ZIP更新手順

For first-time source/destination setup: [English](start-here.md) · [日本語](start-here-ja.md).

## English

1. Prepare a supported WordPress/PHP environment and the required plugins described in the [README](../README.md). Use the exact validated ZIP linked there and verify its SHA-256 against the acceptance record; the display version alone does not identify the candidate. For a new installation, configure the dedicated S3 scope and standard AWS authentication after activation.
2. Before updating, preserve the current plugin files, database and configuration using your normal maintenance procedure. Record active plugins, S3 settings, latest confirmed history, pending operations/errors and recovery results. Verify administrator login first, including WP-Members activation where applicable. Avoid concurrent editing during the update.
3. Check that WordPress permits plugin installation, PHP upload/POST limits exceed the ZIP plus request overhead, and the web-server user can replace the plugin files. Apply any necessary changes only within the intended maintenance environment; do not broadly relax shared-server permissions. Record temporary settings for restoration.
4. In **Plugins → Add Plugin → Upload Plugin**, select the ZIP and click **Install Now**. On an existing installation review the comparison and choose **Replace current with uploaded**; on a fresh installation activate after installation. Wait for the success result.
5. If upload or replacement fails, record the exact error and inspect the installed state before retrying. A copy failure may leave a partial installation. Resolve the identified environment problem or restore the previous files before continuing; do not treat a failed upload as success. Remove only identified test-upload artifacts, never existing content.
6. After success verify activation, configuration, confirmed S3 history, pending operations/errors and recovery results against the baseline. Check existing content/member preservation and restore temporary environment settings. Updating the plugin does not require rerunning site recovery or sending mail.

**Pending work:** do not delete or clear pending queues to simplify an update. Where possible complete the existing history-resume workflow first; otherwise preserve the complete pending state and compare it after updating before resuming. Capture the baseline after the save request has fully ended: native-detail records can be queued at shutdown. The [nonempty-queue browser test](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/pending-zip-update-m1-031.md) preserved one article and one native-detail operation, including their IDs, payloads and recorded errors; browser Resume history confirmed those same operations as 69–70 and cleared the pending/error display. Other queue combinations remain unverified. Earlier synthetic overwrite tests are separate evidence.

**Accepted scope:** the [0.3.1 browser update](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/browser-zip-update-m1-031.md) replaced a prior same-version trial deployment with the frozen validated ZIP and preserved settings, history and recovery results. Earlier fresh-install/extraction tests are separate evidence. This does not establish all version migrations, all hosting configurations, or arbitrary nonempty-queue combinations. The later article/native-detail test adds only the scope described above. Core may register maintenance events during administration; event registration and scheduled execution are separate. Periodic execution remains deferred.

## 日本語

1. [README](../RAADME-jp.md)に従いWordPress・PHP・必要プラグインを用意します。リンク先の検証済みZIPを使い、検証記録のSHA-256と照合してください。表示バージョンだけでは候補を特定できません。新規導入では有効化後に専用S3範囲と標準AWS認証を設定します。
2. 更新前に通常の保守手順で現行プラグイン・DB・設定を退避し、有効プラグイン、S3設定、最後の確定履歴、未確定操作／エラー、復旧結果を記録します。WP-Members利用時の有効化を含め管理者ログインを確認し、更新中の同時編集を避けます。
3. プラグイン変更の許可、ZIPと要求の付帯データを受け付けるPHP上限、Webサーバによるプラグインファイル置換権限を確認します。必要な変更は対象環境に限定し、共有権限を一律に緩和しないでください。一時設定は復帰できるよう記録します。
4. 「プラグイン → 新規追加 → プラグインのアップロード」でZIPを選び「今すぐインストール」。更新時は比較内容を確認して「アップロードしたもので現在のものを置き換える」、新規導入時はインストール後に有効化します。成功表示まで確認してください。
5. 失敗時は具体的な理由と配置状態を確認します。コピー失敗は一部だけ置換された可能性があります。環境原因の解消または旧ファイルへの復帰後に続行し、失敗を成功扱いにしないでください。清掃対象は特定した試験アップロードだけとし、既存コンテンツは除去しません。
6. 成功後、有効化・設定・S3正式履歴・未確定操作／エラー・復旧結果と既存コンテンツ／会員の保持を更新前と照合し、一時設定を戻します。更新確認のためにサイト復旧やメール送信を再実行する必要はありません。

**未確定操作：** 更新を簡単にするためにキューを消さないでください。可能なら既存の履歴再開手順で確定させ、未確定のまま更新する場合は操作全体を保全し、更新後に照合してから再開します。付随情報はshutdown時にキューへ入る場合があるため、保存要求が終了してから基準を採取してください。[非空キュー更新試験](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/pending-zip-update-m1-031.md)では本文1件・付随情報1件のID・内容・エラーを保持し、画面からの再開で同じ操作が69～70に確定、未確定・エラー表示が解消しました。他の組合せは未検証です。以前の合成キュー上書き試験とは別の証拠です。

**検証範囲：** [0.3.1標準画面更新](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/docs/releases/browser-zip-update-m1-031.md)では、同じ表示バージョンの旧試験配置を検証済みZIPへ置換し、設定・履歴・復旧結果を保持しました。以前の新規導入／展開試験とは別の証拠です。全版移行・全ホスティング設定・任意の非空キューの組合せは保証しません。後続試験で追加した確認範囲は上記の本文・付随情報2件です。管理画面操作でCron予約が登録される場合がありますが、予約登録と定期処理実行は別です。定期実行は引き続き後回しです。

## GFS candidate differential check / GFS候補の差分確認

New distribution ZIP verification reused the existing dm WordPress core and DB service with isolated tables/content. Fresh activation and replacement of published v0.3.1-pre.1 preserved GFS/S3 settings, the registered (not executed) slot, two synthetic pending records, diagnostics, recovery results and test content. Existing formal history and its original were read from real S3 using standard authentication. Installed files matched the ZIP byte-for-byte. This was PHP-driven extraction/activation/reload, not browser upload, queue resumption, new S3 writes, real deletion or elapsed-time scheduling. A duplicate DISABLE_WP_CRON warning came from the test bootstrap/shared configuration; assertions passed and it is not evidence of a product defect.

既存dmのWordPress本体・DBサービスを再利用し、テーブルとコンテンツを隔離して新規導入と公開済みv0.3.1-pre.1からの更新を確認しました。GFS・S3設定、予約情報（実行なし）、合成した未確定操作2件、診断・復旧結果、試験記事を保持しました。標準認証で既存S3正式履歴と原本を読み取り、配置ファイルはZIPと全件一致しました。PHPによる展開・有効化・再起動の確認であり、ブラウザアップロード、履歴再開、新規S3書込み、実削除、実時間の定期実行は含みません。DISABLE_WP_CRONの重複定義警告は試験用起動処理と共有設定の組合せによるもので、検証は合格しており製品不具合の証拠ではありません。
