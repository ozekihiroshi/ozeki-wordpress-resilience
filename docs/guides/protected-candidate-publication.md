# 初回実データのS3保管・保持証拠・署名

実施：2026年10月18日。セット `RS-WP-CERI-20261018-001`。[公開集計](../../evidence-public/protected-candidate-publication.json)。

## 結果と位置付け

取得済みのDB、WordPress全体、実行イメージ、PHP設定、構成台帳、取得記録、隔離検証記録、復旧注意事項の8資産を正式バケットへ保存した。資産台帳とanchor・承認文書・署名を加えた計12オブジェクトを、復旧側ロールで固定Version IDから読み戻し、サイズ・SHA-256・GOVERNANCE保持を確認した。アップロード総量は458068818 bytes。

バケットは `ceri-link-resilience-prod-121426368082`、キーは `sites/wp-ceri-link/sets/RS-WP-CERI-20261018-001/` 配下。一意キーへ条件付きPUTを行い、受付前に試行記録を残す。結果不明時に自動再送しない。既存M1セットを上書きしていない。

これは **storage_verified_candidate（保管内容検証済み候補）**。今回の目的である送信・固定版・保持証拠・署名の結合は完了したが、ライブ取得の同時点整合性と無感染判定、本セットを用いたS3起点の完全復元は未完了である。既存M1用の合成データ復元ランナーへこのセットを入力しない。

## 転送と機密情報

ユーザーはDB・サイト全体・構成情報が認証情報や個人情報を含み得ることを確認し、この正式バケットへのアップロードを明示許可した。

communityのEC2ロールが15分有効の対象PUT限定リクエストを署名し、WSLの取得済みファイルからS3へ直接送信した。サイズ、SHA-256、ExpectedBucketOwner、SSE-S3、If-None-Matchを署名対象に含めた。dmの別EC2ロールで固定Version ID付きGETを署名し、WSLの新規専用領域へ読み戻した。

EC2の一時認証情報はEC2内で使用。秘密鍵はPC内で使用。署名付きURLはプロセスメモリだけで受け渡し、ログ・台帳・S3へ保存しない。両サーバーにアーカイブ一時コピーを作らず、AWSの設定変更も行っていない。読み戻し先は手元PCなので、S3のインターネット転送量として課金枠に関係する。過去のストレージのみの見積りは総費用ではない。

## 信頼の結合

1. 各資産の固定Version ID・サイズ・SHA-256・保持モード・期限・復旧側確認時刻を `protected-candidate.json` に記録。
2. 台帳自体をS3固定版で保存・独立取得し、その参照と最短保持期限を `candidate-anchor.json` に記録。
3. anchorのSHA-256、サイト、セット、承認世代、発行/失効時刻、限定スコープへRSA-SHA256で署名。
4. 独立ピンは公開鍵ハッシュと承認文書ハッシュを固定。保存元・S3の公開鍵を信頼の起点にしない。
5. anchor・承認・署名もS3へ保存し、固定版で読み戻した文書を検証。

署名形式は `owr-protected-candidate-approval-v1`、スコープは `storage_integrity_candidate_only`。M1用 `owr-recovery-approval-v1` と混同しない。保持証拠は検証時点の観測であり、未来の管理者による変更を検出済みとは扱わない。復旧時にも固定版の保持状態を再取得する。

今回の署名期限は **2026年10月25日18:15:47（日本時間）**。最短資産保持期限は **2026年11月22日18:13:29.382（日本時間）**。初回候補はレビュー更新を行う前提の7日承認とし、35日保管と区別した。期限後は検証を省略せず、独立レビュー・新世代で再承認する。

## 非公開の保管先と検証方法

WSL内の以下のディレクトリは0700、ファイルは0600の扱いとする。平文アーカイブに別のパスワード暗号化を追加したものではない。

- 資産・送信記録・固定版読戻し：`~/.local/share/owr-production/RS-WP-CERI-20261018-001/`
- 新サイトの独立公開ピンと取出し情報：`~/.local/share/owr-trust/wp-ceri-link/RS-WP-CERI-20261018-001/`
- 秘密鍵：既存PC鍵のまま。新しい信頼パケットには秘密鍵を複製していない。

```bash
cd /mnt/d/workspace/ozeki-wordpress-resilience
candidate="$HOME/.local/share/owr-production/RS-WP-CERI-20261018-001/reader-download"
trust="$HOME/.local/share/owr-trust/wp-ceri-link/RS-WP-CERI-20261018-001"
python3 tools/verify-protected-candidate.py   --trust "$trust" --approval "$candidate/candidate-approval.json"   --signature "$candidate/candidate-approval.sig"   --anchor "$candidate/candidate-anchor.json" --bundle "$candidate"   --site wp-ceri-link --set-id RS-WP-CERI-20261018-001
```

検証器はファイルを実行しない。期限切れ、失効、古い世代、署名/anchor/資産改変、不足資産、固定版欠落、対象バケット違い、保持不足を拒否する。合成データの契約テスト12件と、実署名による正例・負例8件を確認した。

`tools/pilot/` のスクリプトは今回のサイト・セット・ロールに固定したパイロット用で、自動日次運用ツールではない。成功済みセットを再実行・上書きしない。検証器は独立管理する `tools/verify-protected-candidate.py` を使う。

## 次の受入

- 今回のS3固定版から署名検証を必須として隔離復元し、ページ・メディアを再確認する。
- 今回追加した独立ピン・取出し情報を別媒体へ複製し、PC喪失時の取出しを試験する。既存USBの秘密鍵バックアップだけでは新しい信頼パケットのコピー完了にはならない。
- 同時点整合性、感染調査、侵入原因対処、資格情報更新を評価して本番復旧承認へ進む。候補の署名だけで再公開しない。


## 続報：S3起点の復元と別媒体保存

[実施記録](signed-s3-candidate-restore.md)のとおり、新規固定版取得・署名ゲート経由の隔離復元・基本内容確認と、新しいUSB公開信頼情報の読戻し検証を完了した。上記の未実施は公開時点の記録。無感染・同時点整合性・本番再公開の承認は未完了。
