=== Ozeki WordPress Resilience ===
Requires PHP: 8.1
Stable tag: 0.1.0-alpha.5
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Reconstruction preview: administration screens; explicit external kit required for protected editing and recovery.

== Description ==
開発・評価版です。管理画面から通知先・対象警報を設定し、外部処理の状態を確認します。
インストールだけではバックアップ・署名・復元・通知配送・監視は開始しません。
外部ツールと独立した署名運用は別途必要です。完成したサイト保護製品ではありません。

== Installation ==
1. WordPress管理画面の「プラグイン → 新規プラグインを追加 → プラグインのアップロード」で、このZIPを選びます。
2. 「今すぐインストール」「プラグインを有効化」を選びます。
3. 「Resilience → 通知」を開きます。外部連携前の状態未取得は想定どおりです。
4. 通知キー・AWS資格情報・署名秘密鍵を管理画面へ入力しないでください。接続設定名は外部担当者が用意する参照名です。

== Stopping ==
プラグイン一覧から「無効化」します。設定は保持されます。
無効化しても外部ジョブや監視・通知は停止しません。外部側は専用の手順で停止します。
削除時の設定自動消去は実装していません。既存設定の消去は別途管理者が判断します。

== Changelog ==
= 0.1.0-alpha.5 =
初回インストール用開発候補。通知設定、外部状態表示、テスト送信要求。
