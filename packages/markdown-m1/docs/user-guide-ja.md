# 初めての導入 — 準備から保護開始まで

**版の区別：** 以下は申請済み0.3.1の導入手順です。開発版0.3.2-devでは[準備状況と利用条件の確認](setup-readiness-ja.md)を追加しています。申請済みZIPは変更していません。

[English](user-guide.md) · [更新する場合](install-update.md) · [復旧手順](#6-別のwordpressへ復旧する)

記事・画像・コメントや、対応する問い合わせ・会員情報などを保存し、攻撃で元サイトを使えなくなったときにも情報発信や利用者対応を再開できるように準備します。[守る対象とバックアップとの役割の違い](../RAADME-jp.md#攻撃の後もサイトを再開するために)を確認してください。まず **準備 → 保存先設定 → Baseline作成 → 保護開始の確認** の順に進めます。定期取得・保持・復旧は、初回確認が終わってから設定できます。

## 1. 自分の環境で使えるか確認する

まず、再開に必要な内容を決めます。投稿・固定ページ・画像・コメントに加え、問い合わせ・会員情報・表など、利用中の連携機能を確認してください。保存・復旧する内容と対象外の理由は[README](../RAADME-jp.md#残るもの復旧できるもの)にまとめています。連携プラグインを使う場合は[対応表](../RAADME-jp.md#supported-content-and-plugins)を確認してください。Markdownを使わないサイトにMarkdown Documentsの追加導入は不要です。

| 担当 | 初回に用意するもの |
|---|---|
| WordPress管理者 | 管理者ログイン、対応するコンテンツ・プラグインの確認、初期保存時に編集を止められる時間 |
| AWS担当者 | バージョニング有効のS3バケット、サイト専用prefix、保存用の権限。bucket・region・prefix・所有者の12桁アカウントIDを管理者へ渡す |
| サーバ担当者 | WordPress 6.4以上・PHP 8.1以上、InnoDB・ZipArchive・書込み可能な領域、WebのPHPから使えるAWS SDK標準認証、約7.5MBのZIPをアップロードできる設定 |

[具体的なAWS設定](aws-setup-ja.md)はEC2ロール構成を例にしています。EC2以外では、WebのPHPに標準認証を用意できるかサーバ担当者へ確認してください。プラグインにアクセスキーを入力する欄はありません。連携プラグインの要件も適用されます（確認済みCF7 6.2.3はPHP 8.3以上）。

## 2. AWSを準備し、プラグインを導入する

1. AWS担当者が[AWS設定](aws-setup-ja.md)に従って準備します。保存側は `source-no-delete` を選び、自動削除を使わずに始めます。
2. [rc.2リリース](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/releases/tag/wporg-0.3.1-rc.2)から **ozeki-resilience-0.3.1.zip** を取得します。`Source code (zip)` は導入用ではありません。照合用の `SHA256SUMS` も同じ場所にあります。
3. WordPressの **プラグイン → 新規プラグインを追加 → プラグインのアップロード** でZIPを選び、インストール・有効化します。旧版が入っている場合は[更新手順](install-update.md)へ進みます。
4. **ツール → Resilience** を開き、ページ下部の **Storage and optional scheduling settings** まで移動します。上部の状態表示・復旧操作は、保存先の設定後に使います。初回の未設定状態でS3履歴の読取りエラーが出た場合も、まず以下を設定してください。
5. 次の4項目を入力します。

| 画面の項目 | 入力する内容 |
|---|---|
| bucket | S3バケット名。`s3://` は付けない |
| region | バケットのリージョン。例：`ap-northeast-1` |
| prefix | このサイト専用の保存先。例：`sites/my-site/`（末尾 `/` を含む） |
| owner | バケット所有者の12桁AWSアカウントID |

6. **Protect supported operations**、GFSの **Enabled**、自動削除はオフのままにします。製品から削除ロックを要求しない構成では **Optional S3 deletion protection in days** を `0` にして、**Save settings** を押します。

設定の保存後、次のBaseline作成で実際の保存を確認します。

## 3. 最初のBaselineを作る

1. 保存元の内容が信頼できることを確認し、編集を一時停止します。Markdown文書を使う場合は、対応するMarkdown Documentsを有効にしておきます。
2. 同じ画面の **Site-wide recovery — primary workflow** で **I trust the whole current site and have paused editing.** にチェックし、**Create complete initial snapshot** を押します。
3. **Checkpoint** の選択欄に `administrator_initial` と今回の作成日時が現れることを確認します。これが最初のBaselineです（新規prefixでは `history 0`）。エラーの場合はその内容を控え、[困ったとき](#困ったとき)を参照してください。
4. ページ下部の **Protect supported operations (one writer per prefix)** をオンにし、**Save settings** を押します。編集を再開できます。

Baselineは現在の対応範囲を初めて保存する操作です。その後のCheckpointは保存済みの資源と確定履歴から作ります。テーマなど追跡対象外の変更後は、[変更別の対応表](start-here-ja.md)を確認してください。

## 4. 保護開始を確認する

通常の投稿編集画面で、識別しやすいタイトルと公開してよい内容の確認用投稿を一件作り、**公開（Publish）** します。新規投稿の下書き保存だけでは追跡は始まりません。その後 **ツール → Resilience → Save protection status** を開きます。

- **Protection setting: Enabled** になっている。
- **Last confirmed sequence** と確定時刻が更新され、下部の **Confirmed formal history / Individual recovery** 一覧に今回の投稿名と関連情報の履歴がある。最新の **Title** は投稿名ではなく `Article details #7` のようになる場合があります。一覧の確認だけでよく、復旧ボタンは押しません。
- **Locally pending operations: 0** で、今回の保存エラーが残っていない。

この3点を確認できれば、初期設定と投稿保存の確認は完了です。続いて、自分のサイトで使う問い合わせ・会員機能なども確認します。対象外の資産のバックアップは引き続き運用してください。

### 困ったとき

| 状況 | 次にすること |
|---|---|
| ZIPをアップロードできない | サーバ担当者へPHPのアップロード・POST上限、Webサーバの要求サイズ上限、アップロード先（uploads）の書込み権限の確認を依頼する |
| 設定後も認証エラー／AccessDenied | [AWS設定](aws-setup-ja.md)の設定表・PHPの認証・対象prefixの権限を担当者と確認する |
| 未確定操作が残る | 原因を解消して **Resume history**。[保存再開の詳細](save-resume.md)を参照 |
| エラーの意味が分からない | 操作名とエラーを控えて問い合わせる。認証情報や非公開コンテンツは載せない |

元サイト喪失後の復旧に使えるのは確定済みの履歴です。キュー登録前に保存が失敗した場合は、原因解消後に通常編集画面から再保存します。

## 5. Checkpointの日時・保持を設定する

画面のタイムゾーンを確認します。例えば週次は日曜02:00・2週間、月次は1日02:00・3か月、年次は1月1日02:00・1年と設定できます。保存したい期間と利用量に合わせて設定してください。日付と時刻が重なると一式を一回作って複数区分を付け、一つでも有効な区分があれば残します。更新がなくても独立一式を取得します。同じサーバの複数サイトでは時刻をずらせます。

**Detailed history recovery window in days** は詳細履歴を残す期間と境界の復旧点を決めます。`0` は最新Checkpointと必要な後続履歴であり、全資源を消す意味ではありません。過去のGFS基点は途中の全履歴がなくても残せます。**Optional S3 deletion protection** は別のAWS削除ロックで、`0` に変えても既存ロックは解除されません。[GFS詳細](gfs-checkpoints-ja.md)。

設定後は **Next complete-site Checkpoint (UTC)** を確認します。サーバ担当者と定期的な起動機会を用意してください。WP-Cronは厳密な時計ではありません。実行後は今回の成功・失敗と次回予約を確認します。取得失敗時には削除を行わず、前回の削除成功記録が過去の時刻付きで残る場合があります。

最初は削除しない **Preview complete-site retention** を使い、残す点・必要資源・候補・保留理由を見ます。復旧確認後に[AWSの削除用ポリシー](aws-setup-ja.md)へ変更すると、確認チェックと **Delete expired complete-site resources** で候補を削除できます。定期削除は別のチェックボックスで、定期取得成功後だけ動きます。任意の保持中復旧点を強制削除する機能や初期化ボタンではありません。S3 Lifecycleの経過日数による削除を代わりに設定しないでください。

## 6. 別のWordPressへ復旧する

保存した記事・画像・問い合わせなどを別のWordPressへ戻し、情報発信や利用者対応を再開します。元サイトが停止していても、S3に残した内容から復旧できます。攻撃への対応では、信頼できる初期保存（Baseline）と、戻す変更の範囲を選びます。管理者ログインや外部サービスの接続は復旧先で用意し、外部公開を制限した状態で確認してから再開します。

1. クリーンな専用復旧先に、保存時と同じWordPress系列の同じか新しい修正版（例：7.1.2から7.1.3）、製品ZIP、必要なプラグインを用意し、管理者ログインを確認します。WP-Membersが承認を要求する場合、復旧先管理者を別途有効化します。元管理者の認証情報は復旧しません。他用途で稼働中のサイトを復旧先にしません。
2. AWS認証には **recovery-read-only** を使い、**Storage and optional scheduling settings** で元と同じbucket・region・prefix・ownerを入力し、**Save settings** を押します。保護・定期取得・削除はすべてオフ。復旧先でBaselineを作りません。未解決のローカル未確定操作がない復旧環境を用意します。
3. **Site-wide recovery — primary workflow** の **Create complete Checkpoint** の下、**Formal history end** と並ぶ **Checkpoint** 欄でBaseline（`administrator_initial`）またはCheckpointを選び、**Formal history end** で適用終了番号を指定します。その番号を含めて復旧します。基点の `through` と同じ番号なら基点だけ、後の番号なら間の必要な正式履歴・資源が必要です。番号は必ずしも編集一回の境界ではありません。例えば本文が1、関連情報が2なら、その編集全体を採用するには2まで選びます。
4. 復旧先の置換を確認して **Restore complete site** を実行します。復旧先コンテンツを置換します。S3の復旧資源は残します。
5. **Last site-wide recovery result** の成功・失敗、使用Checkpoint、要求・適用履歴番号を確認します。**Preserved in S3 — not automatically applied** の未適用項目も確認します。投稿件数は過去版等を含み、ファイル書込み0件は既存の同一ファイルを再利用した場合にも表示されます。調査には詳細JSONを残します。エラー時は表示内容と復旧先の状態を確認し、原因を解消してから再実行します。
6. 復旧先で用意した管理者で再ログインし、代表的な本文・著者表示・画像・リンクと必要な会員制限・表・フォームの動作を確認します。サイト名が元の名前に変わっても、復旧先URLで確認を続けます。元の `publish` はそのまま再現します。DNS・ネットワーク公開は管理者の別判断であり、メール再送は復旧機能に含めません。

[詳細な復旧仕様](site-snapshot-ja.md) · [適用規則と未適用情報](application-rules.md)

## 7. 問い合わせ

保存・復旧の対象は[README](../RAADME-jp.md#残るもの復旧できるもの)、設定エラーへの対処は[困ったとき](#困ったとき)を参照してください。問い合わせには版・タグ、操作、エラー、確定番号、必要な環境版を添え、秘密鍵・トークン・個人情報・非公開原本は除いてください。

[今回の候補確認](wordpress-org-candidate.md)と[既存の受入記録](recovery-readiness-ja.md)を参照してください。後者にはサンプル単独IAM受入を記録しており、それ以前の未検証という記載を更新しています。
