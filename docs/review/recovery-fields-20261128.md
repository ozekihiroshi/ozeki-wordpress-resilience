# Markdown過去版・CF7連携・入力説明・元ファイル名の修正

後続の[実S3確認・取り込み記録](recovery-fields-s3-20261128.md)。以下はローカル転送を使用した先行確認時点の記録。

確認日：2026-11-28 JST。前回の[限定調査](recovery-embed-20261128.md)で未修正とした項目への対応。
TablePressの修正と同じ作業ブランチ内で実施し、mainへの取込み・公開物作成・申請は行っていない。

## 修正した適用境界

| 対象 | 修正内容 |
|---|---|
| MarkdownのWordPress過去版 | 親が保全対象のMarkdown文書であるrevisionに限り、`_ozmd_source`を原文のまま復旧。無関係・親不明のrevisionには許可しない |
| 差し戻し後の派生状態 | 復旧済みサイトのMarkdownを標準の過去版復元で戻した後、原文ハッシュを再計算し、表示キャッシュを破棄する。原文を加工しない |
| CF7→Flamingo | `flamingo_name/email/subject`の単一フォーム項目参照を許可。事前導入済みCF7の構文解析で存在する項目名と照合。引用符なし・単引用符・二重引用符を扱い、任意命令・特殊メールタグ・不存在項目・HTML混在の指示は許可しない |
| ACF | 対応フィールドの`instructions`を文字列として復旧対象に含める。管理画面に表示される説明文だけをHTMLの安全処理対象とし、値・選択肢等の構造化データは変換しない。任意ショートコードを実行しない |
| Markdown元ファイル名 | `.md`の書き出し名として保持。ディレクトリ部分を取り除き安全なファイル名へ限定し、変更した場合は適用記録に残す。実ファイル配置先の指示としては使わない |

保存処理・原本形式・履歴形式は変更していない。既存原本に入っている情報を復旧時に適切に利用する修正。
以前の復旧で情報を除外し、その状態だけを再保存した場合、失われた情報はそこから生成できない。
情報を含む元の保全データを使う必要がある。

## 確認結果

- 提出済みrc.23のコピーで回帰確認が `Markdown revision source lost` により失敗することを確認した。
- 修正後の契約確認：正しい親の原文を保持、無関係なrevisionを除外、原文のscript表記を原文として保持、ファイル名をパスとして使わない、存在するCF7項目だけを対応付け。すべて成功。
- 合成原本を初回保存→復旧→利用→通常保存→新しい初回保存→再復旧→再利用した。
- 両復旧後、WordPressの標準`wp_restore_post_revision`で旧Markdown原文へ戻り、原文ハッシュも一致した。現在原文も保全されている。
- 両復旧後、ACFの項目描画処理で説明文が表示され、script要素と実行可能な未認識ショートコードは残らない。`PLC <PLC> [channel]`という値は不変。
- ACFの定義・値、CF7フォームを通常のAPIで再保存してから再復旧し、同じ利用確認に成功した。
- Markdown Documentsの実際の書き出し名生成処理で、両復旧後とも`technical-source.md`を確認した。HTTPによるダウンロード全体の試験とは区別する。
- CF7のsubmit→Flamingo受信フックを通し、標準項目名と独自項目名の両方で氏名・メール・件名を確認した。再復旧後も一致。`skip_mail`で実メール送信はしていない。
- TablePressのページ表示・編集を含む既存の往復確認と、HTML・未認識ショートコード・動的ブロックの既存安全確認も成功した。
- 試験の保存済みオブジェクトは内容ハッシュ不変。提出済みrc.23 ZIPはSHA-256不変。

## 確認条件と範囲

dmの新しい専用Dockerネットワーク（internal、公開ポートなし）と独立DBを使用。
WordPress 7.1.5 / PHP 8.3、CLIメモリ256MB、CF7 6.2.5、Flamingo 2.6.4、ACF無料版6.8.11、
Markdown Documents 0.1.2、TablePress 3.4.1、WP-Members 3.5.8.3。
製品はrc.23のコピーに今回の変更ソースを適用した。

S3 SDKの既存ローカル試験転送を使った。実S3での追加確認、保護オンの日常保存による正式履歴確定、
全管理画面の対話的ブラウザ操作、実メール配送、Markdown Documents 0.1.3での確認は今回の範囲外。
本番・既存の原本と履歴には接続せず、変更もしていない。試験用の架空データだけを使用した。

最初の試行では試験側の作業ディレクトリ未作成と再復旧先URLの重複を製品が拒否した。
試験環境を正し、新規DB・新規試験prefixで一連の最終確認を完了した。安全条件の緩和はしていない。

補足：復旧前のMarkdown Documents 0.1.2では、標準の差し戻し後に原文ハッシュが追随しない挙動を
観測した（結果の`source_revision.derived_hash_matches=false`）。今回追加した派生状態の更新は
復旧済みサイトに限定しており、その条件では両復旧後ともtrue。Markdown Documents本体は変更していない。
この観測を「保存元の通常利用も含めた解消」とは扱わない。

## 再現用ファイル・証拠

- `packages/markdown-m1/tests/recovery-field-contract.php`：適用境界の回帰確認。
- `packages/markdown-m1/tests/recovery-fields-roundtrip.php`：合成データと各段階の操作。専用環境の`/lab/fields.php`に配置。
- `packages/markdown-m1/tests/recovery-fields-run.py`：専用Docker環境の段階実行と合格判定。新規DB・新規保存prefixで使用。
- [往復確認結果](recovery-fields-20261128/results.json)
- [適用契約確認](recovery-fields-20261128/contracts.txt)
- [既存の安全確認](recovery-fields-20261128/safety.txt)

## English

The recovery projection now preserves Markdown revision sources only for recognized Markdown parents,
retains safe `.md` export filenames, restores ACF field instructions with presentation-only sanitization,
and accepts the three CF7-to-Flamingo mappings only when they reference existing form fields.
Restoring a Markdown revision on a recovered site refreshes its derived hash and clears render caches.
Archived originals, storage formats and history formats are unchanged.

Synthetic isolated round trips passed after normal field/form saves and recapture. Both recoveries preserved
usable old Markdown revisions, ACF instructions and values, export filenames and actual Flamingo receipt
name/email/subject values for default and custom field names. Existing content-safety and integration checks passed.
Storage used the local SDK test transport; no production/S3 access or external email occurred.
The original Markdown Documents 0.1.2 source-side revision hash observation remains separate from the recovered-site fix.
Submitted ZIPs/tags and existing originals/history were not changed; no publication was performed.
