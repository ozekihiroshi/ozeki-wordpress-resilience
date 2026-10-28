# Resume unfinished saves / 未完了の保存を再開する

## English

On the surviving source site, open **Tools → Resilience → Save protection status**. This resumes saving to S3; it does not run recovery on a destination.

1. Check the affected content, pending count and failure reason. If history cannot be read, resolve that access problem before judging the save complete.
2. Correct the storage or access problem. Keep the affected article unchanged and retain pending data while doing so.
3. Select **Resume history** once. If the response times out, check the history and pending state before retrying.
4. Confirm that the expected content and related information appear in confirmed history and their pending entries are cleared. One edit can produce separate records for the body and its related information.
5. If resumption fails, keep the pending data and report the displayed reason through [GitHub Issues](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues), without credentials or private content.

**A recorded capture failure with no pending entry needs a different action.** Check the affected content and history, correct the cause, then save that content again. The resume button retries existing pending data; it cannot recreate content that was never captured. A past error can remain visible after unrelated saves succeed.

Recovery uses confirmed saves. If the source is lost before confirmation, recovery retains the previous confirmed version; an unconfirmed new item is not yet included.

## 日本語

元サイトが使える場合は、**ツール → Resilience → 投稿などの保存状況** を開きます。S3への保存を再開する操作であり、復旧先への復旧実行とは別です。

1. 対象の内容・未完了件数・失敗理由を確認します。履歴を読み取れない場合は、アクセスの問題を解消してから保存完了を判断します。
2. 保存先やアクセスの問題を解消します。その間、対象の記事は変更せず、未完了データを残してください。
3. **未完了の保存を再開**を一度押します。応答が途切れた場合は、履歴と未完了状態を確認してから再操作します。
4. 対象の内容と付随情報が確定履歴に入り、それぞれの未完了表示が解消したことを確認します。一つの編集でも、本文と付随情報が別々の履歴になることがあります。
5. 再開できない場合は未完了データを保持し、表示された理由を[GitHub Issues](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues)へ報告してください。認証情報や非公開の内容は含めません。

**取得失敗の記録があるのに未完了データがない場合は、操作が異なります。** 対象の内容と履歴を確認し、原因を解消してから、その内容をもう一度保存してください。再開ボタンは既存の未完了データを再送するもので、取得されなかった内容は再作成できません。別の保存が成功しても、過去のエラー記録が残る場合があります。

復旧には確定済みの保存を使います。確定前に元サイトを失った場合、更新は前の確定版まで、新規の内容は未収録となります。
