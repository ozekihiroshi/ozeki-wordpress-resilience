# 独立した初期スナップショットとCheckpoint

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

この文書は補助的な資産単位の経路です。本文・画像・テーマ・メニュー・関連情報を含む復旧には、基本操作の[サイト全体の復旧](site-snapshot-ja.md)を使用してください。資産単位のボタン名は Restore assets from Checkpoint + later history です。信頼済み基準状態とS3正式履歴の確定操作までを復旧対象とし、元サーバ喪失時の未確定操作は採用しません。新規記事なら含めず、更新なら前の確定版を復旧します。

初期スナップショットとCheckpointは、同じ生成処理・完全ファイル形式・復旧処理を使います。初期だけは管理者が信頼すると判断した公開済みMarkdown文書を入力とし、取得中は編集を止めます。以後は前のスナップショットとS3の正式履歴を入力とし、稼働中WordPressから再採取しません。対象はM1のMarkdown文書・属性・文書間リンクであり、WordPressの全機能ではありません。

各セットに全対象のsource.md、metadata.json、再開用plan.json、最後に確定するmanifest.jsonを保存します。変更していない文書もコピーします。目録は同一セット内の固定Version IDとハッシュだけを参照します。読み戻し確認後に目録を確定し、途中失敗は一覧に採用しません。同じ計画・保持期限で再開します。初期登録の再試行は可能ですが、既存の初期状態を別内容で置き換えません。

通常更新は対象文書の完全原文と成功履歴だけを保存します。復旧は選択したCheckpointとそれ以降の連続する履歴を使います。以前の原本・履歴・スナップショットは不要です。後続履歴の欠落やファイルの不一致は復旧を中止します。原文と公開状態を保持し、表示時の文書間リンクを復旧先へ対応付けます。

## 操作

ツール → Resilienceで保存先、通常保存の保護、Checkpoint間隔（日数）を設定します。0は手動で、毎日固定ではありません。WP-Cronにはアクセス又は既存の定期実行が必要です。初期取得は未使用の履歴範囲で管理者の確認を必要とします。すでに正式履歴があるM1環境は、S3履歴から最初のCheckpointを作れます。履歴保存待ちは先に解消します。変更がない場合は既存の完全セットを維持します。

## 保持期間による自動削除・手動削除

Object Lockの削除禁止期限と、復旧点を何日残すかは別設定です。最新の検証済み完全Checkpointは必ず残します。設定期間内の他のCheckpointも残し、最も古い保持対象から後の全成功履歴と、その完全原本を保護します。単なる期限切れでは、復旧に必要なものを削除しません。

管理画面の「Preview expired versions」で対象を確認し、「Delete previewed versions」で確定します。自動削除も同じ計算を使用します。復旧点の保持期間は初期値90日、0は最新基点と後続履歴を維持する設定です。Checkpoint作成間隔とは別です。自動削除は初期状態で無効。明示的に有効化した場合だけ、設定間隔のCheckpoint確認成功後に実行します。更新だけで自動的に有効にはなりません。

残す完全ファイル、後続履歴の連続性、S3の固定Version ID、保持期限・Legal Holdを検査します。削除直前に同じ書込みロックの下で再検査し、プレビュー後に変化があれば拒否します。正式履歴保存待ちは先に解消します。候補に有効な保持ロックが1件でもあれば削除開始前に全体を停止します。検査後に追加された制限はS3側で強制され、拒否・応答不明が起きた時点で残りの削除を止めて報告します。保持解除・迂回権限は使いません。

対象は既知形式の期限切れ旧スナップショット、保持基点までの履歴、参照されない古い原本です。古い未採用原本も未確定保存がない場合だけ対象です。未知のパスは残し、同一キーの複数版やDelete Markerは自動処理せず停止します。削除は必ずVersion IDを指定します。旧目録・履歴を先に取り除き、続いて不要データを削除します。途中停止後はS3から再プレビューでき、ローカル削除台帳なしで残りを判断します。単一書込み元の前提を維持し、別のLifecycleや外部処理が必要資産を独自削除しない構成とします。

## 権限・確認範囲

通常の読取りに加え、対象範囲のListBucketVersions、DeleteObjectVersion、バケットのGetBucketObjectLockConfiguration、Object Lock使用時はGetObjectRetention/GetObjectLegalHoldが必要です。権限不足を無視して進めません。現行IAMは変更していません。[AWS API権限表](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html)、[HEADでの保持情報表示条件](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html)を参照。

削除候補はメモリ内の版管理S3代替と、既存dm Docker上の実WordPress再登録で確認しました。保持期間、最新基点・後続履歴の保護、ロック、古いプレビュー、途中停止・再開、複数版の拒否を検証しています。定期コールバックの直接試験と実時刻での定期実行は区別します。実S3資産の削除やAWS側削除制御の実証はしていません。稼働中の保存側・復旧側プラグインには削除機能を配置しておらず、先に設定した定期Checkpoint確認を変更していません。
