# community rc.23：新しい初回保存と隔離往復確認 / New Baseline and isolated round trip

確認日：2026-11-28 JST。完了した作業の運用記録です。この文書反映では本番サイト・S3を操作していません。rc.23は既存のWordPress.org申請へ提出済みで、審査担当者の回答待ちです。公開承認済みではありません。

## 対象と方法

- 本番で稼働中のrc.23から、新しい初回保存を追加しました。既存の保存を置き換える操作ではありません。
- 同一ZIPを使用。SHA-256：`062a8c423c4ecca40b0075dc65d4d783e27ed884024fc66c5933f341e7de5447`。タグ：`wporg-0.3.3-rc.23`、対応ソース：`ebac41426b3dd09c9b3c93c2fedddabcfb841618`。
- dmに公開ポートのないDockerネットワーク、独立DB、復旧先2つを用意しました。WordPress 7.1.5・日本語パック・保存時と同じテーマと対応プラグインを公式配布元から事前導入しました。
- Markdown Documentsは本番に入っていた0.1.2で確認しています。0.1.3での結果へ読み替えません。本番の同プラグインは更新していません。
- 本番S3は仲介処理で読取り専用に制限。再保存は新規の試験専用prefixへ、暗号化・新規作成限定で実行しました。認証情報を復旧先へ渡していません。
- 保存・復旧は製品APIとWordPressの通常フック、表示・ログインは内部HTTPと描画処理で確認しました。試験側の外部メール・Cron・自動更新を停止しています。

## 結果

| 確認 | 結果 |
|---|---|
| 本番の新しい初回保存 | 正式履歴81までを含む438リソースを保存し、固定版を読み戻して検証。分割データの再構成後は58ファイル |
| 最初の復旧 | 115投稿レコード。確認用ページの既存の追記とHTTP表示を確認 |
| 添付ファイル | 51件すべて原本あり。公開12件は直接URLでHTTP 200、非公開保全39件はHTTP 404 |
| 会員の利用 | 隔離側の確認用購読者で実HTTPログイン。会員ページ2件をHTTP 200で確認し、非会員時の表示との差異も確認 |
| その他の利用 | Markdown埋込み3文書、TablePressモデルからの表読取り、ウィジェット描画を確認 |
| 再保存 | 復旧先から試験専用S3へ393リソースの初回保存。確認用ページに隔離側だけの追記を通常保存 |
| 正式履歴 | 試験側で4件が確定（page、owr_native、owr_acf 2件） |
| 再復旧 | 別の復旧先に試験履歴4までを反映。追記、会員ログイン・閲覧、Markdown埋込みを再確認 |
| 往復の一致 | 比較対象の投稿内容、51件のファイル内容・閲覧条件、ページの会員閲覧条件のハッシュが一致 |
| 準備済み設定 | WP-Members、TablePress、テーマ、ウィジェットの設定を両復旧後・再保存後に維持 |
| ソフトウェア | 両復旧でファイルハッシュ・有効プラグインが不変。復旧中のinstall.php / uninstall.phpの追加読込みなし |
| 保存状態 | 観測時点で保全待ち・添付の未処理・添付エラーなし |

本番の初回保存自体が履歴81までの状態を含みます。最初の復旧で81件を後続履歴として追加再生したわけではありません。一方、再復旧では試験用初回保存（through=0）に試験履歴4までを反映しました。本番履歴を巻き戻した意味ではありません。

## メモリ条件と試験前提の調整

- 最初のCLI実行はPHPメモリ上限128MBでメモリ不足となりました。通常管理画面の `WP_MAX_MEMORY_LIMIT=256M` を確認し、新規の隔離環境でCLIも256MBに揃えて完了しました。製品コードの変更や上書き補正はしていません。
- この結果は「この復旧セットが256MB条件で完了した」という確認です。128MBでの完了や、任意の規模に256MBで足りることは確認していません。管理画面で復旧ボタンを操作した試験とも区別します。
- 本番の登録ユーザーは管理者のみで、購読者は未登録でした。会員の欠落ではありません。隔離側だけに確認用会員を作り、その会員の再保存・再復旧後のログインも確認しました。
- HTTPクライアントが通常の301転送を追わず停止した点は、転送をたどる設定に直して確認しました。製品側の不具合修正ではありません。

