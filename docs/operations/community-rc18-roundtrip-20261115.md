# community rc.18 隔離復旧・再保存・再復旧 / Isolated recovery round trip

確認日：2026-11-15 JST。結果：以下の確認範囲でPASS。完了済み試験の記録であり、この記録作成のための本番・S3操作は行っていません。

## 対象と方法

community本番の2026-11-12の初回保存（through 0）と正式履歴1〜66を、提出済みrc.18で復旧しました。読取り専用経路でS3のVersionIdを固定して取得し、ハッシュ検証付きコピーを隔離環境へ提供しました。本番の書込み認証情報は渡していません。

2つの新規WordPressには信頼済み配布パッケージから必要なソフトウェアを別途導入・通常セットアップしました。内部Dockerネットワークで、公開ポート・本番マウントなし。メール・Cron・自動更新を停止し、資源上限を設定しました。復旧・保存は製品のPHP処理と通常のWordPressフック、表示は内部HTTPで確認しています。

- ZIP SHA-256: `eadc9ec4de01f06014414a9bb709b11905019e525fdbdc918f45d3626d2f2d97`
- 初回復旧：履歴66まで、投稿87件。確認用ページID130の本番での追記をHTTP表示で確認。
- 独立した試験用S3の空のprefixへ新しい初回保存を作成し、確認ページへ試験用追記を保存。
- 2つ目の準備済みサイトへ、試験側の初回保存＋履歴26までを再復旧。元の追記と試験用追記の両方が表示されました。

## 前回不足していた10件

前回のrc.16・履歴41までの復旧では、対象51パス中10パスに原本がありませんでした。今回のrc.18・履歴66までの復旧では、その10件すべての原本を取得でき、対象51パスの原本不足は0でした。

今回の復旧点には、本番rc.18で追加確定した添付一式の履歴が含まれます。古い復旧点の不足をバージョン更新だけで補完したという意味ではありません。以前の原本・履歴は書き換えていません。

- 公開12件：直接URLでHTTP 200。
- 保留39件：直接URLでHTTP 404。原本自体は非公開で保持。
- 再保存後と再復旧後で、51パスの内容ハッシュ・閲覧条件・公開配置状態が一致。

機械可読結果の `files: 12` は公開配置されたファイル数であり、原本が12件しか戻らなかった意味ではありません。`all_registered_files_recovered` は今回の対象51パスについての結果で、サイト外部の全資産への保証ではありません。

## 準備済み設定と復旧後の利用

各復旧先で異なる準備済み設定を用意し、初回復旧後・再保存後・再復旧後に照合しました。

- WP-Membersの準備済み版情報・form_tags・clone_menusを維持。
- TablePress全体設定を維持し、実TablePress APIで復旧した表を読込み。
- 選択テーマ・独自設定・追加CSS本文を維持。
- ウィジェット本体と配置を維持し、標準テキストウィジェットを描画。
- 対象投稿本文、ファイル内容と閲覧条件、会員限定3ページの設定が再保存後と再復旧後で一致。
- 復旧中のプラグイン/テーマファイル・有効化一覧は不変。install.php/uninstall.phpの新規読込みなし。通常セットアップ後にWP-Members初期化関数を呼ぶと失敗するガードを入れた状態で通過。
- 未完了保存・添付エラーなし。定期保存・自動削除はオフ。

適用規則による未適用項目は初回177、再復旧133として報告されました。全設定を無条件に適用したという意味ではなく、今回の確認結果は上記対象の復旧・利用と準備済み設定の維持についてのものです。

## 保全と確認範囲

元の本番S3の572版・10,863,133バイトは、取得前後のkey/version/ETag/size/latest一覧が一致しました。再保存は別の試験用S3だけに457版を新規作成し、再復旧前後の試験側版一覧も一致しました。試験側操作はPutObject 457、GetObject 1,593、ListObjectsV2 107、エラー0・削除操作なし。試験資産は保持し、専用コンテナ・ネットワーク・ボリュームは片付け済みです。

本番サイト、既存原本と履歴、提出済みZIP・タグは変更していません。実際のコンテンツ・会員情報・ファイル名・認証情報はこの公開記録に含めず、集計結果だけを掲載しています。

確認はブラウザの復旧ウィザード操作ではありません。全実会員のログイン、問い合わせ送信、外部メール配送、全テーマ/拡張ウィジェットの外観は今回の対象外です。会員限定条件は設定の一致を照合し、ファイルの直接アクセス制限はHTTPで確認しました。保留ファイルの会員向け配信機能を検証したものではありません。

[往復結果](../../evidence-public/community-rc18-roundtrip-20261115/summary.json) / [前回不足10件との照合](../../evidence-public/community-rc18-roundtrip-20261115/first-summary.json) / [元S3の保全](../../evidence-public/community-rc18-roundtrip-20261115/source-preservation.json) / [試験輸送・後片付け](../../evidence-public/community-rc18-roundtrip-20261115/transport-audit.json) / [本番更新・保存記録](community-rc18-20261115.md)

## English

The exact submitted rc.18 ZIP restored community's initial Baseline and formal history through 66 into a separately prepared WordPress. A new Baseline and an edited verification page were then saved to a fresh, isolated real-S3 prefix and recovered into a second prepared site through trial history 26. Both the original append and the isolated edit were visible over internal HTTP.

All 51 file paths in the checked recovery set had original bytes, including all ten missing in the earlier rc.16/history-41 check. This recovery includes newly confirmed attachment-bundle history; it does not retroactively repair old recovery points merely by updating software. Twelve public files returned HTTP 200; 39 held files returned 404 while retaining their bytes privately. File hashes, placement/access conditions, selected post content and three pages' membership settings matched across resave and second recovery.

Prepared WP-Members runtime/version settings, TablePress globals, the selected theme and its custom settings/Additional CSS, and widget configuration/layout survived. Actual table loading and text-widget rendering passed. Recovery did not change installed software or activation state, include installers, or call the guarded WP-Members initialization function.

The source's 572 S3 versions were unchanged. Only the separate trial prefix received 457 new versions, which were unchanged by second recovery. No production changes, source deletions, ZIP or tag changes were made. Trial containers/networks/volumes were removed; trial assets were retained.

These are product-function/hook and internal-HTTP checks, not browser wizard automation or a test of every real member login, external mail delivery, theme or extension widget. Membership rules were compared as settings; direct file access was tested over HTTP. Aggregate evidence is published without production content, member data or credentials. WordPress.org publication remains unapproved, awaiting the reviewer response.
