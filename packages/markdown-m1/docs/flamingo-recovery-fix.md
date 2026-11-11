# Flamingo受信項目の復旧修正と確認記録

2026-11-11。これはmainに取り込む修正の記録です。提出済み0.3.3 rc.12には含まれません。rc.12のZIP・タグは変更せず、公開承認済みではなく審査担当者の回答待ちです。今回、新しいZIPの作成・申請更新は行いません。

## 修正内容と見逃しの原因

Flamingo 2.6.4では、`_fields`に項目名とnullを保存し、実際の受信値を個別の`_field_*`メタデータに保存します。以前の復旧規則は前者だけを適用し、後者を除外していました。S3の原本には値が残っていましたが、復旧後の管理画面では値が欠落し、その状態で再保存すると空の値が保存されました。

以前の確認は`_fields`同士を比較していたため、項目名とnullの一致を成功と判定していました。保存形式の一部分の一致を、利用できる受信内容の一致として扱ったことが原因です。未知の設定を除外する境界を作る際に、対応する情報を読み出すために必要な項目まで除外しないかという照合が不足していました。

修正では、各受信の`_fields`に宣言された項目名から、その受信に必要な`_field_*`の適用規則を組み立てます。すべての同名接頭辞を一括許可するものではありません。既存のデータ型検査を通し、オブジェクト、曖昧な項目識別子、重複した項目マップを拒否します。別の投稿種類や未知の付加情報へ許可を広げません。

原本の保存処理、保存形式、正式履歴の形式は変更していません。添付ファイル・アドレス帳などへの対応追加も行っていません。

## 再発を防ぐ確認方法

`tests/flamingo-application.php`を既存の`tests/application-rules.php`から実行し、既存のContracts CIに組み込みました。

- 項目マップだけでなく、Flamingoが読み出す実効値を独立した期待値と比較します。日本語、改行・記号、配列、空文字、文字列の0、シリアライズに見える文字列を含めます。
- 値のメタデータを意図的に削除した結果が不一致になることも確認します。修正前のrc.12で、この確認が失敗することを確認してから修正しました。
- 旧形式のマップ内の値と、個別メタデータが優先される形式を確認します。未宣言項目の除外、オブジェクト・識別子衝突・重複マップの拒否、他の投稿種類への影響も確認します。
- アダプターの変更では、保存された値だけでなく、その意味を決める定義と利用側の読み出し方を照合します。適用規則を狭める変更でも、正常な対応データが欠落しないことを合格条件にします。
- 統合確認では、保存成功・復旧成功だけを合格にせず、復旧後の表示、標準操作による再保存、次の保存からの再復旧まで、同じ期待値で確認します。

自動確認は適用規則の回帰検出を担います。実際のFlamingo画面やS3を使う一連の確認は別の統合確認であり、すべてがCI内で動くわけではありません。

## 隔離環境での確認結果

WordPress 7.1.3、PHP 8.3.36、Contact Form 7 6.2.5、Flamingo 2.6.4で確認しました。本番と別の試験サイト・DB領域と、新しい実S3保存領域を使用し、外部メール送信を止めています。

| 確認 | 結果 |
|---|---|
| CF7から実送信した受信の初期保存・正式履歴からの復旧 | 両方の受信で6項目の実効値が一致 |
| 復旧先でのFlamingo管理画面の閲覧 | 値を表示できることを確認 |
| Flamingo標準save()による再保存 | 再読み出し後も値が一致 |
| 復旧先での新規受信・再保存領域から第三サイトへの再復旧 | 全3受信で実効値が一致し、管理画面でも確認 |
| 修正前rc.12が作った既存原本からの復旧 | 欠落なく復旧。原本・正式履歴・初期保存manifestのハッシュ不変 |
| PHP構文・既存適用規則・新しい回帰確認 | 成功 |
| Plugin Check | エラー0、警告100。rc.12と警告の種別別件数も同じ |

これは上記構成での確認結果であり、すべてのFlamingo版や拡張機能の確認完了を意味しません。

## 互換性と運用上の注意

既存原本の書き換えや移行は不要です。ただし、欠落状態で再保存して既に空になったデータは、この修正だけでは補完されません。値が残っている以前の原本から復旧します。

試験の終盤に共有ホストの空き容量が不足しました。今回の試験用コピーを整理してPlugin Checkを完了し、結果を保存して試験サイトの保護を停止しました。終了時の空きは約551MBのため、次の大きな試験前に容量を確保する必要があります。本番サイトの設定・保存先・保護開始は変更していません。

## English summary

This main-branch fix is not included in submitted 0.3.3 rc.12. The submitted ZIP and tag remain unchanged; the application is awaiting the reviewer's response, not approved. No new ZIP or submission is part of this change.

Flamingo 2.6.4 stores a field-name/null map in `_fields` and actual values in individual `_field_*` metadata. Recovery previously retained only the map. Originals still contained the values, but restored receipts lost them; saving those receipts could persist empty values. Earlier checks compared the null map instead of the values consumed by Flamingo.

Recovery now derives per-receipt application rules from declared field names, retaining their values through existing data validation. It does not admit arbitrary metadata or executable software. Capture, original formats and formal history remain unchanged.

The regression check compares effective values with independent expectations and proves that deliberately removed values are detected. It covers old inline values, individual-value precedence, empty/zero/array values and rejection boundaries, and runs through the existing application-rules Contracts CI. Separate isolated integration checks covered real CF7 submissions, real S3 baseline/history recovery, the Flamingo admin view, standard re-saving, new receipts and recovery into a third site. All tested receipt values matched. Recovery from pre-fix originals also passed with original/history hashes unchanged. Plugin Check reported zero errors and the same 100 warnings as rc.12.

Existing originals need no migration. Data already re-saved empty must be recovered from an earlier original that still holds the values. Future adapter changes must check the complete value/definition/consumer relationship and the full use, re-save and re-recovery cycle, rather than treating storage or restoration completion alone as success. The isolated host also needs more free space before further large tests.
