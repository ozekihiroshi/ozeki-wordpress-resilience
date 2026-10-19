# 日次の実S3保存と独立署名承認（専用環境）

日次ジョブはDB・ファイル・キューを保存し、署名せずに終了する。保存完了は復旧承認と別である。対象は専用WordPress／MariaDBの生成データ、東京の `ceri-link-resilience-lock-lab-121426368082`、`sites/isolated-queue-lab/sets/AWS-.../` に限定する。

## 状態と完了条件

| 状態 | 条件 | 次の扱い |
| --- | --- | --- |
| `running` | 取得・送信・固定版読戻し中 | 同じ台帳では他の実行を拒否 |
| `failed` | ワーカー開始前の事前確認で失敗 | 原因を直して `--retry-failed` |
| `unknown` | ワーカー開始後のエラーや応答喪失 | 当日・翌日の自動送信を停止。元の受領記録を調査 |
| `awaiting_approval` | 三資産のPUT受領Version ID・35日保持・別ロールでの固定版読戻し・整合性を確認 | 保存完了。同日の再送は省略。翌日は別セットを保存可能。署名承認は未完了 |
| `approved` | 独立して指定した鍵・文書ハッシュ・署名を検証し、三資産を固定版で再取得して保持と整合性を確認 | 署名承認済み。自動復元はしない。無感染認定・本番復旧承認ではない |

`last_storage_complete_day` と `last_approved_day` を分ける。承認待ちは `missing_days` に含めず、`awaiting_approval_days` に示す。承認期限切れ・承認記録読取り不能は `expired_or_unreadable_approval_days` に示し、監視を要する状態とする。保存が完了したtickは終了コード0でも、承認待ちのstatusは2となる。

取得から後片付けまでの34ケースが成功して初めて日次台帳を保存完了にする。S3へのPUTは三資産だけ。候補文書は作業フォルダの `candidate/candidate.json`、受領記録は `candidate/receipt.json` と `candidate/transfer-receipts/operations.json` に保存する。日次ジョブは秘密鍵を受け取らず、鍵生成・署名・復元の処理へ進まない。

## 実行方法

既存の[実S3実験用IAM手順](real-queue-s3-lab.md)を使用する。保存はcommunityの `my-ssm-role`、固定版読取りはdmの `OwrM1RecoveryReader`。長期アクセスキーやIAM変更は不要。

WSL Ubuntu-24.04で次を実行する。模擬S3の日次台帳と混ぜない。状態ディレクトリには保存モードを固定記録し、別モードでの再利用を拒否する。

```bash
python3 /mnt/d/workspace/ozeki-wordpress-resilience/tools/daily-backup-lab.py tick \
  --storage s3 --execute-lab \
  --state-dir "$HOME/.local/share/owr-daily-s3-lab-20261019"
python3 /mnt/d/workspace/ozeki-wordpress-resilience/tools/daily-backup-lab.py status \
  --storage s3 --state-dir "$HOME/.local/share/owr-daily-s3-lab-20261019"
```

時間帯は既存の日次試作と同じ日本時間03時。タイマーは有効化していない。実S3を使う場合は明示的な `--storage s3` が必要。既存の模擬タイマー例は実S3送信へ自動変更しない。

## 独立した署名操作

運用担当は候補文書と文書SHA-256を受領し、サイト・セット・三資産・チェックポイント・固定Version ID・保持期限・対象の取得日時を確認する。公開鍵は候補文書内の指定を採用せず、運用担当が別途保管している鍵と既知の指紋を指定する。文書ハッシュを比較するだけでは取得元の無感染を証明しない。

`sign-daily-lab-candidate.py` は日次ジョブから呼ばれないオフラインの専用試験用署名ツール。署名専用環境へ候補文書を移して実行する。秘密鍵のパスや鍵そのものを日次設定へ渡さない。

```bash
python3 tools/sign-daily-lab-candidate.py --sign-lab-candidate \
  --document /operator/review/candidate.json \
  --private-key /operator/keys/lab-private.pem \
  --expected-document-sha256 REVIEWED_DOCUMENT_SHA256 \
  --expected-public-key-sha256 KNOWN_PUBLIC_KEY_SHA256 \
  --signature /operator/review/recovery-set.sig
```

署名文書を変更して期限を延ばす操作はしない。今回の承認期限は候補作成から最大7日・保持期限以内。待機中に期限が切れたら署名・承認を拒否する。承認更新は別途設計する。