## 保全と確認範囲

- 本番のコンテンツ各表、設定、正式履歴のハッシュは初回保存前後と最終確認で一致しました。新しい初回保存の登録を確認し、保護オン・定期保存オフ・自動削除オフを維持しています。
- 正常往復の仲介記録では本番S3の読取り686操作、変更操作0件。410件の作成操作は新規の試験prefixだけです。既存S3の全版を再列挙した比較とは区別します。
- 試験資産・原本・履歴は削除していません。今回作成したDockerコンテナ・ネットワーク・ボリュームは終了・除去し、既存dmサービスの継続稼働を確認しました。
- 最初の復旧で未適用345件、再復旧で140件を記録しています。今回は理由別の再分類・解消はしていません。全設定の完全再現や未適用0件という評価ではありません。
- 全編集画面のブラウザ操作、実在する本番会員のログイン、問い合わせ送信・メール配送、あらゆるプラグインの表示経路は今回の確認範囲外です。上記の件数と一致は、この復旧セットについての結果です。
- 本番の既存コンテンツ・既存原本と履歴・提出済みZIP・タグを保全しました。今回の記録反映ではコード・本番・S3・ZIP・タグを変更せず、申請やメール返信も行っていません。

[公開用の集計結果](../../evidence-public/community-rc23-roundtrip-20261128/summary.json)。原文を含む試験記録はdmの非公開領域（0700）に保持し、本文・会員情報・認証情報・S3保存先詳細は公開していません。

## English

On November 28, 2026, the exact rc.23 ZIP created a new production Baseline containing the state through formal history 81. All 438 stored resources were read back at fixed versions; reassembly produced 58 files. This Baseline already includes history 81, so the first recovery did not replay 81 additional records.

Two isolated Docker destinations on dm were prepared with WordPress 7.1.5, the official Japanese language pack, and trusted matching software. Markdown Documents was 0.1.2, matching production; this is not evidence for 0.1.3. Production S3 access was read-only through a restricted broker. New encrypted, create-only writes were limited to a fresh trial prefix, without transferring credentials to WordPress.

The first recovery restored 115 post records and the verification-page append. All 51 file originals were available: 12 public files returned HTTP 200, while 39 privately held files returned HTTP 404 at direct URLs. A test subscriber could log in over HTTP and access two member pages with different guest output. Three Markdown embeds, table-model reads and widget rendering were checked.

A 393-resource trial Baseline and a normal page edit were saved to real S3. Four trial records were confirmed (page, native state and two ACF records). The second destination recovered through trial history 4. The append, member login/access and Markdown embeds passed again. Selected post content, file bytes/access states and page restrictions matched. Prepared destination settings and software files remained unchanged; no additional install.php or uninstall.php was included during recovery. No pending saves or attachment errors were observed.

The initial CLI attempt exhausted its 128MB limit. A fresh environment completed at 256MB, matching the observed administrative `WP_MAX_MEMORY_LIMIT`. This is neither a 128MB acceptance nor a claim that 256MB suffices for every site, and recovery itself was API-driven, not a browser-button test. Production had no subscribers; only an isolated test subscriber was created and subsequently preserved/recovered. The HTTP client was also corrected to follow ordinary 301 redirects. Product code was not patched.

Production content, configuration and formal history hashes remained unchanged. Protection stayed enabled; scheduled saving and automatic deletion stayed disabled. The successful transport log recorded 686 read-only production operations and zero production mutations; all 410 creates were in the new trial prefix. This is not an inventory comparison of every existing S3 version. Owned trial infrastructure was removed, while S3 assets and private evidence were retained.

There were 345 non-applied entries in the first recovery and 140 in the second; their reasons were not reclassified in this task. Full browser-editor coverage, real production-member credentials, inquiry/mail delivery and arbitrary plugin display paths were not tested. This documentation-only follow-up publishes aggregates, not private content or storage identifiers. Production, existing assets/history, submitted ZIPs and tags remain unchanged. rc.23 is submitted and awaiting the review team's response, not approved for publication.
