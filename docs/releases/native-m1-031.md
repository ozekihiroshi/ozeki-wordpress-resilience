# 0.3.1 independent product: native content and media review

## Scope and architecture

This cumulative change introduces `packages/markdown-m1`, independently of the
preserved root 0.2.0 research plugin. A WordPress plugin and S3 are the runtime;
Markdown Documents is required for Markdown content. No research worker, SSH
signer, custom body editor or standing recovery server is required.

Complete Markdown/HTML originals are saved before protected WordPress writes.
Only verified successful operations enter S3 history. Pending formal history
can be resumed; loss of the source before confirmation is persisted does not
prove the last operation successful. This is not a distributed atomic commit.
One writer per prefix is required.

Pages/Posts publication, updates, trash/untrash and referenced local image
addition/replacement use this path. Image originals are saved before registration;
successful article versions bind originals, generated sizes and attachment data.
Whole-site recovery uses a complete baseline and subsequent S3 history. It preserves
publication state and rebases local links. Destination replacement is explicit.
The individual-document restore control is not equivalent to whole-site/media
recovery; use the complete-site path for native pages with images and ID relations.

Initial/independent Checkpoint and optional cleanup code are also included in
the cumulative package. Wall-clock periodic acceptance and live-S3 deletion are
deferred, not claimed complete; cleanup is disabled by default.

## Validated ZIP

`release-candidates/20261024-native/ozeki-wordpress-resilience-0.3.1-native-final.zip`

SHA-256: `04bf1316e9ec75bf4eaf39054797c2b32ce3ab6054836568f36a2f8ea265603b`

The ZIP includes current product code, English/Japanese READMEs, specifications
and the existing AWS SDK. It excludes test tools and authentication helpers.
The source builder was corrected during review to include specifications as the
validated ZIP already does. This tool correction does not change product bytes.
This PR is not a GitHub Release or deployment authorization.

## Evidence and acceptance

- Existing AWS source/recovery hosts, standard SDK EC2-role authentication.
- Standard editor new Page/Post publication and image replacement: histories19–22.
- Actual browser file chooser uploads, addition/replacement: histories23–24.
- Chrome visual insertion and Replace/media-library controls, without HTML/code
  editor input: histories25–26. Both versions restored from the same baseline
  plus history; image SHA-256 and article content matched.
- Final ZIP fresh installation and update from the prior
  `0.3.1-checkpoint-sdk-fix` package used separate directories and table prefixes
  in the existing recovery container. Real WordPress activation APIs were used;
  browser ZIP-upload installation was not tested in this run.
- Settings, generated content, stable asset identity and recorded restore result
  survived replacement. All26 S3 formal-history entries remained unchanged.
- Both final-ZIP installations restored from S3 only through26; four trial
  Page/Post records matched body/state and referenced image hashes. No source DB.
- Existing39 source records and scheduling configuration remained unchanged.
- Prior generated failure tests reject S3 image-save failure and unverified
  WordPress application without adopting failed versions into formal history.

## Limits and problem classification

No guarantee for arbitrary plugin metadata, taxonomy changes, featured-image
updates, unused media entries, external/CDN resources, third-party binary
overwrite tools, permanent deletion, scheduled publication or all dynamic blocks.
Native editing uses WordPress concurrency controls; only the Markdown editor
has the additional Resilience stale-form token. Source text5MiB; image files32MiB.
Process-kill rollback during whole-site replacement is not accepted as complete.
External mail/authentication services and source administrator credentials are
not cloned. This is manually invoked reconstruction, not automatic synchronization.

- **Browser/environment:** in-app browser blob editor iframe remained blank;
  Chrome displayed and edited the same site/user/article with no server/plugin
  changes. Internal browser cause unresolved. Use Chrome; do not count this as a
  fixed Resilience defect or disable site security to work around it.
- **Test infrastructure:** WSL access required the approved execution path;
  shell quoting in a transfer command was corrected by using a script. Earlier
  in-memory listing needed StartAfter behavior. These are test-tool issues.
- **Product changes:** native creation, complete HTML history, trash/untrash,
  referenced-image replay and SDK function-loading collision handling are in
  the reviewed product. No new product defect was found in final-ZIP acceptance.

## 日本語要約

通常のPages・Posts・画像を含む独立M1製品経路を追加します。専用0.3.1 ZIPを使用し、
旧研究経路とは区別します。標準編集からS3保存・正式履歴・別WordPressへの復旧、
最終ZIPの新規導入と旧版からの更新、設定・履歴保持を確認しました。
画像付き通常記事は全サイト復旧経路を使用し、個別文書復旧と混同しないでください。
アプリ内ブラウザの空白はChromeとの比較で環境課題に分類し、内部原因は未確定です。
試験コマンド/模擬S3の問題と製品修正も分離しました。既存39件・定期設定は無変更です。
定期実行、実S3削除、正式公開は後回しです。上記未対応機能を全面対応とは扱いません。
