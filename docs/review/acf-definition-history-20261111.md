# ACF定義の独立保全 — main取り込み記録

2026-11-11。対象実装: `57297bc8d075d67b5fb90b9378a480ec1ffefd83`。

## 判断と変更内容

ACF無料版のDB定義を、記事保存とは独立して正式履歴へ保存する更新をmainへ取り込む。既存ガイドは定義単独変更を対象外として新Baselineを要求していたため、既存保証への違反の修正ではなく、承認された制限の解消である。提出済みrc.10には含まれず、今回、新しいZIPの作成やWordPress.orgへの送信は行わない。

定義操作完了後に全定義を既存の書込みロック内で取得し、既存キュー・固定版照合・正式履歴へ接続する。空の定義一覧も有効な削除状態として扱う。後続の記事原本に同梱された旧定義で最新定義を戻さない。記事がなくてもBaselineに定義を保全する。原本を選別・削除して復旧を成立させる変更ではない。

## 確認結果

専用DB・コンテンツ領域・S3子prefixを持つ既存の隔離環境で実施。WordPress 7.1.3 / PHP 8.3.36 / ACF無料版6.8.10。既存サイトの利用者データは使っていない。

| 確認 | 結果と範囲 |
|---|---|
| 実S3での定義変更・削除 | 記事保存なしで正式履歴に確定し、復旧先の定義と一致 |
| 管理画面の通常操作 | Chromeから作成・変更・削除。履歴件数は順に1・2・3、各段階で未確定・取得エラーなし。復旧はCLIで実行し、ACF APIで元サイトと照合して差分0 |
| グループの操作 | ゴミ箱移動・復帰・完全削除の反映を確認 |
| 記事ゼロ・全定義削除 | Baseline＋履歴、Checkpointの両方で定義の存在／空状態を復旧 |
| 復旧後の利用・再保存・再復旧 | get_field、定義・値・参照を照合。復旧先で値と定義を変更し別S3領域へ保存、第3サイトで再復旧して一致 |
| 原本・履歴の保全 | 各復旧の前後で対象試験領域の原本・正式履歴のハッシュが一致 |
| 機械的な欠落検出 | 正常な対応データの267末端項目を個別に除去し、267件すべてを検出。製品の適用処理から独立した照合 |
| キュー回帰 | ロック内取得、取得失敗時の解錠、凍結原本の再開、同一状態抑止を確認。障害注入はメモリS3試験 |
| 既存処理 | 保存失敗、確定照合、コメント、問い合わせ、会員契約、ACF準備画面の日英表示等が合格 |
| Plugin Check 2.1.0 | エラー0、警告99。rc.10とfile/type/code/messageを重複込みで比較し差分0（行番号移動を除外）。警告解消を意味しない |

初期試行の環境設定・試験ハーネスの失敗は成功件数に含めず、修正後の結果を採用した。試験終了後は保護を停止し、一時的な管理画面アクセス設定とURLを復元、SSHトンネルを終了した。

## 互換性と保全

既存の `owr-acf-1` 記事原本は変更せず、新版で旧Baseline・履歴を復旧できることを確認した。新しい定義履歴は `owr-acf-definitions-1`。これを含むBaseline・Checkpointは `owr-separated-assets-acf-definitions-1` と識別する。旧読込処理が新履歴・復旧点を拒否することも確認し、古い定義を黙って適用させない。復旧には対応する更新版を準備する。

- 提出済みrc.10 ZIP SHA-256: `a762c181772ded58ac403ad520a731278c4c73ed91181d3326bd1cab6420acbf`
- 保全するタグ: `wporg-0.3.3-rc.10`（タグオブジェクト `ac939587309c48177e8796bb93c5d68cb2751b28`）
- 研究ブランチの未コミット変更は取り込まず、変更しない。

## 残る範囲

今回の結果は全対応データの検証完了や公開承認を意味しない。実並行リクエストの負荷試験、新候補ZIPの作成・導入更新確認は未実施。適用契約は正常な対応データ用であり、対象外データ・削除済み定義への残存値などの任意入力判定を網羅するものではない。復旧ボタンのブラウザ操作を今回のCLI復旧結果で代替したとは扱わない。

手元の詳細証跡は `release-readiness/acf-definition-fix-20261111/` と `release-readiness/acf-definition-admin-20261111/` に保持。秘密を含み得る入力・環境情報は公開しない。本書は公開可能な結果の要約である。

## English summary

The approved ACF free update records database definition changes independently of article saves, using the existing locked history queue. Isolated real-S3 tests covered definition edits/deletions, group lifecycle, no-article states, recovery, changed resaves and recovery on a third site. Browser-created, edited and deleted definitions were recovered through the CLI and matched independent ACF API observations. Plugin Check 2.1.0 reported zero errors and the same 99 warnings as rc.10, compared by file, severity, code and message.

Existing originals remain unchanged and readable. New definition history and its recovery points require the updated reader; old readers reject them. This is a development merge, not a new release or submission. The submitted rc.10 ZIP/tag and uncommitted research work are preserved. Concurrent-load and new-package installation/upgrade checks remain outside this verification.
