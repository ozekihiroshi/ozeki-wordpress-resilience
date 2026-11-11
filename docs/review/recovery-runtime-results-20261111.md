# TablePress・Markdownの復旧継続性：修正と確認結果

2026-11-11。mainへ取り込む開発変更の記録。**提出済み0.3.3 rc.11のZIP・タグには含まれない。新しい公開用ZIPは作成せず、WordPress.orgへの送信も行わない。** rc.11は審査担当者の回答待ちであり、公開承認済みではない。

## 修正内容と構築方針

| 対象 | 原因 | 対応 |
|---|---|---|
| TablePress | 実行用設定を除外した結果、導入先が必要とするキーまで欠け、表の表示がHTTP 500になった | 保存されたカスタム命令は適用せず、`datatables_custom_commands`を安全な空文字で用意する。他の対応値と原本は維持する |
| Markdown | 原文に元サイトのURLを残す一方、次の保存に引き継ぐ参照元が直前のサイトに限られ、未編集文書の2回目の復旧で参照が切れた | 確認済みのサイト・画像保存先の対応を、復旧先、次の原本記述、Baseline、正式履歴、Checkpointへ引き継ぐ。原文は書き換えない |

これは試験の数だけの問題ではなかった。「保存値を選別する規則」を「復旧先を使える状態に構築する規則」の代わりにしていた。今後は、保存値の適用、安全な動作状態の構築、次の保存に必要な関係情報を分けて定義する。実行コードを持ち込まない原則は維持する。

製品の変換結果から期待値を作らず、導入済みの信頼できるTablePressが要求する設定キー、独立したURL・ハッシュ期待値、実際の利用操作と照合する。詳細は[構築方針の追記](recovery-construction-policy-20261111.md#rc11後の修正復旧先の動作条件と参照の継承未提出)を参照。

## 確認結果

修正に先立ち、新しい契約確認と実ブラウザ確認で、未変更rc.11の表のHTTP 500と、未編集Markdownの旧サイト参照を検出した。その後、隔離した3サイトと実S3の専用試験領域で以下を確認した。

| 確認 | 結果 |
|---|---|
| 旧Baselineを復旧→利用→一部編集・再保存→別サイトへ再復旧 | 成功。Baseline＋正式履歴（through 8）とCheckpoint経由を確認 |
| TablePressの利用 | 表示・検索・並べ替え・ページ送りが成功。保存されたカスタムスクリプトは実行されない |
| TablePressの独立した読み戻し | 別PHP要求で必須設定キー、セル、表示設定、対応値を照合し差分なし |
| 編集済み・未編集Markdown | 2回目の復旧後もリンク・画像URL・画像の実体が一致。原文のハッシュも一致 |
| 旧サイトからの独立 | ブラウザで旧サイトへの通信を遮断して成功。最終10チェック成功、旧サイトへの要求・スクリプトエラーなし |
| URL境界 | サイト内URL、似たホスト・パス、外部URL、ポート、クエリ、正規化で境界を越え得るパスを区別 |
| 契約確認 | 既存32件PASS、追加の参照境界・形式・旧reader試験PASS、PHP構文確認成功 |
| 原本・履歴の保全 | 試験対象の既存オブジェクトは復旧前後で不変。新規保存は専用試験領域のみ |

環境はWordPress 7.1.3、PHP 8.3.36、TablePress 3.4.1。復旧は製品処理をCLIから実行し、利用確認はChromiumで実施した。今回、管理画面の復旧ボタン操作を再検証したという意味ではない。終了後は試験サイトの保護・定期実行を停止し、処理待ちがないことを確認した。

Plugin Checkはエラー0・警告100件。比較対照のrc.11はエラー0・警告99件。増加1件は、`RecoveryRules.php`の配列内`meta_value`のJSONデコードを低速DB問い合わせとみなす静的警告で、該当行はDB問い合わせを行わない。残りは対照と同じ分類・件数。Plugin Checkの記録は最終URL境界ガード追加直前のソースに対するもの。そのガード追加後は参照契約と実ブラウザ確認を再実行した。新候補ZIPの確認完了とは扱わない。

## 互換性と利用上の注意

- 更新版は旧形式の保存データを読める。既存S3オブジェクトの移行・書換えは行わない。
- 新しい参照情報を必要とする保存には形式識別子を付ける。**その形式を含む復旧点は、更新版の復旧処理で使用する。** 未変更rc.11が読み取り時に明示的に拒否することを、独立プロセスと実S3で確認した。古い参照を黙って復元しないための扱いである。
- 過去に失われた参照元情報は本文から推測して補完しない。参照元は最大32組とし、不正・超過時は切り捨てず停止する。
- 今回の対象はサイト全体復旧。旧Markdown個別復旧の保証範囲を拡張するものではない。
- 実行ソフトウェアは管理者が信頼できる配布元から別途準備する。カスタム命令の原文を保存していることは、その命令を復旧先で実行することを意味しない。

## 再発検出と記録

`application-rules.php`で安全な必須値・正常な0/false/空欄・原本不変を確認し、`reference-context.php`と`reference-format.php`を既存CIへ追加した。旧readerとの比較は`reference-legacy-reader.php`、隔離実環境の読み戻しと利用は`tools/testing/table-runtime-readback.php`と`recovery-use-browser.cjs`で再実行できる。実行例は構築方針文書に記載する。

詳細ログは運用作業領域`release-readiness/rc11-runtime-fix-20261111/REPORT-ja.txt`および同領域の`owr-runtime-fix/`に保全。認証情報や実環境の原本値を含み得る生ログは公開リポジトリに同梱しない。

提出済みZIP SHA-256: `0fcbbac0a7e8dcadbbb5d5b247248a3c8081ceb1b4ee6c2771f7e19cc5233c1c`。
提出済みタグ`wporg-0.3.3-rc.11`のオブジェクト: `c247a62dc4569cbbea841399f1e0d3979a778998`。研究側の未コミット変更は別worktreeに保全する。

今回の2件を修正・確認したことと、すべての連携・任意の版や組合せの確認完了は区別する。新候補の梱包、導入・更新確認、公開判断は次の段階で行う。

## English summary

These main-branch changes are not included in the submitted rc.11 ZIP or tag. No new public ZIP or WordPress.org submission is made; rc.11 remains awaiting the reviewer response, not approved.

TablePress now receives an explicit safe empty custom-command value instead of a missing required setting. Archived executable settings remain in originals but are not executed. Markdown retains verified site/upload provenance across complete-site recovery and subsequent saves without rewriting document bytes. The structural correction is to define destination runtime requirements and next-generation provenance, rather than treating archive filtering alone as recovery construction.

Regression checks detected both defects before the fixes. Three isolated sites and real S3 verified recovery, browser use, partial editing, resaving, and a second recovery, including untouched Markdown and Checkpoints. Table interaction, independent readback, links and image bytes passed with earlier sites blocked. Existing originals/history and submitted rc.11 are preserved.

The updated reader accepts old data. New context-dependent originals and recovery points require the updated reader; unmodified rc.11 explicitly rejects them. Missing historical provenance is not guessed. This does not extend the legacy individual-Markdown recovery scope. Plugin Check recorded zero errors and 100 warnings (99 on rc.11); the additional warning concerns array processing, not a database query. That check preceded the final URL guard; reference and browser checks were rerun after the guard. Packaging and release qualification remain separate work.
