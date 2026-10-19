# 保存元侵害を想定した削除耐性の検証

実施日：2026年10月18日。**通常削除・固定版削除の直接試験は合格。保存元侵害時の総合的な破壊耐性は未認定。**

[公開用結果](../../evidence-public/writer-deletion-resilience.json)。AWS設定は変更していない。

## 試験対象と実測

communityの現在のEC2資格情報が保存側my-ssm-roleであることとアカウントをSTSで照合した。長期キー・ローカルAWS設定は使わず、侵害された保存元がこのロールのAPI操作を行える状況を模擬した。ホストへマルウェアを投入した試験ではない。

新規UUID付き `wordpress-test/security-probes/writer-20261018-*/` 内に109bytesの試験用テキスト2個を保存し、それぞれ異なる削除操作を試した。両方とも事前にdmのOwrM1RecoveryReaderから固定Version IDで取得・ハッシュ照合済み。

| 操作 | 保存側の結果 | 削除試行後のdmによる確認 |
| --- | --- | --- |
| Version IDなしのDeleteObject | AccessDenied | 元の固定版GET成功・SHA-256一致 |
| 固定Version ID指定のDeleteObject | AccessDenied | 対象の固定版GET成功・SHA-256一致 |

試験用ファイルは残した。既存バックアップのキーを削除要求に使っていない。固定版のサイズは109bytesで、APIが返したContentLength・VersionIdも原本に記録した。今回の新規キーに対する結果を、条件の異なる全キー・全主体へ一般化しない。

## 保持設定と確認できない部分

- VersioningはEnabled。
- LifecycleはNoSuchLifecycleConfigurationで、ルールなし。
- Object LockはObjectLockConfigurationNotFoundErrorで、未設定。
- 暗号化設定の読取りは成功。試験用オブジェクトの暗号化はAES256。
- Bucket policyの読取りはAccessDenied。
- 保存側ロールのget-role、list-attached-role-policies、list-role-policiesもAccessDenied。

読取りのAccessDeniedは設定変更権限がないことの証明ではない。削除拒否が明示Deny・Allow欠如・bucket policy・その他の境界のどれによるかも未確定である。Versioning停止、Lifecycle追加、bucket policy変更、IAM権限追加、他ロール取得やdm制御などの経路は評価未完了。既存バケットへこれらの変更要求を出して試験しない。

## 次のAWSコンソール確認（変更せず内容を確認）

利用者が以前選択したAWSコンソール方式で、次の設定を確認する。EC2ロールへ管理権限を追加する必要はない。認証情報・パスワードは共有しない。

1. IAM → ロール → **my-ssm-role** →「許可」。アタッチされた管理ポリシーすべての有効なJSONと、インラインポリシーすべてのJSONを確認する。ポリシー名だけでは権限を判定できない。Permissions boundaryの有無と内容も確認する。
2. 同ロールの「信頼関係」を確認する。OwrM1RecoveryReaderの信頼関係も確認し、保存側からAssumeRoleできる経路がないか照合する。
3. S3 → 実験用バケット →「アクセス許可」→「バケットポリシー」のJSONを確認する。「管理」のLifecycle、「プロパティ」のVersioning・Object Lockも照合する。
4. 以下の権限とワイルドカード許可、条件、リソース範囲をレビューする。Organizations SCP等の制約がある場合は管理者から確認を得る。IAM policy simulatorの結果だけで資源ポリシー等を含む全経路の証明にしない。

| 確認する経路 | 主な権限の例 |
| --- | --- |
| 直接削除 | s3:DeleteObject、s3:DeleteObjectVersion |
| 保持・版管理の変更 | s3:PutLifecycleConfiguration、s3:PutBucketVersioning、s3:PutBucketObjectLockConfiguration |
| バケット側の保護変更 | s3:PutBucketPolicy、s3:DeleteBucketPolicy |
| ロック回避・保持変更 | s3:BypassGovernanceRetention、s3:PutObjectRetention、s3:PutObjectLegalHold |
| 自分・別主体への権限追加 | iam:PutRolePolicy、AttachRolePolicy、CreatePolicyVersion、SetDefaultPolicyVersion、UpdateAssumeRolePolicy、Permissions boundary変更、sts:AssumeRole |
| 別ホスト・管理環境の取得 | iam:PassRoleとEC2 profile関連権限、ssm:SendCommand/StartSession、EC2起動・制御関連権限 |

これは確認対象の例であり網羅的な有効権限解析ではない。証拠JSONは非公開の `.local/` に保管する。既存の `tools/export-recovery-iam-review.py` を使う管理者向け読取り経路もあるが、今回はユーザーのコンソール方式を継続する。

## Object Lock試験へ進む条件

今回、直接削除を拒否できているため、既存ロールへ重複するポリシーを盲目的に追加しない。権限レビュー後、保持期間中に固定版を残す必要を満たす構成を選ぶ。

