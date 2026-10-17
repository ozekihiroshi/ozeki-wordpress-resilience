# はじめてのS3・IAM設定

このプロジェクトは開発中です。この手順はMilestone 1の実験環境を準備するためのものです。手順を終えただけで復旧成功になるわけではありません。実資産の固定版取得と復元試験まで確認します。

## 1. 何を準備するのか

S3はバックアップの保管先です。バケットは保管領域、プレフィックスはその中で名前を区切る部分です。「フォルダ」は画面上の表示であり、今回の対象はwordpress-test/から始まる名前のオブジェクトです。

IAMロールはサーバーへ渡す権限です。EC2にロールを付けると、AWS SDKが一時的な認証情報を取得します。WordPressの画面や設定ファイルに長期アクセスキーを入力しません。

Versioningは同じ名前のファイルの版を区別する機能です。復旧時は「最新」ではなく記録されたVersion IDを指定します。Versioningだけでは、削除権限を持つ攻撃者から旧版を守れません。

| 項目 | この実験で使う値 |
| --- | --- |
| AWSリージョン | 東京 ap-northeast-1 |
| バケット | owr-example-bucket |
| プレフィックス | wordpress-test/ |
| EC2への接続 | WSLから ssh owr-writer |
| 保存側の既存IAMロール | ExampleSharedRole |
| 復旧側のIAMロール | 未構成。保存側と別に用意する |
| AWSアカウント | 123456789012 |
| EC2ディスク | 確認時97%使用。大きな資産を追加コピーしない |

ap-northeast-1aはAvailability Zone名です。リージョン欄には末尾のaを付けません。

## 2. AWS管理画面とサーバーの役割

AWS管理者はブラウザーからS3とIAMを設定します。サーバーは設定済みのロールでバックアップを保存します。サーバーへIAM全体の管理権限を与える必要はありません。

AWS管理画面にサインインしただけでは、ローカルWSLやEC2のCLIが認証されるわけではありません。EC2ではインスタンスに割り当てたIAMロールを使います。WSLの古いdefaultアクセスキーは今回使いません。

以下の操作は実験専用の対象を確認して行います。別の本番バケットや既存ポリシーを書き換えないでください。既存EC2のIAMロールを置換すると、他の開発作業に影響する場合があります。今回の既存ロールは維持し、必要な範囲の許可を追加します。

## 3. S3を設定する

AWS管理画面で S3 → 汎用バケット → owr-example-bucket を開きます。

1. リージョンが東京であることを確認します。
2. アクセス許可 → パブリックアクセスをブロックで、4項目を有効にします。バックアップを公開する必要はありません。
3. プロパティ → デフォルトの暗号化を確認します。今回の実験はSSE-S3（Amazon S3管理キー、API表示AES256）を使用します。SSE-KMSを使う場合は別途KMSの権限と費用の設計が必要です。
4. プロパティ → バケットのバージョニング → 編集 → 有効にする → 保存します。
5. 初回有効化後は15分待ってから書き込みます。

Versioningはバケット全体に適用されます。wordpress-test/だけに有効化する設定ではありません。一度有効にすると未有効の状態には戻せず、一時停止ができます。既存オブジェクトに非nullのVersion IDが遡って付くわけではありません。これから保存する新しい実験セットで版を記録します。

LifecycleとObject Lockは別の設定です。この段階で自動削除ルールを追加しません。Object Lockも未設定なので、改変・削除への耐性を確立したとは扱いません。

