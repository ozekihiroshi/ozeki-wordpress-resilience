# 二資産取得アダプターの日次接続（専用環境）

DB・ファイルの取得アダプターを日次枠へ接続する開発用入口です。生成したWordPress／MariaDBだけを対象にします。三資産の72時間観測とは別のSQLite台帳・Docker資源・S3セットを使います。既存のtimerは変更しません。

## 状態の意味

|状態|保存|署名承認|次回起動|
|---|---|---|---|
|running|取得または転送中|未承認|OSロックで重複を拒否|
|awaiting_approval|二資産の固定Version ID・読戻し・35日保持を確認済み|pending|同日枠は再取得・再送なし|
|approved|保存済み|別操作で署名・独立ピン・固定版を再検証済み|同日枠は再送なし|
|unknown|途中停止・失敗・証拠不足。保存されている可能性あり|未確認|翌日枠を含め自動送信を停止|

JSONでは `storage_complete` と `approval_state` を分けます。署名期限後は `expired`。`restore_allowed` は状態照会からは常にfalseです。実際の復元には独立保管のピンと署名をその都度検証する必要があり、approvedも本番再公開やマルウェア無害性を承認しません。今回の入口は復元を実行しません。

日次枠は日本時間03:00に切り替わります。取り逃した過去枠を後日成功で埋めません。未承認セットが残っていても翌日分は別枠で保存しますが、unknownが一つでもある場合は新たな送信を止めます。

## 1. 生成データを日次枠で保存する

WSL上で、リポジトリのルートから実行します。既存の実験バケットとcommunity/dmの分離ロールを利用できる環境が必要です。認証情報をコマンドへ書き込みません。

```bash
python3 tools/run-first-site-daily-lab.py --execute-lab \
  --state "$HOME/.local/share/owr-first-site-daily-lab" \
  --output "$HOME/.local/share/owr-first-site-daily-reports/run-$(date +%Y%m%dT%H%M%S).json"
```

stateは毎回同じ専用パスを指定し、outputは未使用ファイルにします。同時起動はロックで拒否され、同日の再起動で取得・PUTは繰り返しません。試験用サイトは実行ごとに作成・除去されます。報告ファイル、取得物、転送受領、台帳は保持します。プラグイン単体で本番サイトの日次取得が開始する機能ではありません。

```bash
python3 tools/first-site-daily.py \
  --state "$HOME/.local/share/owr-first-site-daily-lab" status
```

保存処理には署名鍵を渡しません。2件のPUTと対応する固定版読戻しの証拠が揃って初めてawaiting_approvalになります。取得不整合や停止解除不明はPUT前に拒否します。

## 2. 独立した承認を反映する

担当者が候補の内容とSHA-256を確認し、保存処理とは別の場所で署名します。試験用の `first-site-lab-sign.py` は生成データ専用の使い捨て鍵であり、本番署名鍵の代わりにはなりません。

```bash
python3 tools/first-site-lab-sign.py \
  --candidate "/専用state/first-daily-識別子/candidate.json" \
  --operator "/別の専用保管先/セット識別子"

python3 tools/first-site-daily.py --state "/専用state" approve \
  --day YYYY-MM-DD --trust "/別の専用保管先/セット識別子" \
  --document-sha256 "担当者が確認した候補のSHA256" \
  --key-sha256 "別管理した公開鍵のSHA256"
```

ハッシュを候補の申告値だけで自動承認しないでください。実行側は文書・公開鍵のピン、署名、有効期限を検証してからS3へアクセスします。拒否時は承認待ちを維持します。成功時も `isolated_restore_verified=false` です。同じWSLユーザー内の別ディレクトリ試験は、ホストや管理アカウントの独立性の証明にはなりません。

## 3. 停止・結果不明からの再開

起動を止める場合は、この専用コマンドを呼ぶスケジューラーを停止し、実行中の取得・停止解除・転送の結果を確認します。WordPressプラグインの無効化だけでは外部処理は止まりません。

プロセスが中断したrunningは、次回の排他取得時にunknownになります。台帳や受領記録を消して再送しないでください。2件のPUT・固定版読戻し・候補・保存完了受領が全て残り、台帳更新だけが中断していた場合は、担当者が照合して次を実行できます。

```bash
python3 tools/first-site-daily.py --state "/専用state" reconcile --day YYYY-MM-DD
```

この操作は再送せず、完全な保存証拠から承認待ちへ戻すだけです。証拠が不足するPUT結果不明・取得失敗を解除する汎用機能は未実装です。エラーを一律に安全な再試行とみなさず、手動調査を必要とします。

## 到達範囲

専用環境の取得→固定版保存→署名承認待ち→別操作による承認を対象とします。汎用ホスト向け取得アダプター、実サイトへのtimer配置、WordPress管理画面との統合、署名期限の更新・失効、承認後の自動隔離復元は別の課題です。共通PHP部品、Backup for S3、既存の72時間観測は変更しません。

## 承認後の明示的な隔離復元

[専用の復元入口](first-site-daily-restore.md)を追加しました。独立保管した署名文書・ピンから検証し、S3固定版二資産だけを取得して、新規の隔離WordPressへ復元します。日次保存から自動実行はせず、復元結果の自動集約も行いません。
