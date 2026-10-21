# 導入判定付きの日次バックアップ（試作）

既存 `first-site-daily.Coordinator.tick_admitted` に初回取得入口を接続しました。保存済みの合格JSONではなく、保護された入力ファイルのパスを渡します。

```python
row = coordinator.tick_admitted(
    now, admission=dict(profile=profile_path, inventory=inventory_path,
        report=report_path, health=health_path, review=review_path,
        workspace=private_capture_workspace),
    backend=dedicated_backend,
)
```

`admission` は [初回取得仕様](first-capture-readiness.md) の最新入力です。workspaceは確認記録に結び付く事前作成済みの所有者限定フォルダーです。日次台帳と取得記録は保持し、別の試験や既存観測の台帳を流用しません。

## 実行順序と拒否

1. 既存の日次ロック・日次枠・未解決処理を確認。重複や結果不明の枠では取得も保存もしない。
2. 初回取得入口でサイトロック取得後と更新停止直前に入力を再検査。条件不足ならfence/streamを呼ばない。
3. 既存のDB・ファイル取得、整合性確認、停止解除を実行。解除不明や不整合なら保存しない。
4. 資産読取り後に再検査。さらに保存先の接続前検査後、S3アダプターを作る前に再検査。取得中・保存準備中に条件が変わってもPUTしない。
5. 既存publish/固定版・保持証拠確認を経て、保存完了と署名承認待ちを記録する。署名や復元許可は別操作。

拒否や失敗は既存台帳の `unknown`（要担当者確認）として記録し、自動再試行しません。明確な取得前拒否であっても今回新しい再試行状態は導入していません。記録を削除して同じ日次枠を強制再実行しないでください。取得開始後の結果は `capture-result.json` に残り、保存失敗は既存failure/receipt/transfer記録で調査します。保存前に止まった場合、receiptが存在してもstorage_completeはfalseです。

低水準の `tick` は既存試験・観測との互換性のため維持しています。新しい導入経路は `tick_admitted` を使用します。既存の72時間観測や本番の日次スケジュールは切り替えていません。技術的根拠は毎回5分未満を要求します。日次用担当者確認は最長7日で、明示的に更新し自動延長しません。長期無人の棚卸し更新と本番配置は残課題です。根拠は信頼する外部ホストで管理する前提であり、OS管理権限への防御ではありません。

## 専用試験

`python3 -B tools/run-first-site-daily-admission-lab.py --execute-lab --output /new/private/path/result.json`

新しいネットワークなしWordPress/MariaDB、生成データ、ローカルS3代替アダプターを使用します。実取得・日次台帳・publish・固定版と保持情報の検査コードを通しますが、S3の応答・保持情報は模擬値です。実AWSの権限・Object Lockの再検証や実S3送信は行いません。

環境、試験基盤、製品コードの問題を区別します。過去の原因未確定ブラウザ問題や72時間観測の欠測はこの試験の成功で解消扱いにしません。

結果：日次接続7試験、既存日次12試験、取得入口7試験が成功。実WordPress/MariaDB試験4項目も成功し、試験資源を削除済み。AWS送信は0件。追加のPython環境で既存日次SQLite接続の閉じ忘れがResourceWarningとして発覚したため、明示的closeを追加し、警告を有効にした日次接続7試験と既存日次12試験で再確認した。これは製品側の修正であり環境障害には分類しない。新規の環境・試験基盤障害は確認していない。

日次用確認の追補：[期限・更新方式](recurring-capture-review.md)。毎回5分未満の技術検査と、最長7日の担当者確認を分離。明示発行のみで自動延長なし。初回用確認の5分期限は維持します。
