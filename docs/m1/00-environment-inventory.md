# Phase 0 環境と資産の調査

調査日：2026年10月17日  
範囲：ローカルソース、文書、Git状態、実行環境の読取り調査。クラウド操作と復旧試験は未実施。

## 結果

M1の基礎になるバックアップ機能と内部Recovery Set実装が既存リポジトリに存在する。追加開発は既存資産の利用を前提に絞り込める。一方、実験環境はまだ準備されておらず、WSLのDockerデーモンへ接続できない。Phase 1は利用者の調査結果確認後に開始する。

## プロジェクトとGit

| 対象 | 調査結果 |
| --- | --- |
| D:\workspace\ozeki-wordpress-resilience | 正式なプロジェクトルート。仕様書と原文が存在。git statusは「not a git repository」。Git未初期化 |
| D:\workspace\secure-s3-storage-for-wordpress | 既存プラグインの開発リポジトリ。main...origin/main、HEAD 627e47c2b31527ef1486e582b79fd5dba875843f |
| 同上の変更 | tracked差分なし。未追跡はozeki-markdown-documents/とtools/prepare-wordpress-release-030.sh。変更・削除していない |
| D:\workspace\wp-rescue | 既存環境の参照候補。main...origin/main、HEAD 1fb6b66220a8d8c3f7ac5944c0ebca9fcf9b50bf |
| 同上の変更 | deploy/、docs/owr-writer-company-staging.md、docs/eleview-markdown/、omd-wporg-0.1.1-verification.zip、scripts/が未追跡。変更していない |
| D:\workspace\wordpress-org-svn\ozeki-database-backup-for-s3\trunk | ローカル配布作業コピー。ヘッダとStable tagは0.2.0。開発版とは異なる |

originとの比較はローカルに保存された追跡情報であり、fetchはしていない。

D:\AGENTS.md、D:\workspace\AGENTS.md、新プロジェクト直下のAGENTS.mdは存在しなかった。既存ソースの今回読んだ範囲にも追加指示ファイルは見つからなかった。

## バージョンの区別

開発ソースのプラグインヘッダは0.3.0。READMEは公開版を0.2.1、内部Recovery Setを0.3.0として説明している。ローカルタグはv0.2.1まで存在する。WordPress.orgの現在の公開状態をこの調査で再検証したものではない。

M1で使用する版は未確定。0.3.0を使う場合は上記コミット等へ固定し、内部APIへの依存を明記する。ローカルSVNの0.2.0を最新公開版とみなして使わない。

## 実行環境

| 項目 | 確認結果 |
| --- | --- |
| Windows PATH | git、rg、AWS CLI、Node.jsあり。docker、php、wp、pythonは今回のGet-Commandでは見つからない |
| WSL | Ubuntu-24.04を確認 |
| WSL PHP | /usr/bin/php、PHP 8.3.6 |
| WSL DBクライアント | /usr/bin/mysql、/usr/bin/mariadbあり。DBサーバ稼働は未確認 |
| WSL WP-CLI | command -v wpで検出されない |
| WSL Docker | CLI 29.1.3、Compose 2.40.3+ds1-0ubuntu1~24.04.1 |
| Dockerデーモン | /var/run/docker.sockがなく接続失敗。コンテナ、イメージ、ボリュームの状態は未確認 |
| WSL起動 | systemd user session for ozekiの開始失敗警告あり。原因未調査 |

AWS CLIの存在は、実験用権限が使える証拠ではない。AWS資格情報、SSH設定、.env、実運用DB・バックアップの内容は読んでいない。既存サイトへの接続、サービス起動、イメージ取得は行っていない。

## 試験環境候補

第一候補はWSL上のDockerで、模擬本番と復旧先を別ネットワーク・別ボリュームに分離する構成。既存tools/test-wordpress-recovery-local.shには分離試験の参考実装がある。ただし新プロジェクトの専用リソース名を使い、既存wp-rescueの環境を再利用・停止しない。

既存スクリプトのwordpress:php8.3-apacheとmariadb:11.8は参考値であり、新実験の固定版ではない。Phase 1では具体的な版とイメージdigestを記録する構成を提案する。Dockerが利用できない場合は専用Linux VMが代替候補。課金クラウドは別途対象・概算費用の承認が必要。

## コマンドとエラー記録

| 調査操作 | 結果と対応 |
| --- | --- |
| Get-ChildItem、rg --files、Get-Content、rg -n | 対象の一覧・公開ソース・仕様・文書を読取り |
| git -C D:\workspace\ozeki-wordpress-resilience status --short --branch | fatal: not a git repository。初期化せず記録 |
| 既存リポジトリのgit status / rev-parse | 初回はdubious ownership。サンドボックス実行者と所有者が異なる |
| git -c safe.directory=対象パス ... | コマンド単位の例外でstatus、HEAD、tag、diffを確認。global設定は変更しない。wp-rescue確認では両既存パスの例外を指定して成功 |
| Get-Command git,rg,docker,php,wp,aws,python,node | 複数指定のうち未検出項目があるため終了コード1。見つかった項目と区別して記録 |
| wsl --list --quiet | サンドボックス内ではWsl/EnumerateDistros/Service/E_ACCESSDENIED。昇格した読取り調査でUbuntu-24.04を確認 |
| wsl --exec sh -lc内のcommand -v、docker version、docker compose version、php --version | PHP等は成功。Dockerはunix:///var/run/docker.sock接続失敗。複合コマンド末尾の成功だけでDocker正常とは判定しない |

最後のWSLコマンドから得たDockerエラーは、dial unix /var/run/docker.sock: connect: no such file or directory。デーモンの起動や修復はPhase 1へ持ち越す。

## 調査の限界

既存文書の試験成功記録は過去の報告として参照し、今回の実測結果やM1のE3として扱わない。S3バケット設定、Object Lock、Versioning、IAM、復旧用資格情報、料金、現行サイトの構成は未確認。Phase 0のコード調査は完了したが、M1の実装・実証は未着手。
