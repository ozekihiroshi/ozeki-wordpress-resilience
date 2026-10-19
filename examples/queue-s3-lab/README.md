# 三資産S3往復試験の限定ポリシー

バケット: ceri-link-resilience-lock-lab-121426368082（東京）。今回の対象は sites/isolated-queue-lab/sets/ 配下のみ。旧 object-lock-probes/ の削除権限付き試験ポリシーは再利用しない。

1. AWSコンソール → IAM → ロール → my-ssm-role → 許可を追加 → インラインポリシーを作成 → JSON。writer-policy.json を貼り付け、名前 OwrQueueS3LabWriter で作成する。
2. ロール OwrM1RecoveryReader で reader-policy.json を同様に追加し、名前 OwrQueueS3LabReader で作成する。
3. EC2ロールの付替えや、既存ポリシーの削除・置換は行わない。追加後に試験を再開する。

保存時にGOVERNANCE保持を明示する。35日以上を確保するため要求時刻から35日と10分を指定する。保存後に期限を読み戻す。保持中の試験データは残す。自動削除・bypassは行わない。保存側のPutObjectRetentionは、既定保持のない試験バケットへ保持付きPUTを行うために必要。

試験データは専用WordPressの架空データで、本番データと本番署名鍵は使用しない。署名鍵は手元WSLの試験専用ディレクトリに作成し、community/dm/復元コンテナへ渡さない。試験後も信頼情報と取得先を手元に残す。

試験が終了し必要な読戻しが済んだ後、今回追加した2ポリシーだけを取り外す。保持期限経過は自動削除を意味しない。後日のデータ整理は別途行う。

参考: https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html