既存共有バケットへの即時有効化は行わない。Object Lock有効化後は無効化やVersioning停止ができないため、最初は専用の実験バケットで短い固定保持期間を設定し、新規canaryに限定して試す。GovernanceとComplianceのどちらを使うか、解除できる管理主体・費用・保持期間を先に確定する。既存版が自動的に保護されたと扱わず、各Version IDの実際の保持状態を確認する。

試験では、保持中の固定版削除・保持短縮・Governance bypassの拒否と、dmの固定版取得を確認する。通常削除の成功だけでは固定版消失と判定しない。Object Lockがある場合も削除マーカーは作成可能だからである。検証用主体の削除Allow等も確認し、単なる権限不足をObject Lockの効果と取り違えない。

参考：[AWS Object Lock設定](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-configure.html)、[Object Lockの運用・制約](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html)、[削除マーカー](https://docs.aws.amazon.com/AmazonS3/latest/userguide/DeleteMarker.html)。Object Lockは暗号鍵喪失やAWSアカウント・管理端末全体の喪失を解決するものではない。

## 証拠と公開判定

非公開原本は `.local/writer-deletion-probe-20261018.json` と `.local/writer-iam-review-20261018.json`。前者には試験prefix、Version ID、API応答、前後のSHA-256を保持する。

CR01は「直接削除の部分試験は合格、総合条件は未達」とする。保存元が侵害されても必ずバックアップが残る、とはまだ説明しない。次に必要なのはIAM・bucket policyのレビューであり、既存バックアップへの破壊試験ではない。

## GetBucketPolicy追加後の確認

利用者が閲覧権限s3:GetBucketPolicyを追加した後、communityのmy-ssm-roleから再取得した。応答はAccessDeniedではなくNoSuchBucketPolicyで、このバケットにbucket policyが未設定であることを確認した。非公開原本は `.local/bucket-policy-review-20261018.json`。上記のbucket policy閲覧不能という状態はこの追加確認で解消した。

したがって、今回の削除拒否をbucket policyの明示Denyによるものとは説明できない。IAM側のAllow欠如・Deny、その他の制約を特定するため、次はmy-ssm-roleの全許可ポリシーとPermissions boundaryを確認する。bucket policy未設定だけで、削除可能または設定変更可能とは判定しない。IAMの閲覧権限は今回追加されておらず、そのレビューは引き続き未完了。

## 利用者提供のロールポリシー確認

利用者が示したmy-ssm-roleの一覧7件について、カスタム6件のJSONとAWS公式AmazonSSMManagedInstanceCore（既定v2）を照合した。APIで全ポリシーを取得できたという意味ではなく、画面・貼付JSONと公式文書に基づく確認である。MoodleのJSONは同じ内容が2回提示されており、異なる2ポリシーとは数えない。

- shared-role-functional-test-policy：実験バケットのwordpress-test/*へのPutObjectとGetObjectVersionだけ。
- ceri-link-resilience：実験バケットの設定閲覧。GetObjectVersionはbucket ARNのみなのでこのStatementからオブジェクト取得は許可されず、上記の別ポリシーが取得を許可する。
- SecureS3StorageTestPolicy：別のsecure storage試験バケットに限定された操作。
- ceri-demand-monitor-prod-121426368082：別のdemand-monitorバケットとそのプレフィックスに限定された操作。
- s3MoodleStorageTestPolicy：別のMoodle試験バケットとそのプレフィックスに限定された操作。
- my-kms：指定KMS鍵へのDecryptだけ。鍵削除・無効化・キーポリシー変更は許可しない。
- AmazonSSMManagedInstanceCore：SSMエージェント向け。S3削除・設定変更・IAM変更・sts:AssumeRole・ssm:SendCommand/StartSessionの許可はない。公式JSON：https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html

確認した7件には、実験バケットの削除・Versioning/Lifecycle/bucket policy変更、IAM権限追加を直接許可するActionはない。削除拒否の実測はこの内容と整合する。提示ポリシーには削除の明示Denyもなく、「削除のAllowがない」という状態と評価する。別バケットの削除許可を今回のバケットへ拡張して解釈しない。業務用の別バケット向けポリシーを削除しない。

Permissions boundaryの有無は未回答。これは権限を追加する仕組みではないため、未回答だから削除Allowがあると推測しない。ほかの資源ベースの許可や、ロール以外のホスト上の資格情報、他ホストのSSH経路は別途確認する。SSM管理ポリシーにResource=*のGetParameter/GetParametersが含まれるため、Parameter Storeに別の管理用認証情報が置かれていないかも管理者側で確認する。値や秘密情報を取得・表示する試験は行わない。

現在の保存側ロールについて直接操作の権限レビューは進んだが、ホスト侵害時の全経路の遮断、Object Lockによる保持、別管理主体の独立性を全面合格にはしない。


利用者からPermissions boundary未設定との回答を受領した。境界から権限は追加されず、先の直接操作レビューの結論は変わらない。次の段階は[専用Object Lock試験](object-lock-lab.md)。AWS設定・保持試験は準備段階であり、実施済みとは記録しない。
