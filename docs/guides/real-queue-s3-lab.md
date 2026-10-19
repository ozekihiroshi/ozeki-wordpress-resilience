# 実験用S3と分離ロールによる三資産往復試験

## 対象と設定

対象バケットは `ceri-link-resilience-lock-lab-121426368082`、東京リージョン。新規 `sites/isolated-queue-lab/sets/AWS-<乱数>/` 配下だけを使う。以前の `object-lock-probes/` と正式保管バケットには書き込まない。

`community` の `my-ssm-role` で保存、`dm` の `OwrM1RecoveryReader` で固定版取得を行う。IAM追加手順とJSONは [examples/queue-s3-lab](../../examples/queue-s3-lab/README.md)。EC2ロールの付替えは不要。長期アクセスキーやAWSのdefaultプロファイルは使わない。

署名要求を作る前にSTSで実行主体・アカウントを検証し、IMDSv2で当該EC2ロールの一時認証を取得する。署名付きURLは短時間の通信にだけ使用し、ログ・証拠へ保存しない。URLの宛先・キー・Version ID・期待バケット所有者を手元でも検査し、リダイレクトを拒否する。

## 保存・検証

事前にリージョン、Versioning、Object Lock、SSE-S3、公開遮断、バケットポリシー・Lifecycleを確認する。今回の基準はポリシー・Lifecycleなしの既存専用バケット。新しい設定が見つかれば勝手に変更せず確認を止める。

保持はPUT時にGOVERNANCEで付与する。通信遅延を考慮し、要求時刻から35日10分を指定し、保存後のLast-Modifiedとの差が35日以上であることを検証する。MD5とSHA-256 checksum、SSE-S3、If-None-Matchを指定する。不確定なPUTを盲目的に再送せず、非公開の操作記録を調べる。

試験対象は専用WordPressで生成した架空データ。DB・ファイル・キューの合計を128MiB以下に制限する。実サイトのDB・個人情報・認証情報は取得しない。サーバーには大きな一時アーカイブを作らず、手元からS3へ直接転送する。

1. 小さなpermission-probe.txtで、復旧側PUT拒否を確認する。
2. 保存側で同probeを保持付き保存し、復旧側で固定版取得する。
3. 復旧側・保存側の固定版DELETEがAccessDeniedになることを確認し、probeが取得できることを再確認する。
4. 三資産を保持付き保存し、復旧側で全Version ID・サイズ・SHA-256・保持証拠を照合する。
5. 手元WSLの試験専用鍵で文書へ署名する。公開鍵・承認ピンは手元の独立ディレクトリに保持する。
6. 署名文書・署名も保持付き保存し、独立ピンのVersion IDから再取得する。
7. 不正署名が資産取得前に拒否されることを確認し、正常な署名で三資産を再取得・検証する。
8. 検証済みバイト列から隔離WordPress/MariaDBとキューを復元し、未処理ジョブ・ACK喪失分の配送を確認する。

削除拒否は今回のIAMポリシーの明示Denyを含む結果であり、削除許可を持つ主体へのObject Lock単独の強制力を改めて実証する試験ではない。以前の[Object Lock試験](object-lock-lab.md)と区別する。HTTP403でもSignatureDoesNotMatch等は合格にせず、AccessDeniedのみを対象とする。

## 実行

先に2つのIAMポリシーを追加する。ローカル模擬試験は従来の`--external`のまま。以下の`--s3-lab`を明示した場合だけ実AWSへ書き込む。

```bash
cd /mnt/d/workspace/ozeki-wordpress-resilience
python3 tools/run-wordpress-consistency-lab.py --execute-lab --s3-lab \
  --lab-image owr-external-lab:local --output .local/real-queue-s3-new.json
```

出力ファイルは新しい名前を指定する。失敗時も作成済みのS3版は保持する。試験コンテナはfinallyで後片付けする。既存の業務コンテナやDBには触れない。

## 証拠・鍵・後片付け

非公開の転送記録と信頼情報はWSLの `~/.local/share/owr-queue-s3-lab/AWS-<乱数>/` に保存する。`transfer-receipts/operations.json`、`operator-trust/pin.json`、公開鍵、署名文書・署名、`result.json` が残る。保存時の成功と最終復元成功は別段階として記録する。

試験専用の秘密鍵は署名後に削除する。本番署名鍵やUSBは使わず、community/dm/復元コンテナへ秘密鍵を渡さない。承認の期限は最大7日で、この試験鍵による更新運用は行わない。長期運用の鍵バックアップ・更新・失効運用が完了したという意味ではない。

S3にはprobe・三資産・署名文書・署名の計6オブジェクト版が残る。期限が過ぎても自動削除されない。bypassせず、後日の整理は別途行う。検証後に今回追加した2つのIAMポリシーを取り外すと、この実験セットの再取得もできなくなるため、必要な読戻しを終えてから取り外す。

参考: [AWS PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)、[Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html)。

## 実測結果（実AWS）

専用環境43ケースに合格。実S3へ試験専用の三資産・署名文書・署名・権限probeの6版（合計29,845,276 bytes）を保存し、分離ロールで固定版・保持・署名を検証後、隔離復元と再配送まで完了した。[実測記録](../../evidence-public/real-queue-s3-roundtrip.json)。

三資産の最短保持期限は 2026-11-23T08:22:20+09:00（日本時間）。S3の試験データは保持中で削除していない。手元の独立信頼情報は残し、試験専用秘密鍵と試験コンテナ・匿名ボリュームは削除済み。IAMの追加2ポリシーは取り外していない。追加の読戻しが不要になったら、コンソールでOwrQueueS3LabWriter / OwrQueueS3LabReaderのみ取り外す。既存の業務用・正式保管用ポリシーは維持する。

削除拒否はIAM明示Denyを含む実測。Object Lock単独の削除拒否を再実証したとは扱わず、本番データ・本番署名鍵・本番の復旧承認は対象外とする。

初回は署名文書の更新時刻が手元の観測時刻より先行し、厳格な時刻照合で停止した。保持期間は35日以上だった。5秒以内の先行なら時刻が追いつくまで待ち、過大な差・時計停止は拒否する修正を加え、Python契約114件に合格した。元の失敗記録と既存署名を維持し、保存済み三資産・署名文書の固定版を再利用して再開した。初回の権限拒否・三資産保存の証拠を再利用したケースは実測JSONに明記している。今回作成した隔離コンテナのサイト内容を空にして復元し、署名されたアーカイブと全ファイル一覧・ハッシュの一致も確認した。
