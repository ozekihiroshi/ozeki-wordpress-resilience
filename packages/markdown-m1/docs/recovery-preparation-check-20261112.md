# Recovery preparation checks / 復旧前の準備確認

2026-11-12. GitHub source update after submitted rc.13. No release ZIP, tag or production installation was changed.

## Change

Before replacing destination content, the selected Checkpoint and confirmed-history end can be checked with **Check / recheck recovery preparation**. The screen shows required/current WordPress and plugin versions, plugin activation, the source language pack, separate-destination/protection state, and existing local prerequisites. It links to language settings and Plugins, explains the next action in English/Japanese, and retains the selected point/history for the subsequent restore form.

The check reads the existing fixed originals and replays the selected history without installing data. The actual restore independently runs the same requirement checks after loading/replay and before staging, uploads, users, options or content replacement. A cached display result never authorizes restoration. Preparation results are diagnostic options, separate from site content.

Missing language packs are identified before WordPress rejects the language setting. Standard language settings provide the official installation path; no custom software installer was added. Uninstalled plugin paths no longer generate file-read warnings during inventory checks.

Existing original/history formats are unchanged. The language is read from the stored content, so earlier recovery points are covered without rewriting S3. Guides identify this source-only addition and retain manual instructions for unchanged submitted rc.13.

## Verification

Disposable WordPress 7.1.4 / PHP 8.3.36 on dm, using the dedicated read-only recovery role. Official software was installed separately; the rc.13 archive was extracted and current source files overlaid only in the disposable installation. No published ports; Cron, external WordPress HTTP and mail disabled. Containers, network, volume and temporary credential file were removed afterwards.

- PHP syntax checks passed.
- `tests/recovery-preparation.php` passed English/Japanese checks for English without a pack, missing/invalid languages, missing WordPress/plugin requirements and the shared restore guard.
- Authenticated HTTP tests exercised the new nonce-protected check action in English/Japanese with Japanese missing and Flamingo inactive. Both missing conditions and next actions appeared, with language/plugin settings links.
- Direct restore attempts in both languages reported the missing conditions before changing destination content, users, language/configuration or staging files.
- After installing the official Japanese pack and activating Flamingo, both languages' HTTP rechecks reported all tested requirements ready.
- Restoration from the existing production Baseline through confirmed history 5 succeeded. A fresh WordPress request and public HTTP response matched the test article's updated body exactly. Destination software and administrator were preserved.
- All 278 source S3 versions remained unchanged. No S3 writes/deletes or production mutations were performed.
- Submitted rc.13 SHA-256 remains `34eee728e5c6d78f6e8368256d60676a0df7085e8a35ed343f787afd2898c2b8`.

[Machine-readable results](recovery-preparation-check-20261112.json).

## 日本語

復旧ポイントと履歴の終点を選び、復旧前に不足条件と次の操作を確認・再確認できるようにした。言語設定・プラグイン画面へのリンクを設け、日英で案内する。実際の復旧でも同じ判定を繰り返し、不足があればデータ変更前に止める。原本形式は変えず、過去の保存からも言語設定を読み取る。

隔離環境で日本語言語パック不足とFlamingo未有効の案内、変更前の停止、導入後の再確認と履歴5までの復旧を確認した。確認記事の追記は本文・HTTP表示とも一致した。本番・既存S3資産・提出済みZIP・タグは変更していない。

日英ガイドから、復旧用IAMロールの設定と完全な読取り専用JSONへ直接案内する。保存用ロールへ誤って追加しない説明も明示した。IAMとソフトウェアの準備、確認、復旧という順序を揃えている。
