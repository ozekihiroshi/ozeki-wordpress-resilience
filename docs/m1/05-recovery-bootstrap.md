# Phase 2：Recovery Bootstrap

更新日：2026年10月18日。Phase 2の最小実装。外部保管と復旧実行はPhase 3・4で検証する。

## 現在できること

WordPressなしでRAMを生成・検査し、Recovery SetにRAMの正確なバイト列のSHA-256を固定できる。RAMはDB、uploads、WordPress core、テーマ、プラグイン、設定、実行環境、既存製品のRecovery Manifestという8種類の必須資産を識別する。保存先はlocal、s3、pendingを明確に区別する。

S3の宣言にはbucket、region、key、version_id、credential_refを必須とする。Version IDの省略、空文字、文字列nullを許可しない。資格情報そのものを格納する欄はない。local/S3の資産にはバイト数とSHA-256が必須。pendingには架空のハッシュやサイズを設定できない。

サンプルRS-M1-P2-001はPhase 1のバージョン情報と実行環境イメージの情報を使用する。残り7種類の資産は未取得である。環境情報のinventory_scopeはphase1_baseline_onlyであり、全プラグイン・MUプラグインの完全な棚卸しを意味しない。独自guard.phpを含む実ファイルの収集はPhase 3で行う。

## ファイルと依存環境

- tools/recovery-metadata.py：generate、freeze、inspect。
- schemas/recovery-asset-manifest.schema.json：RAM v1。
- schemas/recovery-set.schema.json：固定セットv1。
- examples/m1/asset-declarations.json：資産宣言入力。environmentは生成時に補う。
- examples/m1/RS-M1-P2-001/：固定済みのRAMとRecovery Set。
- tools/verify-m1-phase2.py：回帰試験と独立ディレクトリでの検査。
- evidence/m1/phase2/：試験結果。E2/E3を示す証拠ではない。

WSL Ubuntu-24.04、Python 3.12、python3-jsonschema 4.10.3で検証。実装はPython 3.10以上を必要とする。jsonschemaは外部依存であり、災害時にネット接続してインストールする前提にしない。独立Bootstrap配布物に実行環境・依存パッケージ・スキーマ・手順を保管し、その配布物の信頼情報も別経路で確保することがPhase 3の残作業である。AWS SDKやWordPressはメタデータ検査に不要。

## 通常時：生成と固定

Ubuntuでプロジェクトルートに移動する。

    cd /mnt/d/workspace/ozeki-wordpress-resilience
    python3 tools/recovery-metadata.py generate \
      --baseline evidence/m1/phase1/source-baseline.json \
      --declarations examples/m1/asset-declarations.json \
      --output .local/ram-candidate.json
    python3 tools/recovery-metadata.py freeze \
      --ram .local/ram-candidate.json --output .local/recovery-sets

generateはbaselineのバージョン欄だけを取り込み、生成日時を記録する。DB内容やruntime.envは取り込まない。存在する出力ファイルは上書きしない。baselineは本番側のE1宣言であり、独立観測ではない。

freezeはset_id名のディレクトリを排他的に作成する。同じIDは再発行できない。未確定資産を確定させる場合も、新しいset_idの宣言を作り、新しいRAMを発行する。既存セットを書き換えない。ディスク障害などで途中失敗した場合もIDを予約したまま残す。壊れたセットは検査で拒否し、新しいIDで再発行する。

この排他制御は本ツールの通常操作に対する制約であり、管理者によるファイル改変・削除を防ぐWORMではない。S3のVersioning、独立権限、保持策の実測はPhase 3で行う。

## 障害時：独立した入口から確認する

