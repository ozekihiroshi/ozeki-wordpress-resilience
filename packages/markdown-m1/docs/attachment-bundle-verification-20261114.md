# 添付一式の保全 / Attachment bundle preservation

この変更は開発ブランチの確認用です。main、本番、提出済みrc.16のZIP・タグは更新していません。

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

## English summary

Daily capture previously missed newly registered PDFs even when their viewing conditions appeared in formal history. The new attachment bundle records registered originals, metadata-listed derivatives, required definitions and viewing conditions together, independently of article editing. Full and daily capture share file selection and completeness validation. Held files remain private after recovery while their bytes remain preserved.

Existing originals/history are unchanged. New readers accept old formats and explicitly report missing originals. rc.16 rejects new attachment history, full recovery points and independent history Checkpoints. Do not downgrade a writer or storage-management installation using the new format. No production update or replacement of a submitted ZIP/tag is part of this change.

The isolated tests use real WordPress PDF registration/preview generation and HTTP checks, with an isolated file-backed S3 test transport. They cover restoration, use, resave and second restoration, missing-original detection/retry, interrupted confirmation and old-reader rejection. This is not a live AWS IAM/network validation.
