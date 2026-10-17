# Phase 3：バックアップ取得と外部保管

更新日：2026年10月18日。状態：着手、ローカル収集・外部保管設計。Phase 3は未完了。

## 使用先

利用者は既存の実験専用S3バケットの使用を指定した。バケット名、リージョン、専用プレフィックス、保存用・復旧用AWSプロファイルは回答待ち。実資格情報を文書や会話に貼らない。現時点でS3書込み、権限変更、課金リソース変更は行っていない。

## 実資産の取得

tools/capture-m1-assets.pyは専用Docker Composeプロジェクトowr-m1のみを対象にする。previewを停止し、既存プラグインの固定版PhpMySqlDumperを利用してDBを取得する。uploads、テーマ、pluginsとMU plugins、WordPress coreをtar.gzで取得する。構成にはCompose、イメージ固定情報、proxy定義、独自guardを含める。wp-config.php、runtime.env、DB接続パスワードは構成アーカイブに含めず、復旧側の別資格情報から再生成する。

DBダンプには模擬ユーザーのパスワードハッシュなどが含まれるため、アーカイブは.local/captures/以下に保管しGitから除外する。evidence/m1/e1/にはバイト数・ハッシュ・時刻・方法だけを記録する。アーカイブ内のリンク・デバイス・パス逸脱を拒否する。取得失敗もE1として記録し、previewの再開を試みる。

HTTP入口の停止とCron無効化は整合性確保の補助手段である。DB管理者や別のローカルプロセスの書込みまでは遮断しないため、現状はconsistency=uncoordinatedとする。厳密な整合点を確定したという主張は行わない。

既存プラグインのRecoveryCollector/Publisher全体の採用は未確定。今回は既存DBダンパーを再利用する収集アダプターを実装した。odbfs3-recovery-setを作ったように偽装せず、ローカルcapture.jsonは別のE1形式で記録する。上位RAMのrecovery_manifest必須資産への接続と全資産固定は残作業。実行環境はWordPressイメージを取得済みだが、DB/proxyの独立配布も今後確認する。

## S3の固定方法

外部保存時は専用prefix/新しいset_id/配下に一度だけアップロードする。PutObject応答の非null VersionIdを保存し、読み取り側はそのVersionIdを指定して取得する。HEADで最新版を見ただけでは固定しない。S3のETagをSHA-256と見なさず、独立取得した全バイトのサイズとSHA-256を照合する。

アップロード後の再取得で期待値と一致した資産だけをRAMに採用する。VersionIdとSHA-256を含むRAMを固定し、上位Recovery Set、Bootstrapの順で発行する。取得と発行途中で失敗したセットは公開済みとして扱わない。既存のpendingセットを上書きせず新IDを使用する。

VersioningがEnabledかを事前に読む。Suspendedや未有効なら作業を止め、バケット管理者に変更範囲を提示する。既存バケット全体の設定を無断で変えない。Lifecycleによる旧版削除、Object Lock、暗号化、KMS、既存bucket policyも確認対象。