1. 被害を受けたWordPressやその管理者アカウントを使わず、別管理のBootstrap保管先から、ツール、スキーマ、手順、対象site_id/set_idとセットの取得先を入手する。現段階のサンプル保管先はローカルexamplesであり、サーバー全損への耐性はまだない。
2. 別管理の資格情報保管先でcredential_refに対応する復旧専用権限を取得する。RAMには鍵・パスワード・署名付きURLを入れない。実アカウント、ロール、認証回復手順はPhase 3で確定する。
3. Recovery SetとRAMを取得する。S3利用時は必ず指定したVersion IDで取得する。最新版への置換を許可しない。
4. 独立保管した期待SHA-256があれば、次の引数でRecovery Setを照合する。そのセットがRAMの正確なバイト列を束縛し、RAMが各資産を束縛する。
5. pending、欠落、ハッシュ不一致、取得不能、権限不足があれば、復旧実行に進まず不足を記録する。別セットを使う場合はID、時点、業務上の損失を再確認する。
6. 全資産を確認した後に、procedure_id=owr-m1-independent-recovery-v1に対応するPhase 4の独立環境での復旧手順へ進む。このIDの実行手順は現在未実装であり、このCLIは復元しない。

    python3 tools/recovery-metadata.py inspect \
      --ram examples/m1/RS-M1-P2-001/ram.json \
      --set examples/m1/RS-M1-P2-001/recovery-set.json

独立保管済みの64桁SHA-256がある場合だけ --expected-set-sha256 を追加する。RAMと同じ場所で新たに計算したハッシュを独立した信頼情報と呼ばない。--asset-root . を追加するとlocal資産をストリーム読み取りしてサイズ・ハッシュを確認する。S3の取得はこのCLIの範囲外であり、not_observedのままになる。

終了コード0はメタデータ検査の成功だけを意味する。復旧可能・外部保管済み・真正性検証済みを意味しない。エラーは終了コード2。結果のrecovery_readyは本フェーズでは常にfalse、authenticityはunverified、restoreはuntested。ローカル整合性が一致しても、侵害前の安全なデータであることは保証しない。

## 信頼の起点と既存製品との関係

M1 Phase 2では署名を実装せず、真正性をunverifiedとして扱う。独立保管SHA-256との照合機能はあるが、その保管主体の独立性・紛失対策・配布経路を検証していないため、成功してもauthenticityを昇格しない。検査プログラムやスキーマ自体の差し替えにも、独立して信頼できる配布元が必要である。

既存のOzeki Database Backup for S3のodbfs3-recovery-set v1は変更しない。上位RAMのrecovery_manifest資産として、その原文バイト列のサイズ・ハッシュ・保存場所を参照する。プラグイン内部の32桁set_idと上位のRS-M1-P2-001は別の名前空間である。

Phase 2は内部Recovery APIを呼び出していない。Phase 3の収集アダプターで固定コミット627e47c2b31527ef1486e582b79fd5dba875843fの厳密なdecode契約を確認し、DB・全uploadsの実体、Version ID、RAMとの対応を検証する。内部manifestのversion_id:nullを上位でそのまま確定扱いにしてはならない。uploadsを複数オブジェクトで保存する場合は、全オブジェクトのVersion IDとハッシュを束縛する一覧資産が別途必要である。現在の上位CLIは既存manifest内部まで解析・検証していない。

## 検証と限界

    python3 tools/verify-m1-phase2.py

28試験：生成、上書き拒否、同一ID拒否、バイト改変、アンカー不一致、site不一致、セットの資産欠落、重複JSON、サイズ上限、必須role、重複ID、依存先欠落・循環、秘密フィールド、日時、非対応版、不正な真正性宣言、パストラバーサル、S3版欠落、ローカル改変とsymlink逸脱などを検査する。

別ディレクトリにCLI・スキーマ・セットだけをコピーし、クリーンな環境変数とPython -Iで読み取る検査も実施する。WordPressとDBにはアクセスしない。同じWSLホスト上の試験であり、別ホストやネットワーク隔離を証明する試験ではない。

許可フィールドを限定することで資格情報の混入経路を減らすが、汎用文字列に人が秘密を入れたことを完全に検知する仕組みではない。入力宣言に実資格情報を含めない。資産の展開・コード実行・S3接続は本ツールでは行わない。

Phase 2完了はRAM/セット/Bootstrapの最小契約と検査入口の成立を意味する。外部取得、独立した信頼情報の配布、全資産の実取得、更新停止期間の整合点、実復旧、RPO/RTO測定、AC01〜AC08の成立は今後の検証対象である。