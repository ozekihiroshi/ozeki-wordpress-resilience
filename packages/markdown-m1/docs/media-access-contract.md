# File access contract — unreleased / ファイル閲覧条件の契約（未配布）

This change is included in submitted rc.15; the application is awaiting the reviewer's response and publication has not been approved. It does not change existing S3 objects, production settings or release archives.

## User behavior

Page membership and file access are separate. A WP-Members restriction continues to protect the page; it does not make an ordinary image URL private. Supported public images remain usable after recovery.

Registered ordinary media with unrecognized attachment conditions or an access-control file in an uploads directory is retained with a **held** condition. Recovery keeps its bytes in non-autoloaded database storage, not public uploads. Articles remain editable, and a later save or independent Baseline preserves both the original bytes and the hold. This does not install the unsupported plugin's private-file delivery system. Review the recovery result's files not automatically applied before arranging their delivery separately.

Successful WordPress post/metadata operations trigger a comparison of current file conditions at the end of the request. Changes use the existing durable queue and formal-history order. After editing uploads-directory `.htaccess` or `web.config` files outside WordPress, use **Record file access conditions** in Tools → Resilience and check that no history remains pending. This inspection recognizes local attachment metadata, unsupported post references and these directory control files; it does not interpret arbitrary remote services, server-wide rules or plugin-specific authorization code.

## Compatibility

- New site snapshots/Checkpoints use `owr-separated-assets-media-access-1`. New media-bearing originals and access-only history use `owr-md-original-media-access-1`. Older readers reject these mandatory formats.
- Existing formats remain readable without rewriting them. A file without recorded access conditions is **unknown**, kept on hold rather than inferred public. A subsequent source-side condition record can supply the inspected condition; a recovery site's projected metadata cannot silently clear an inherited hold.
- A frozen legacy pending operation may resume. Its missing conditions become unknown; the old payload is not relabeled public.
- Keep the updated reader for new recovery points. Downgrading to an older reader cannot recover them. Prepare a clean destination; recovery refuses a held path already present in uploads, before installing files.

## Implementation boundary

`MediaAccess` supplies one classification for initial capture, daily referenced-media originals and condition-only history. `FileScope` identifies ordinary registered paths, separately from permission to place a file. Recovery validates the contract before projection removes unsupported metadata. Held bytes have a SHA-256 check and are copied into a later writer's own S3 namespace; a new Baseline does not depend on the previous writer's prefix. The existing 32 MiB per-resource limit applies. Database storage must accommodate retained held bytes; a failed write must fail recovery, not fall back to public placement.

The contract records public / held / unknown. It does not execute old configuration, reproduce arbitrary private-file serving or expose held files through a new download endpoint.

---

この変更はGitHub公開候補rc.15に含まれ、提出済みrc.14には含まれません。既存S3原本・履歴、本番設定、配布済みファイルは変更しません。

## 利用時の動作

ページの会員制限とファイルの閲覧条件を分けます。WP-Membersの制限はページに適用され、通常の画像URLを非公開にするものではありません。対応する公開画像は復旧後も利用できます。

通常のメディアとして登録されていても、認識できない添付設定やuploads内の制限ファイルがある場合は、原本を「保留」の条件と一緒に残します。復旧先では公開uploadsへ置かず、常時読み込みを無効にしたDB領域に保持します。その画像を含む記事の編集・再保存は続けられ、次の保存先でも原本と保留条件を引き継ぎます。未対応プラグインの限定配信機能を再現するものではありません。復旧結果の適用対象外一覧を確認し、必要な配信方法は別途準備してください。

WordPress経由の投稿・メタデータ変更は、操作終了時に現在のファイル条件を照合し、既存の確定待ちキューと正式履歴へつなぎます。WordPressの外でuploads内の`.htaccess`や`web.config`を変更したときは、**ツール → Resilience → ファイルの閲覧条件を再確認・記録**を実行し、未確定履歴が残っていないことを確認します。判定対象は添付情報、未対応投稿からの参照、これらのディレクトリ制限ファイルです。外部サービスやサーバー全体の設定、任意のプラグインの認可処理を解釈する仕組みではありません。

## 旧版との関係

新しい保存形式は対応する復旧処理が必要で、旧版は読み取りを拒否します。既存原本は変更せず読めますが、閲覧条件のない旧ファイルは「不明」として公開配置を保留します。保存元で条件を確認した新しい記録を加えることはできますが、復旧先で未対応設定が除かれただけでは保留を解除しません。旧版で確定待ちになった保存も、不明条件として再開できます。

復旧先には更新版と新しいuploads領域を用意してください。保留対象と同じファイルが既にある場合、先に整理が必要であることを表示して復旧を止めます。保留したファイルはSHA-256で照合し、再保存時には新しいS3保存先へ独立して保存します。1ファイル32 MiBの上限は継続し、保留データを保持できるDB容量も必要です。DB保存に失敗した場合に公開配置へ切り替えることはありません。
