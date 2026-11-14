# 閲覧条件の実S3確認・取り込み記録（2026-11-14）

`fb3c3e3`の製品ソース22ファイルを最終確認し、実S3を使った隔離環境で保存・復旧・再保存・再復旧と互換性を確認した。製品コードへの追加修正は不要だった。試験先の全ソースのSHA-256は取り込み対象と一致した。結果の[構造化要約](media-access-live-verification.json)も保存した。

## 確認環境

communityホスト上に新しいWordPress 3サイト、専用DB、専用ボリューム・ネットワークを作成した。既存の本番コンテナ・DB・uploads・設定には接続していない。外部公開ポートなし、メール・Cron・WordPressの外向きHTTPは停止。WordPress 7.1.3 / PHP 8.3.31 / WP-Membersを使用した。

AWS SDKの通常の認証・通信で、既存の試験用S3バケット内に新しいランダムな接頭辞を作成した。開始時に空であることを確認し、試験の書き込みはその領域だけに限定した。本番バケット、既存原本・正式履歴、IAM設定は変更していない。S3の代替ハンドラーは使用していない。

## 結果

| ケース | 復旧後の利用・再保存・再復旧 |
| --- | --- |
| 初回保存後に公開画像を追加 | 画像HTTP200、原本SHA-256一致、追記も二度目の復旧へ反映 |
| 既存画像の制限だけ変更 | 条件だけの正式履歴を確認。画像HTTP404、保留原本SHA-256一致、記事の編集・再保存・再復旧が成功 |
| 初回保存後に制限付き画像を追加 | 公開配置せず原本を保持。再保存・再復旧でも画像HTTP404と原本一致を維持 |
| WP-Membersのページ制限だけ変更 | 非会員に本文非表示、会員に表示。画像HTTP200を維持し、再保存・再復旧が成功 |

通常4ケースは、固定した試験画像のハッシュ、匿名・会員の実HTTP表示、本文追記、ファイルの有無、未確定履歴の有無を独立した判定処理で照合し、すべて合格した。

## 互換性

旧版main `054d5a2`の実コードに切り替え、実S3へ旧形式のBaselineと日常履歴を新規作成した。新版を用意した空の専用DBへ復旧し、閲覧条件が記録されていない旧画像は公開せず保留することを確認した。その状態で別の保存先へBaseline作成・記事の追記保存を行い、さらに別のサイトへ復旧しても、本文追記・原本ハッシュ・保留状態が一致した。初回保存済み画像と、後から履歴に追加された画像の双方で確認した。

逆方向は、実際の旧版コードが実S3上の新形式原本と新形式Snapshotの双方を拒否した。形式番号を模倣した判定だけではない。

各復旧の前後でS3のオブジェクト版一覧（キー・VersionId・ETag・サイズ・最新版状態）が一致した。新しい試験領域に記録された569版は保持したままにしており、削除はしていない。

## 取り込みと保全

前回の共通単体確認35件と[隔離確認結果](media-access-verification-20261114.md)に加え、今回の実S3確認を取り込み根拠とした。日英の利用案内と互換性説明も維持し、未配布であることが分かるよう文書を整えた。

本番サイト、研究ブランチの未コミット変更、提出済みrc.14 ZIPと既存タグは保全した。rc.14 ZIPのSHA-256は `453acc6930d57da11da72eaba5adf9c386d0d79aa179cfd15b12b82ad0ba5a2a` のまま。新しい公開用ZIP・タグの作成、WordPress.orgへの送信は行わない。

終了後、今回作成した4コンテナと専用ボリューム・ネットワークだけを削除した。試験の原本と結果は保持している。ローカル証跡は `D:/workspace/wp-rescue/release-readiness/media-access-live-20261114/`、再実行手順は `tests/media-access/run-live.py` と同ディレクトリのREADMEを参照。

---

The reviewed product source (`fb3c3e3`, 22 matching source files) passed a real-S3 trial using three isolated WordPress sites. Public media, attachment-only restriction changes, newly restricted media, and WP-Members page-only restrictions all passed recovery, use, resave and a second recovery. Protected/unknown files remained unserved while their exact bytes survived.

The actual old writer (`054d5a2`) created legacy Baselines and daily history in a fresh S3 scope. The new reader recovered and preserved their unknown file conditions across another generation. The actual old reader rejected both new original and snapshot formats. S3 version inventories were unchanged during recovery; 569 newly created test versions were retained.

Production, existing originals/history, research changes, submitted rc.14 and existing tags were preserved. This verification supports merging the unreleased change; it is not a new ZIP release or a WordPress.org submission.