AWS根拠：
- [固定版の取得](https://docs.aws.amazon.com/AmazonS3/latest/userguide/RetrievingObjectVersions.html)
- [GetObject APIとGetObjectVersion権限](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html)
- [Versioningとnull版](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html)

## 復旧権限の分離

tools/plan-m1-storage.pyで専用prefixに限定した権限案を生成する。AWS接続や適用は行わない。

保存主体は外部publisher用のPutObjectを持ち、DeleteObject/DeleteObjectVersionは明示的に拒否する。復旧主体はGetObjectVersionのみを許可し、最新GETと変更・削除を拒否する。既存プラグイン全体のS3 API呼出しに必要な権限とは別である。内部Pipelineを採用する場合はHEADや照合用GETの権限を別途検討する。

プロファイル名が違うだけでは分離と判定しない。STSで主体を確認し、同じロールの別セッションを区別しない。同一アカウントの管理者侵害に対する耐性も、別アカウントによる隔離とは異なる。M1でどの境界を実証するか証拠に明記する。

実測では復旧主体による固定版GET成功と、最新GET・PUT・DELETE拒否を確認する。否定試験は専用canaryに限り、既存資産に対して削除操作を試さない。実ポリシー、Permission Boundary、SCP、bucket policy、KMSの組合せまで確認するまでは権限分離を合格としない。

## 信頼情報の独立保管

同じバケットにRAMとそのハッシュを置くだけでは信頼の起点にならない。次を本番の書込み主体が変更できない別管理の保管先に置く。

- site_id、set_id、Recovery Setのbucket/key/VersionIdと正確なバイト列のSHA-256。
- Bootstrap配布物のバージョンとSHA-256、検査手順。
- 復旧用権限の取得先への参照、保管責任者、緊急連絡・認証回復手順。
- 固定・承認日時、失効・差替え時に新セットへ移る手順。

候補は別管理者のパスワードマネージャー内の非秘密メタデータ記録、別アカウントの保管先、オフライン媒体。実際の保管先と権限境界は未決。秘密鍵やパスワードをRAMへ埋め込まない。独立性・取得可能性が実測されるまで真正性はunverifiedを維持する。

## 費用とクラウド実行前の確認

実測した取得容量に保存世代数を掛けて月間保管量を算出する。S3 Standardの対象リージョンの保管単価、PUT/GET、外向き転送、必要ならKMS料金を加える。旧版と失敗したアップロードも容量に含める。無料枠は保証に含めない。毎日イメージ全体を複製せず、固定ソフトウェア資産の再利用を検討する。

[公式S3料金](https://aws.amazon.com/s3/pricing/)を参照し、保存先のリージョン確定後に試験費・定常費の見積もりを出す。まだ正確な金額を確定できない。既存仕様の「課金リソースの作成・変更は対象と概算費用を提示して承認を得る」に従い、具体案の確認後にクラウドへ進む。

## 残作業

バケット設定の読取り、費用確定、収集アダプターと既存manifest契約の確定、全実行環境資産の確保、固定版アップロード、独立した復旧主体でのGETとハッシュ照合、権限否定試験、RAM/セット発行、独立Bootstrapの取得試験を実施する。E2はこれらの実測後に記録する。ローカル収集のみでPhase 3完了、AC02/AC03合格とは判定しない。
## 今回のローカル実測

CAP-M1-20261017T213910-d65b1396を取得。資産7項目、合計897,256,640 bytes（既存WordPressイメージを含む）。HTTP入口停止から再開まで約54秒。メディア5ファイルはPhase 1の全ハッシュと一致し、サイト再開後のHTTP14項目も合格した。メタデータ28試験と権限案5試験、計33試験に合格。

再検査：

    python3 tools/verify-m1-capture.py CAP-M1-20261017T213910-d65b1396

証拠はevidence/m1/e1/CAP-M1-20261017T213910-d65b1396.jsonとevidence/m1/phase3/local-validation.json。これらは外部S3からの取得を示すE2ではない。
## 利用者指定の保存先

利用者指定：bucket=owr-example-bucket、prefix=wordpress-test/。
設定記録はexamples/m1/storage-target.json。リージョンと保存・復旧主体は未確定。

WSLではAWS CLIがPATHに存在せず、AWS設定のプロファイル名はdefaultのみ確認できた。秘密値は表示していない。defaultの用途が未確認のため、AWSへの認証・バケット読取り・書込みは実施していない。保存用として利用可能か確認し、復旧用は別主体の設定を行う。名前の異なるプロファイルを作るだけでは権限分離の証明にならない。
## 2026年10月18日：defaultの接続確認

東京リージョンap-northeast-1、保存用defaultの利用をユーザーが承認した。
tools/preflight-m1-s3.phpで既存AWS SDKと明示的なdefaultプロファイルを用いてSTS GetCallerIdentityを実行したところ、HTTP 403 / InvalidClientTokenIdとなった。

認証主体を確認できないため、バケットの読取り・書込み・設定変更には進んでいない。証拠はevidence/m1/phase3/aws-preflight-20261017T215055.json。defaultの認証設定を利用者側で更新した後に同じ読取り検査を再実行する。原因が失効・削除・不正なセッショントークンのどれかは、この応答のみでは特定できない。秘密値を会話やログへ出して調査しない。

preflightは安全側に、認証主体のアカウントをExpectedBucketOwnerとして指定する。別アカウント所有のバケットを使う場合は、所有アカウントを確認してからその期待値を変更する。
## 認証方針の訂正：IAMロール方式を採用

2026年10月18日、利用者指示により古いdefault長期キーの更新方針を撤回した。これより前のdefault更新案は履歴であり、今後の手順として使用しない。既存プラグインのsrc/Aws/S3ClientFactory.phpとdocs/project-definition.mdに従い、IAM Role / Instance ProfileとAWS SDK標準Credential Provider Chainによる一時認証情報を採用する。利用者は既存のEC2実験環境があると回答した。対象インスタンスと接続経路は未確認。

preflight-m1-s3.phpのini(default)固定を撤去した。標準チェーンの取得結果を検査し、セッショントークンと有効期限（残り60秒超）がない資格情報を署名前に拒否する。STSでassumed-role主体を確認してからバケットの読取りへ進む。既存プラグインは変更せず、この実験の入口で長期キーを拒否する。標準チェーン自体は長期キーも採用し得るため、チェーン採用だけで短期認証を保証しない。

WSLの古いcredentialsファイルは変更・削除しない。EC2では対象ロールの取得を妨げる古い環境変数や共有資格情報がない実行環境を使う。EC2ロール資格情報をWSLへコピーする運用はしない。保存主体と独立復旧主体には別ロールを用いる。現在のコードはassumed-roleを確認するだけであり、両ロールの分離は別途実測する。

tests/test-temporary-role-auth.php：8項目合格。長期キー、有効期限なし、失効、残存時間不足、IAMユーザー、root主体の拒否と有効な一時認証・ロール主体を検査。AWSへ通信しない単体試験であり、EC2の実接続成功を示すものではない。
## communityでの読取り確認

2026年10月18日：利用者指定のssh communityで接続。EC2 i-0123456789abcdef0、IAMロールExampleSharedRole、アカウント123456789012のSTS assumed-roleを確認した。子プロセスでAWS環境変数を除外し、共有config/credentialsを/dev/nullに指定して実行した。古いWSLのdefaultキーは使用していない。

ルートボリュームは97G中94G使用、空き3.7G、使用率97%。inode使用率16%。追加ファイル配置、削除、インストール、ボリューム変更はしていない。ローカル資産約897 MBの一括複製は避ける。アップロード時は容量を追加消費しないストリーミング方式も検討するが、実装・実測は未実施。ボリューム拡張は対象と費用を確認して別途判断する。

バケット設定6種類の読取りは全てAccessDenied。オブジェクトのPUT/GET権限は未試験。ExpectedBucketOwnerには実行主体のアカウントを指定したため、所有アカウントが異なる場合も失敗する。拒否理由がIAM、bucket policy、所有者不一致、その他境界のどれかは未確定。

examples/m1/bucket-inspection-policy.jsonに当該バケットだけを対象とする設定閲覧権限案を作成した。未適用。管理者が所有アカウントと拒否要因を確認し、必要なら実験用主体へ適用後に再検査する。このポリシーにはオブジェクトの読取り・書込み・削除・設定変更権限を含めない。

証拠：evidence/m1/phase3/owr-writer-preflight.json。IAMロールの実認証は確認できたが、外部資産のE2検証や復旧用ロール分離は未完了。
## 新旧バケット照合と修正手順

所有アカウント123456789012を明示したHeadBucketが、新owr-example-bucket・旧owr-legacy-example-bucketの両方で成功。両方とも東京リージョン。所有者不一致の疑いはこの検査で解消した。

両バケットのGetBucketVersioningは「no identity-based policy allows s3:GetBucketVersioning」で拒否された。既存製品のdocs/aws-recovery-set-verification-2026-10-17.mdにも同じ制約が明記され、従来の成功は転送・復元の検証であり、Versioning設定・固定版取得の認定ではなかった。今回の新規設定だけの不整合とは認められない。

修正対象は、今回のバケットに対する設定閲覧権限の追加。管理者のAWSコンソールで IAM → ロール → ExampleSharedRole → 許可を追加 → インラインポリシーを作成 → JSON に examples/m1/bucket-inspection-policy.json を指定し、例として OwrM1BucketInspection の名前で追加する。既存ポリシーを置換せず、既存バケット向け権限を広げない。

このSSH主体はIAMのポリシー一覧取得も拒否されており、管理者として設定を検査・編集できる接続は未提供。現在は権限案を作成した状態で、適用は未実施。管理者側で適用後に同じ読取り検査を再実行する。もし追加Allow後も拒否されれば、明示DenyやPermission Boundaryなどを管理者側で確認する。Versioning自体の有効化は、現状を取得できてから別途判断する。

実測：evidence/m1/phase3/bucket-comparison.json。
## 閲覧権限追加後の確認とVersioning変更案

2026年10月18日07:06 JST頃、設定閲覧が成功した。東京リージョン、SSE-S3（AES256）、パブリックアクセスブロック全4項目trueを確認。GetBucketVersioningは空オブジェクトで、Versioning未有効。ObjectLockConfigurationNotFoundErrorとNoSuchLifecycleConfigurationはそれぞれ未設定を示す（取得権限拒否ではない）。

次の変更対象：owr-example-bucketのVersioningをEnabledにする。バケット全体の設定でありwordpress-test/だけに限定できない。新規書込みには固定VersionIdが付与されるが、既存オブジェクトが遡及的に非null版へ変わるわけではない。未有効状態には戻せず、後からSuspendedにできる。旧版は保管容量として課金される。Object Lock、Lifecycle、公開設定、既存オブジェクトには変更を加えない。

管理画面手順：S3 → owr-example-bucket → プロパティ → バケットのバージョニング → 編集 → 有効にする → 変更を保存。
初回有効化後、AWS推奨に従い書込み前に15分待つ。有効化の実行と確認はまだ行っていない。
根拠：https://docs.aws.amazon.com/AmazonS3/latest/userguide/manage-versioning-examples.html

費用根拠：AWS公開価格API（publicationDate 2026-10-15T17:35:40Z）
https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/ap-northeast-1/index.json
東京S3 Standardの最初の50 TBは0.025 USD/GB-month、PUT等0.0047 USD/1000回、GET等0.0037 USD/10000回。
取得済み897,256,640 bytesは約0.836 GiB。1セットの保管は約0.021 USD/月、余裕を見て1 GBとして0.025 USD/月（仮に1 USD=150円なら約3.75円/月）。これは保管分だけであり、リクエスト、外向き転送、税、追加の実行環境資産、既存バケットの他データ、旧版の累積は別。為替150円は比較用仮定で実勢値ではない。自動反復アップロードは行わず、Phase 3の実書込み回数・容量・転送費は実行前に別途限定する。

既存仕様の課金変更確認に従い、現時点ではVersioning変更もS3アップロードも未実施。復旧用別ロールの作成と固定版GETの権限分離も残作業である。
## Versioning有効化確認と復旧候補dm

利用者がVersioningを有効化し、communityからStatus=Enabledを実測した。証拠はevidence/m1/phase3/versioning-enabled.json。初回有効化の正確な時刻が不明なため、最初の書込みは確認後少なくとも15分を空ける。まだ書込みは行っていない。

利用者指定のssh dmを読取り調査。空き59G、使用率48%。IMDSv2でi-0fedcba9876543210とExampleSharedRoleを確認した。保存元と同じロール名のため、復旧主体の分離は未成立。AWS CLIはawscliモジュール欠落で起動せず、STSでの主体確認も未実施。evidence/m1/phase3/owr-reader-preflight.jsonに記録。

初心者向け手順をdocs/guides/s3-iam-setup.mdへ追加し、READMEから案内した。復旧用EC2信頼ポリシーと固定版GET用権限例を作成したが、適用は未実施。既存dmの用途・必要権限を確認してから別ロールへ切り替える必要がある。CLIは既存環境を上書きしない実験専用の実行環境で補う方針。

既存secure-s3-storage-for-wordpressの説明改善候補：ロールと長期キーの違い、EC2での設定とWSLの違い、バケット操作と設定閲覧の区別、最小権限例、接続エラーの切り分け、料金と保持、初回の操作順。今回は本プロジェクトの手順を先に整備し、既存製品リポジトリは変更していない。
## 環境整備と並行した版固定転送の実装

利用者の指示により、独立ロールの準備を開発停止条件にしない。src/VersionedAssetStore.php、tools/versioned-s3-transfer.php、tools/bind-m1-observations.pyを追加した。新しいRAMへ明示的に結び付ける一方、権限分離・真正性はunverifiedを保持する。開発手順はdocs/guides/versioned-transfer-development.md。

Python41試験とPHP転送14試験に合格。これらはオフラインであり、実S3のE2証拠とは別。保存側との同一ロールでも機能試験は実施できるが、その場合は独立した権限による取得を合格と記録しない。
## 実S3検証の完了（2026年10月18日）

RS-M1-LIVE-20261018-001をowr-example-bucket/wordpress-test/へ発行した。8必須資産、Bootstrap、RAM、Recovery Setの11オブジェクトを条件付きPUTで新規保存し、別EC2のdmからVersion IDを明示して全て取得・サイズ・SHA-256照合した。先行する24バイトのcanaryも成功した。詳細はevidence/m1/e2/RS-M1-LIVE-20261018-001.jsonと同名-anchor.jsonに記録する。

runtimeは3固定Dockerイメージをgzipにまとめた454,857,903バイトで、当初のWordPress単体tarとは別資産である。派生梱包のE1記録をE1-PACKAGE-RS-M1-LIVE-20261018-001.jsonに追加した。元の収集記録は改変していない。

anchor.jsonは別ホストdmの専用ディレクトリに配置した。ただし同一管理者・同一AWSアカウント・共通ExampleSharedRoleであり、真正性や権限境界の独立性は証明していない。RAMのcredential_ref=recovery-readerは論理参照名で、今回の実体は共有ロールである。E2時点のrestore=untestedは当時の観測を保ち、後続E3で復旧結果を記録する。