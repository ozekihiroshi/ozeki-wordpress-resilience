# Phase 4 独立復旧の実行手順

状態：2026年10月18日、2回の実復元に成功。実測結果は08-recovery-test-results.mdを参照。以下は今回の実行記録であり、既存出力のある同じディレクトリへ再実行しない。新規試験時もS3保存・固定版取得が成功するまでは元環境を停止しない。

## 前提と対象

元環境はWSLのowr-m1（source/source-db/preview）。保存中継はssh owr-writer、外部取得はssh owr-reader。復旧先は同じWSLホスト上の新しいDockerプロジェクトowr-m1-e3-1とowr-m1-e3-2。Dockerボリューム、DB資格情報、ネットワークは新規作成する。

今回の脅威モデルは元WordPress・DB・ファイルが使用不能という模擬障害である。ホストOS自体の侵害、AWSアカウント侵害、元ホスト完全喪失までを物理的に再現してはいない。共通IAMロールのまま機能検証することを利用者が選択しており、IAMの独立性は未達として評価する。

## 外部保管まで

1. tools/m1-live-storage.pyで小さなcanaryの保存と固定版取得を確認する。失敗したキーの記録は残し、自動的に同じキーへ再送しない。
2. tools/publish-m1-set.pyで計画した9資産を順に保存する。communityへ全量を一括コピーせず、1資産ずつ転送し、専用の一時入力ファイルだけを除去する。
3. 各資産をdmからVersionId指定で取得し、サイズとSHA-256を検証する。
4. 全8必須roleを確定したRAM・Recovery Setを新しいIDで作成し、それ自体もS3へ保存・取得する。
5. dmの専用ディレクトリへanchor.jsonを保存する。set、RAM、Bootstrapの取得先・版・期待ハッシュを含む。秘密情報は含めない。
6. 権限分離、真正性が未達/未検証であることをE2記録に残す。

## 元環境の遮断と新規取得

停止直前の時刻を想定障害時刻として記録する。

    bash tools/m1-lab.sh stop

このコマンドは専用owr-m1だけを停止する。既存の他プロジェクトを停止しない。元ボリュームは削除せず、検証中は読み取らない。

    python3 tools/fetch-independent-bundle.py

この処理はdmのanchorを起点に固定版を取得し直す。以前のアップロード元ファイルからのフォールバックはない。新規.local/independent-downloadへ保存し、全資産を期待ハッシュと照合する。Bootstrapは検証後に展開する。

## 復元と検査

    python3 .local/independent-download/bootstrap/run-independent-recovery.py \
      --bundle .local/independent-download \
      --output .local/e3-run-1 --run 1

ダウンロード済みの3実行イメージをdocker loadし、新規DBを起動、検証済みアーカイブを新規サイトボリュームへ展開、gzip SQLをストリーム展開して新規DBへ投入する。wp-config.phpとDB資格情報は復旧環境用に新規生成する。

投稿・ページ・独自設定・メディア・バージョンを基準データと比較する。その後、模擬管理者のパスワードを新しい実験用パスワードへ変更し、HTTPのページ・画像・PDF・内部リンク・ログイン・ダミーフォームを検査する。新しいパスワードは.local/e3-run-1/runtime.envにのみ保存し、ログや証拠へ出力しない。

初回成功後、初回復旧環境は停止する。以下で別の新規ボリュームから再現性を確認する。

    python3 .local/independent-download/bootstrap/run-independent-recovery.py \
      --bundle .local/independent-download \
      --output .local/e3-run-2 --run 2

2回目は同じ固定版取得済み資産を使用する。S3再取得の再現性試験とは分けて扱う。成功時は2回目をlocalhost:18081で稼働させ、元環境は停止したままにする。公開DNS・外部メール送信・本番サイトは変更しない。

## 失敗時

出力ディレクトリのresult.jsonとDockerログを保存し、実際の原因を特定する。部分実行済みのプロジェクトを新規として上書きしない。手順変更が必要なら新しいBootstrapとセットIDで再固定するか、変更と適用範囲を明示して再試験する。完了していない試験は成功と記録しない。

Dockerを既に利用できるWSL管理環境は前提である。裸のOSからDockerを導入する時間や監視の検知待ちは、この復旧時間には含まない。