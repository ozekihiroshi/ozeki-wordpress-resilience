# wp.ceri.link 正式保管への接続手順

更新：2026年10月18日。バケット名は利用者確認済み。**AWS設定と専用canary試験は確認済み。実バックアップの正式保存・署名・S3からの再復元は未実施。**

## 1. 専用バケットを作る

AWSコンソール右上のアカウントが `121426368082` であることを確認し、S3の「バケットを作成」を開く。

- 種類：汎用、リージョン：東京（ap-northeast-1）。
- 名前：`ceri-link-resilience-prod-121426368082`。
- オブジェクト所有者：ACL無効（バケット所有者の強制）。
- パブリックアクセスをすべてブロック：すべて有効。
- バージョニング：有効。
- 暗号化：SSE-S3。
- 詳細設定のObject Lock：有効。Object Lockを有効にした後は無効にできない点を確認して作成する。

作成後「プロパティ」→「オブジェクトロック」→「編集」。デフォルト保持を有効にし、**ガバナンス、35日**にする。Object Lockを有効にしただけではデフォルト保持は設定されない。削除Lifecycleは追加しない。既存M1・lock-labバケットは変更しない。

[設定値JSON](../../examples/production/object-lock-configuration.json)は確認用であり、コンソールでは上記の項目へ入力する。

## 2. 対象バケットだけの権限を追加する

初回パイロットはcommunityの既存 `my-ssm-role` とdmの `OwrM1RecoveryReader` を使い、対象バケット専用のインラインポリシーを追加する。既存ポリシーを置換せず、SSM・KMS・他業務の設定は維持する。保存側専用ロールへの移行と間接的な権限取得経路の点検は別途必要。

1. IAM → ロール → my-ssm-role → 許可を追加 → インラインポリシー → JSON。[writer-policy.json](../../examples/production/writer-policy.json)を貼り、名前を `OwrProductionSiteWriter` とする。
2. IAM → ロール → OwrM1RecoveryReader で同様に[reader-policy.json](../../examples/production/reader-policy.json)を追加。名前を `OwrProductionSiteReader` とする。
3. 新バケット → アクセス許可 → バケットポリシーへ[bucket-policy.json](../../examples/production/bucket-policy.json)を貼る。ロールARNはこのアカウントの既存2ロールを指定済み。設定作業は保管管理者として行う。

保存側は対象サイト配下へPutObject、復旧側は固定版GetObjectVersionと保持状態読取り。双方に削除・保持変更・bypassを明示拒否する。バケット側でも両ロールの保護変更と復旧側書込みを拒否する。これはアカウント管理者の侵害まで防ぐものではない。

## 3. 設定後の実行順序

1. 所有者、リージョン、Versioning、35日デフォルト保持、公開遮断、暗号化、bucket policy、Lifecycleを読み取り確認。
2. 専用canaryでデフォルト保持、短い個別指定の拒否、削除・保持短縮・bypass・復旧側書込みの拒否と固定版再取得を確認。既存実データで削除試験しない。
3. 今回の取得物をハッシュ再照合し、一意の `sites/wp-ceri-link/sets/<set-id>/` に保存。送信結果不明時は盲目的に再送しない。
4. dmで各固定Version IDを再取得し、サイズ・SHA-256・保持モード・保存時刻から35日以上の期限を検証する。保存受付だけでは保護確認済みにしない。
5. 必須資産に加えRAM、Recovery Set、Bootstrap、検査記録を保存・固定する。独立側の保持確認を全参照へ結び、最短保持期限をセット利用期限の上限とする。
6. 手元PCで検査範囲と整合性をレビューし、承認・期限・世代・anchorハッシュへ署名。新サイト専用の独立ピンを作り、既存M1ピンを上書きしない。鍵は既存PC鍵を利用可能だが、秘密鍵はサーバー・S3へ渡さない。
7. S3固定版から署名ゲート経由で隔離復元し、今回のページ・メディア検査を再実施する。