参考：[AWSのVersioning有効化手順](https://docs.aws.amazon.com/AmazonS3/latest/userguide/manage-versioning-examples.html)

## 4. IAMの「設定閲覧」と「データ操作」を分ける

S3へファイルを保存できても、Versioningや暗号化の設定を読めるとは限りません。旧バックアップ製品の実験も、この状態でした。

AWS管理画面で IAM → ロール → ExampleSharedRole → 許可を追加 → インラインポリシーを作成 → JSON を開きます。

まず[設定閲覧用JSON](../../examples/m1/bucket-inspection-policy.json)を貼り付け、例えばOwrM1BucketInspectionという名前で追加します。このJSONは当該バケットの設定を読む許可だけです。既存ポリシーの内容を置き換えません。

データ操作のひな形は[外部保存用](../../examples/m1/writer-policy.json)と[復旧専用](../../examples/m1/recovery-reader-policy.json)です。両方を同じロールに付けてはいけません。

- 外部保存用：今回のプレフィックスへのPutObjectを許可し、オブジェクトと版の削除を拒否します。
- 復旧専用：今回のプレフィックスのGetObjectVersionを許可し、書き込み・削除・最新版だけを指定するGetObjectを拒否します。
- この保存用ひな形は新プロジェクトの外部publisher用です。既存プラグインの接続試験、HEAD/GET検証、マルチパート転送などに必要な権限をすべて含むわけではありません。既存製品にそのまま流用しません。

既存ロールに他の許可が付いていれば、Allowは合算されます。このJSONを追加しただけで「最小権限になった」とは判定しません。明示Denyは他の許可より優先され、同じプレフィックスで動く他の処理にも影響します。適用対象と既存用途を管理者が確認します。

復旧用ロールは独立した環境に割り当て、保存元communityからそのロールを取得できるようにはしません。信頼ポリシーは接続元を決めてから作成します。Principalをワイルドカードにした汎用例は使用しません。

## 5. 接続と設定を確認する

WSLで次を実行してEC2へ接続します。

    ssh owr-writer

EC2のロールが使われているかを確認します。以前のキーが環境変数や共有設定に残っている場合に混同しないよう、今回の確認コマンドではそれらを子プロセス内で無効にします。ファイルは削除しません。

    env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_PROFILE \
      -u AWS_ROLE_ARN -u AWS_WEB_IDENTITY_TOKEN_FILE -u AWS_CONTAINER_CREDENTIALS_RELATIVE_URI \
      -u AWS_CONTAINER_CREDENTIALS_FULL_URI \
      AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
      AWS_DEFAULT_REGION=ap-northeast-1 AWS_PAGER= \
      aws sts get-caller-identity

Arnにassumed-role/ExampleSharedRole/が含まれることを確認します。アクセスキーやセッショントークンを表示・コピーする操作は不要です。以降のAWSコマンドも同じenv指定を付けて実行します。

    aws s3api get-bucket-versioning \
      --bucket owr-example-bucket \
      --expected-bucket-owner 123456789012 \
      --region ap-northeast-1

期待する結果は {"Status":"Enabled"} です。{} は未有効、Suspendedは一時停止を意味します。AccessDeniedは状態が無効という意味ではなく、状態を取得できなかったという意味です。

権限追加後は、保存成功だけで終わらず、別の復旧主体で固定Version IDの取得・SHA-256一致・書込み拒否を実測します。まだこの試験は未完了です。

## 6. 保存から復旧までの流れ

1. ローカルで実験資産を収集し、サイズとSHA-256を記録します。
2. VersioningがEnabledであることと、初回設定後の待機時間を確認します。
3. 新しいセットIDのキーへ保存し、S3が返すVersion IDを記録します。既存セットを上書きしません。
4. 復旧用の別主体から、そのVersion IDを明示して全バイトを読み、サイズとSHA-256を確認します。
5. 確認済み資産をRAMとRecovery Setに固定します。未取得の資産を完了扱いにしません。
6. Recovery Setの取得先・Version ID・SHA-256を、保存元の権限で書き換えられない別管理の保管先へ置きます。
7. 元サイトへアクセスできない状態で独立復旧試験を実施します。

独立保管先には復旧用の権限取得手順も残します。RAMとそのハッシュを同じバケットに置くだけでは独立した信頼の起点になりません。まだ運用が確定していないため、真正性はunverifiedです。

## 7. 費用とよくあるつまずき

東京S3 Standardは確認時0.025 USD/GB-month（最初の50 TB）。取得済み約0.9 GBの1セットは保管分が月約0.025 USD以内の目安です。旧版・追加資産・リクエスト・外向き転送・税は別です。毎日フルコピーすれば保存量は積み上がります。固定ソフトウェアを使い回す方式や保持期間は検証後に設計します。

[公式料金](https://aws.amazon.com/s3/pricing/)。
[今回取得した東京リージョン単価の原典](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/ap-northeast-1/index.json)。

| 症状 | 確認すること |
| --- | --- |
| InvalidClientTokenId | 古いアクセスキーが選ばれていないか。今回の解決はキー再発行ではなくEC2ロールの利用 |
| 設定閲覧だけAccessDenied | データ操作とは別の設定閲覧権限があるか |
| 権限追加後もAccessDenied | 対象バケット・プレフィックス・ロール、明示Deny、境界、SCP、bucket policy |
| Version IDがnull | Versioningと書込み時点を確認。既存のnull版を固定済みと扱わない |
| HeadBucketが所有者指定で失敗 | アカウント、権限、バケット名を確認 |
| 容量不足 | 今回communityは空き約3.7 GB。資産一式の複製や不要データの一括削除をしない |

## 現在地

2026年10月18日：Versioningを有効化し、実資産・Bootstrap・RAM・Recovery SetをS3へ保存、別EC2のdmから固定Version IDで取得しハッシュ一致を確認しました。dmにも取得情報anchor.jsonを保管しました。IAMロールは共有のままで、権限分離は未達です。復元結果は最終評価を参照してください。

詳細は[Phase 3実測記録](../m1/06-backup-and-storage.md)と[Bootstrap手順](../m1/05-recovery-bootstrap.md)を参照してください。
## 8. dmに復旧用ロールを準備する

実測で、communityとdmには同名のExampleSharedRoleが割り当てられていました。サーバーを分けただけでは権限の分離にはなりません。dmの空き容量は約59 GBです。

管理者側で以下を準備します。

1. IAM → ロール → ロールを作成 → 信頼されたエンティティはAWSのサービス、ユースケースはEC2を選びます。
2. 復旧用ロールの例として OwrM1RecoveryReader という名前を付けます。
3. [復旧専用ポリシー](../../examples/m1/recovery-reader-policy.json)をインラインポリシーとして追加します。許可範囲はowr-example-bucket/wordpress-test/*の固定版取得だけです。
4. 信頼関係は[EC2用信頼ポリシー例](../../examples/m1/recovery-ec2-trust-policy.json)に対応します。communityのロールをAssumeRole元として許可しません。
5. **dmが現在必要としている権限を先に管理者が確認します。** SSMなどの運用を継続するために必要な許可があれば、新しいロールにも必要最小限を引き継ぎます。既存のS3書込み権限や管理権限をそのままコピーしないでください。
6. EC2 → インスタンス → i-0fedcba9876543210 → アクション → セキュリティ → IAMロールを変更、で新しいロールを割り当てます。既存用途への影響を確認できない場合はここで止め、別の復旧専用実行環境を使います。
7. 既存ExampleSharedRole自体の権限を削除・変更しません。communityが引き続き使用します。
8. dmでSTSのArnが新しいロールへ変わったことを確認します。固定版GET成功と書込み拒否は、後続の専用試験で検証します。

dmの既存/usr/local/bin/awsはModuleNotFoundErrorで利用できませんでした。既存環境を上書きせず、公式署名を検証したAWS CLI 2.38.1を/home/ubuntu/.local/owr-m1-runtime/bin/awsへ導入し、この絶対パスで取得を検証しました。再現用コードはtools/prepare-owr-reader-runtime.pyです。
## 今回のみ：同一ロールで機能試験する場合

利用者は今回、ロール分離を未達として明示したうえで同一ロールでの機能試験を選択した。
その場合は[共有ロール機能試験用ポリシー](../../examples/m1/shared-role-functional-test-policy.json)を使用する。対象はowr-example-bucket/wordpress-test/*のPutObjectとGetObjectVersionだけ。復旧専用reader-policyにはPutObjectの明示Denyがあるので、共有ロールには追加しない。

初回実試験では、設定閲覧は成功したがPutObjectがAccessDeniedだった。設定閲覧とデータ操作が別権限であることを実測した。権限追加後は別の検査キーで再試験し、旧エラーを上書きして消さない。

同じロールで復元できても、侵害された保存主体と復旧主体の権限分離を実証したことにはならない。本番向けの推奨構成は別ロール・別の権限取得経路である。
### ポリシー追加後も保存できない場合

今回、AWSは「no identity-based policy allows the s3:PutObject action」と返しました。IAMのポリシー一覧に作成しただけでなく、IAM → ロール → ExampleSharedRole → 許可に、そのポリシーが追加されているか確認します。ResourceはバケットARN単体ではなく `arn:aws:s3:::owr-example-bucket/wordpress-test/*` です。実際のロールはSTSで確認します。設定追加後、canary-06.txtの保存・dmからの固定版取得が成功しました。失敗記録も残しています。