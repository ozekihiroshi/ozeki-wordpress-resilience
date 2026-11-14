# 添付一式の保全 / Attachment bundle preservation

この変更はmainの未配布ソース修正です。本番、提出済みrc.16のZIP・タグは更新していません。新しい公開用ZIPはまだ作成していません。

## 修正の理由

communityの初回保存後に登録されたPDF2件と生成プレビュー8件は、履歴41に閲覧条件だけがあり、原本参照がありませんでした。初回保存は登録済みPDFを扱う一方、日常保存は本文・アイキャッチの画像が中心で、添付登録そのものが正式履歴につながっていませんでした。

新しい処理は、登録済みの情報ファイルについて、原本・メタデータに記録された付随画像・必要な添付定義・閲覧条件を一組にします。初回保存と日常保存は `FileScope` の対象判定と `AttachmentHistory::assertComplete` の不足照合を共有します。非公開条件は保存を省く理由にせず、復旧時の配置条件として保持します。認識されないメタデータは原本側に残し、復旧先の設定として無条件に適用しません。

登録・メタデータ更新・削除をリクエスト終了時に処理し、既存のロックと保存待ちキューで正式履歴を確定します。閲覧条件だけの変更も添付一式を照合します。記事の再編集を待つ必要はありません。PDFブロックのIDを画像IDと誤認して記事保存を止める処理も修正しました。

不足するファイルは添付IDと理由を示して未完了に残します。保存元のファイルを戻した後は、既存の「履歴を再開」を使用できます。旧復旧点に原本不足がある場合は、復旧結果を「未完了」と表示し、S3に残っているが適用しない情報とは区別します。不足を含む状態を完全な新しい復旧点として確定しません。

## 形式と互換性

| 用途 | 新しい識別子 |
|---|---|
| 添付の正式履歴種別 | `owr_attachment` |
| 添付契約 | `owr-attachment-bundle-1` |
| 添付原本 | `owr-original-attachment-bundle-1` |
| 完全な初回保存・Checkpoint | `owr-separated-assets-attachment-bundle-1` |
| 添付を含む独立履歴Checkpoint | `owr-snapshot-attachment-bundle-1` |

S3のキー・版番号・SHA256参照、独立原本の分割形式、正式履歴の連番は既存の仕組みを使います。過去の原本・履歴は書き換えません。新版は旧形式を読み、不足は不足として報告します。rc.16は新しい履歴・完全復旧点・独立Checkpointを拒否します。新形式を使い始めた保存先へ旧版を戻して保存・整理を続けないでください。読取り拒否は旧版のすべての書込み操作を防ぐ保証ではありません。

## 再現可能な確認

- `tests/attachment-contract.php`: PDF原本、生成プレビュー、閲覧条件、原本のない閲覧条件の不足を検出。
- `tests/attachment-fixture.php`、`attachment-pdf.py`、`attachment-run.py`: 機密情報のないPDFをWordPressの通常のsideload・添付登録・プレビュー生成APIで作成。rc.16で漏れを再現し、新版で登録後に記事を編集せずに保全されることを確認。
- 公開PDF1件・保留PDF1件、それぞれ4件の生成JPEG。別WordPressへの復旧、PDFブロックの利用、添付名の更新、再保存、さらに別WordPressへの再復旧を照合。
- 公開URLの応答・内容ハッシュと、保留ファイルの非公開・非公開領域内の原本ハッシュを確認。
- 旧形式にある不足10件の報告、元ファイルを戻した後の再試行、正式履歴PUT失敗からの再開を確認。
- 実際のrc.16で、新形式3種類を復旧先へ適用せず拒否し、保存オブジェクトが変化しないことを確認。
- `tests/recovery-result.php`: 原本不足を成功と表示しないこと、日英の案内とパスのHTMLエスケープを確認。
- 既存の保存キュー、ハッシュ照合、独立Checkpoint、保持期間、本文保存、画像、閲覧条件、旧形式の回帰テストを確認。新しい契約テストは既存ActionsのPHP 8.1 / 8.3ジョブに追加。