今回のライブ取得はDBとファイルの同時点整合性が未確定なので、まず保護された検証候補として扱う。正式な運用復旧点として承認するには、更新停止可能時間帯または整合性検査の受入条件を決める。隔離試験用署名を正式承認へ読み替えない。日次自動取得はまだ開始しない。

## 実装状況と次の作業

VersionedAssetStoreに35日保持モードを追加した。設定 `retention_days: 35` の場合、PUT前にデフォルト保持を検査し、固定版GETの保持情報が欠落・短期・期限切れならファイルを公開しない。既存M1モードは維持。署名の対象に保持証拠を組み込む上位パイプライン、初回取得物を正式RAM/Bootstrapへ対応付ける処理、ストリーム送信の本番用統合は残っている。既存M1アップロードスクリプトは保存元へ一時ファイルを転送するため、そのまま本番に流用しない。

保持検証はAWS SDKが返す固定版のObjectLockMode、ObjectLockRetainUntilDate、LastModifiedを利用する。復旧側にはGetObjectRetentionも必要。保管後の独立取得で保持を再検査し、事前チェックからPUTまでの設定変更も成功扱いにしない。

根拠：[AWS Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)、[設定手順](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-configure.html)、[保持情報の取得](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html)。


## 2026年10月18日 実機確認

東京、Versioning有効、Governanceデフォルト35日、SSE-S3、公開アクセス全面遮断、削除Lifecycleなしをcommunityとdmから確認。バケットポリシーは用意した内容と一致した。

communityから専用canaryへ99bytesの保存に成功し、Version IDを取得した。ただしdmのOwrM1RecoveryReaderによる同じ版のGetObjectRetentionとGetObjectVersionは、identity-based policyのAllowがないというAccessDeniedで停止した。バケット設定の読取り権限とオブジェクト版の読取り権限は別である。reader-policy.jsonのReadFixedVersionsAndRetentionを含む全文が適用されているか確認が必要。

固定版の保持・ハッシュと削除拒否の試験は未完了。実バックアップは未送信。canaryは `sites/wp-ceri-link/canaries/20261018-a67423846495/protected.txt` に残し、権限修正後はこの版を使って再開する。削除・保持短縮はまだ試行していない。


## 同日追記：権限修正後の検証成功

復旧ロール修正後、保存済み99bytesのcanaryを再利用して検証を完了した。[公開結果](../../evidence-public/production-storage-canary.json)。

- dmでVersion IDを指定した取得・SHA-256照合、保持情報の読取りに成功。
- 保持はGOVERNANCE、期限は2026年11月22日17:59:45.547（日本時間）。
- community・dm双方から通常削除、版削除、bypass付き版削除、保持短縮がAccessDenied。
- communityの1日保持指定PUTと、dmのPUTがAccessDenied。
- 試験後も同じ版の内容・保持期限が一致。

S3応答のLastModifiedは2026-10-18T08:59:46Z、RetainUntilDateは2026-11-22T08:59:45.547Z。単純比較では35日より0.453秒短くなるため、異なる時刻精度を扱う上限1秒未満の許容差を実装した。1秒以上短い保持は拒否する。実際の保持期限そのものは丸めず記録し、セットの最短期限・承認期限の判定で延長して扱わない。転送テスト21項目に境界試験を含めて合格した。

削除拒否はIAM・バケットポリシーを合わせた権限の結果であり、Object Lock単独の強制力を切り分けた実験ではない。99bytesの試験版は保持したまま残す。実バックアップは未送信であり、次は一時ファイルを保存元へ作らない送信経路と正式RAM/Bootstrapを統合する。


## 初回取得済みデータの保存・署名

[実施記録](protected-candidate-publication.md)のとおり、正式バケットへの8資産と台帳・署名等12オブジェクトの保存・固定版独立取得・署名検証まで完了した。保管内容検証済み候補であり、同時点整合性・無感染・本セットからの完全復元の受入は未完了。上記の未送信は実施前の記録として残す。
