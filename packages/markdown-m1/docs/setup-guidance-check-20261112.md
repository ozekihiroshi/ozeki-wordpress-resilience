# Initial protection guidance / 初回の保護開始案内

2026-11-12. Source-only UI change after submitted 0.3.3 rc.13; not installed on production or included in a new release ZIP.

The protection checkbox now explains the existing setup order: leave protection off while saving settings, check storage, complete the first save and verified read-back, then enable protection. English and Japanese follow the administrator's locale. The explanation is connected to the checkbox with `aria-describedby` and is absent in recovery mode. Existing protection settings are not changed.

The bucket input uses a 63-character width with a 100% maximum and border-box sizing, allowing long names while limiting the input to its container. Other fields and configuration behavior are unchanged.

## Verification

On dm's dedicated rootless Docker environment, a new WordPress 7.1.3 / PHP 8.3.36 fixture used an internal-only network, no AWS credentials, disabled Cron and blocked external WordPress HTTP. Submitted rc.13 was extracted into a disposable directory; only `Plugin.php` and `AdminText.php` were overlaid there. No archive was rebuilt or modified.

- PHP syntax checks passed for both changed files.
- Actual authenticated admin HTTP requests passed six cases: English/Japanese, each with source protection off, source protection on, and recovery mode.
- Correct-language guidance, checkbox/help association, full bucket value and width attributes were checked. Recovery mode has no protection checkbox or initial-protection help.
- Rendering preserved stored configuration and the existing protection checkbox state.
- Fixture containers, network and volume were removed after the checks.
- No S3 save or recovery was executed; this validates the changed display, not storage readiness. Responsive sizing was checked in the emitted markup, not a mobile-browser screenshot.

The first runner attempt used a historical admin-page slug and received HTTP 403. Correcting the runner to the current `page=ozeki-resilience` route resolved it; no product change was needed.

[Machine-readable results](setup-guidance-check-20261112.json).

## 日本語

「保護を開始する」の直下に、初回はオフで設定保存し、保存先確認と最初の保存・読み戻しの成功後にオンにする案内を追加した。日英は管理者の言語に合わせる。バケット名欄を広げ、狭い画面では親要素の幅を上限にする指定を加えた。設定値や保護開始の動作は変更していない。

本番とは別の使い捨てWordPressで、ログインした管理画面の日英6ケースを確認。設定保持、チェック状態、案内の表示対象、入力値と幅指定を確認した。実S3の保存・復旧やモバイルブラウザーでの目視確認は今回の対象ではない。

本番サイト、提出済みrc.13 ZIP、既存タグは変更していない。新しい公開ZIPは作成していない。