隔離試験はcommunity上の専用Dockerネットワーク・専用DB/ボリュームで実施します。公開ポートと本番マウントはなく、メール・Cron・外部HTTPを停止します。S3操作はファイルベースの試験用SDKトランスポートで、実AWSの権限・通信・耐久性試験とは区別します。実際の保存元データを試験に追加保全したり、既存履歴を書き換えたりする処理は含みません。

実行時は隔離ディレクトリに `attachment-run.py` を `run.py`、`attachment-fixture.php` を `fixture.php`、試験用 `transport.php`、パッケージの `src/`、提出済みrc.16の複製を `candidate.zip`、WP-CLIを `wp.phar` として用意します。`attachment-pdf.py` で `manual.pdf` を生成し、`python3 run.py` を実行します。結果は `results/`。専用コンテナ・ネットワーク・ボリュームは終了時に削除します。実サイトのディレクトリをマウントしてはいけません。

## 実S3での最終確認（2026-11-14）

空であることを確認したランダムな試験専用prefixを使用し、実AWS SDK・EC2ロールで確認しました。認証情報のホスト間転送は行っていません。試験用トランスポートはバケット・prefix・所有者・操作種別を限定し、削除操作を許可しません。既存の本番S3領域には接続していません。

- PDF2件とWordPressが生成したJPEG8件：保存、復旧後の利用、再保存、再復旧で内容・添付情報・閲覧条件が一致。
- 公開側5件はHTTP取得内容のSHA256まで一致。保留側5件は直接URLが404で、非公開領域に原本を保持。
- 旧形式の読取り、旧復旧点の原本不足10件の表示、不足原本を戻してからの再試行を確認。
- 実際のrc.16が新しい履歴・完全復旧点・独立Checkpointを拒否。拒否・復旧処理の前後で試験S3の版一覧が不変。
- 正式履歴の書込み失敗を注入し、保存待ちからの再開を確認。途中の原本を完了扱いにしない。
- 最終レビューで、添付削除後のメタデータ削除通知が削除状態を上書きする経路を修正。実S3で削除記録の確定を確認し、専用回帰テストをActionsにも追加。
- 試験終了時のS3オブジェクト版数は171。試験データは新規prefixに残し、専用コンテナ・ネットワーク・ボリュームは削除。
- PHP 8.1でActions相当のパッケージ契約39コマンドが成功。旧形式名を期待していたACF・参照元情報テストは、新形式名に更新し、元の情報一致の検証を維持。

機械可読結果：[実S3確認結果](attachment-bundle-live-results-20261114.json)。ファイルベース試験の結果は[別記録](attachment-bundle-results-20261114.json)として保全しています。実S3実行時は `OWR_ATTACHMENT_LIVE=1` と `attachment-live-transport.php` を使用します。

## English summary

Daily capture previously missed newly registered PDFs even when their viewing conditions appeared in formal history. The new attachment bundle records registered originals, metadata-listed derivatives, required definitions and viewing conditions together, independently of article editing. Full and daily capture share file selection and completeness validation. Held files remain private after recovery while their bytes remain preserved.

Existing originals/history are unchanged. New readers accept old formats and explicitly report missing originals. rc.16 rejects new attachment history, full recovery points and independent history Checkpoints. Do not downgrade a writer or storage-management installation using the new format. No production update or replacement of a submitted ZIP/tag is part of this change.

The first isolated tests used real WordPress PDF registration/preview generation and HTTP checks with a file-backed S3 test transport. A subsequent run repeated the checks against real AWS S3 in a new, initially empty, guarded test prefix. It confirmed all ten files, public HTTP hashes, private retention, resave/second restoration, missing-original detection/retry, interrupted confirmation and rc.16 rejection of all three new recovery formats. Attachment deletion confirmation was also checked after correcting callback ordering. The live run produced 171 object versions; no production objects, submitted ZIPs or tags were changed. No new release ZIP has been created.