署名と公開鍵のみを承認取込み側へ渡す。文書SHA-256と公開鍵指紋は運用担当が独立して確認した値を指定する。

```bash
python3 /mnt/d/workspace/ozeki-wordpress-resilience/tools/daily-backup-lab.py approve \
  --storage s3 --state-dir "$HOME/.local/share/owr-daily-s3-lab-20261019" \
  --day YYYY-MM-DD --signature /operator/review/recovery-set.sig \
  --trusted-public-key /operator/keys/lab-public.pem \
  --expected-document-sha256 REVIEWED_DOCUMENT_SHA256 \
  --expected-key-sha256 KNOWN_PUBLIC_KEY_SHA256 \
  --operator-dir /operator/trust/NEW_SET_DIRECTORY
```

承認取込みでは公開鍵指紋・文書ハッシュ・署名・期限を検査してからS3読取りを行う。署名不正なら資産の取得前に止まる。S3再読取りはreaderのみで、追加PUT・削除は行わない。再読取りで保持不足・資産不整合を検出した場合も承認待ちを維持する。

運用担当の保管フォルダは日次台帳の外に新規作成する。そこへ署名文書・署名・公開鍵・独立ピン・承認結果を残す。`pin.json` の `envelope` は空で、今回の承認束は独立媒体から直接選択する形式。署名束のS3保管、USB更新や別媒体への配布は未実施。

## 障害と再開

- 事前失敗：同じ台帳へ `--retry-failed` を指定。ワーカー開始前である証拠が必要。
- PUT結果不明：同じ候補フォルダへの再送を拒否。台帳削除や新しい台帳への切替で回避しない。
- S3保存済みだが最後の台帳更新が失われた：`reconcile --storage s3 --day YYYY-MM-DD` で元の34ケースの完了報告と候補・PUT/GET受領記録を照合する。承認待ちへ戻すだけで承認済みにはしない。
- 署名不正・公開鍵違い・文書差替え：承認待ちを維持。独立した照合元を確認する。検証条件を緩めない。
- 承認取込み中の読取り失敗：S3への変更はない。原因を解消後、新しい運用担当フォルダで再検証する。失敗したフォルダも調査用に残す。
- 承認処理完了直後の台帳更新喪失：保存候補は再送しない。既存の運用担当フォルダを保管し、新しいフォルダで同じ署名と固定版を再検証する。

## 試験範囲と境界

本試験では日次プロセスと署名プロセスを分け、試験用秘密鍵を日次台帳外に一時作成し、署名後に破棄する。本番鍵にはアクセスしない。ただし同一WSLユーザーで行う専用試験であり、OS権限や別PCによる強制的な隔離の証明ではない。本番では保存元から署名鍵と独立信頼情報を変更できない配置・権限を別途整える。

今回は生成データの実S3保存と承認分離まで。新しいセットの隔離復元、実サイトの日次取得、本番の署名承認、外部通知、定期起動、保持後の削除は実施しない。34ケースの保存試験を、以前の43ケースの実S3復元試験や51ケースの模擬日次復元試験と混同しない。

## 実測結果（2026-10-19）

日次の専用環境34ケースと全Python契約143件に合格。未署名で実S3へ3版・合計29,842,275 bytesを保存し、台帳が承認待ちで停止することと同日の重複送信防止を確認した。誤った確認済みハッシュでの署名を拒否し、不正署名の取込みをS3読取り前に拒否した。別プロセスの試験用署名を取り込み、固定版の3回のGETだけで保持・ハッシュ・チェックポイントを再検証して承認済みへ移行した。[実測記録](../../evidence-public/daily-s3-approval-lab.json)。

最短保持期限は 2026-11-23T09:05:21+09:00、試験承認期限は 2026-10-26T08:55:35.050921+09:00（日本時間）。S3の3版は削除していない。試験秘密鍵は署名直後に破棄し、運用担当フォルダに公開鍵・署名・候補文書・ピンを保持している。今回のセットの隔離復元は実行していない。IAMと本番環境は未変更、タイマーも未有効化。

## 後続の隔離復元

本書の承認済みセットは、[後続の隔離復元試験](approved-daily-restore.md)で固定版取得・署名検証・DB/ファイル/キュー復元まで実測した。本書の承認時点の記録は履歴として変更しない。
