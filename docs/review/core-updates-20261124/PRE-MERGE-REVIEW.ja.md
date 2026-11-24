# 次期候補の差分確認と導入案内 — 2026-11-24

対象はmainの `4053e1d` から開発ブランチの `629c245` までの変更と、その後の未コミット修正。今回、製品コードは変更していない。導入文書の修正と既存のオフライン確認を実施した。main取り込み・ZIP作成・本番反映・申請は未実施。

## 差分の判断

今回確認した差分と既存の結果の範囲では、新たに実装修正を必要とする具体的な問題は特定しなかった。ただし、最終ソースと公開済みMarkdown Documents 0.1.3を組み合わせた実S3の往復確認は残る。これを省略して公開可とは判断しない。

| 修正群 | 共通の変更点 | 既存の根拠 |
|---|---|---|
| 記事の属性・パスワード・投稿者、分類・基本設定 | 保存・適用でUpdateContractの項目と型を共有。分類の定義と所属をまとめ、古い記事付随情報で上書きしない | RESULTS.ja.md、verification-summary.json、core-update-contract / core-update-format |
| 予約公開・コメント・投稿者・添付削除 | 操作途中ではなく完了状態を記録。予約公開は編集者のログインを前提にしない。削除の根拠と保護識別情報を再保存にも引き継ぐ | FOLLOWUP-RESULTS.ja.md、followup-verification.json、completed-state / scheduled-capture / protected-identity / attachment-deletion-state / attachment-pending |
| クラシックメニュー・先頭固定・パーマリンク | メニューの内容・定義・所属を一組で扱い、設定一覧を初回保存と共有 | NAVIGATION-FIX.ja.md、navigation-verification.json、navigation-state |
| 基本設定9項目・参照設定2項目 | 共通設定一覧を利用。参照先は復旧点全体の構成後に検査し、不在なら解除して報告 | BASIC-SETTINGS-FIX.ja.md、REFERENCE-SETTINGS-FIX.ja.md、basic-settings / reference-settings |

実行コードの配置・プラグインのインストール・初期化は追加していない。準備済みアカウントへの権限付与や設定再生成も追加していない。投稿者表示用アカウントと権限のある既存アカウントが衝突した場合は上書きしない。削除済みファイルが復旧先に残る場合も、無条件に削除して穴埋めせず準備不足を報告する。

記録形式は `core-updates-5`。旧形式の独立原文を読めることと、古い復旧点全体を現在の規則で適用できることを区別する。候補版間の互換性を一律に約束せず、健全な保存元・復旧先を同じ対応版に揃え、新しい初回保存を作る。既存の原本・履歴を移行・書換えする修正ではない。

## 今回再実行した既存確認

次の12本が成功した。実S3、ブラウザ、本番、WordPress.orgには接続していない。

`core-update-contract`、`core-update-format`、`completed-state`、`scheduled-capture`、`protected-identity`、`attachment-deletion-state`、`attachment-pending`、`navigation-state`、`basic-settings`、`reference-settings`、`no-software-install`、`prepared-settings`。

最初の実行ではcore-update-formatにパッケージパス引数を渡さず停止した。既存試験の呼出しを修正して再実行し成功した。製品コードや期待値の変更はしていない。過去の段階別結果を、最終組合せの実S3確認として読み替えていない。

## 文書の修正

- ルートと同梱用READMEの日英、readme.txt、導入・更新・変更後対応ガイドを整理した。
- 新規Markdown導入は公開済み0.1.3を案内。未確定保存を解消し、健全な保存元を先に更新、新しい初回保存、復旧先に記録された同じ版を準備する順序とした。
- SiteSnapshotは記録済み依存版との一致を検査する。復旧先だけ新版へ変更して古い復旧点を使う案内にはしない。
- 過去の0.1.1試験記録は当時の証拠として残した。0.1.3との最終組合せが既に検証済みであるとは記載していない。
- PDF等を日常追跡しないという古い文言を、rc.17以降の登録添付の扱いに合わせた。
- メニュー・分類・設定はすべて初回保存のみ、という案内を整理。次期ソースの対応と提出済みrc.21を明確に分けた。ブロックナビゲーション、任意のテーマ設定、外部ファイルに対応範囲を広げていない。

## 取り込み・公開までの残り

1. 公開済みMarkdown Documents 0.1.3と最終Resilienceソースで、既存の代表シナリオを実S3の専用隔離領域で確認する。保存・復旧・利用・再保存・再復旧、原本不変、閲覧条件、準備済み設定を照合する。
2. 合格した差分を取り込み、Actionsを確認する。
3. 新候補ZIPそのもので導入・更新・Plugin Checkと必要な復旧確認を実施し、対応ソースと説明を揃える。
4. 本番反映・WordPress.org申請・メール返信は別の段階で報告する。

新しい仮説の網羅探索や機能追加を開始するための計画ではない。

## 後続確認

上記1の最終ソースと公開済み0.1.3による実S3確認は完了した。結果・確認範囲・30実行ファイルのハッシュは [FINAL-SOURCE-REAL-S3.ja.md](FINAL-SOURCE-REAL-S3.ja.md) と付属のmanifest/summaryを参照。取り込み時にも30件の一致を確認した。候補ZIP自体の確認は別工程として残る。
