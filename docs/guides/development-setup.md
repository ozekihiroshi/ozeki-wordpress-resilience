# 初版開発環境

Ubuntu / WSL、Python 3.12、PHP 8.1以上（mysqliを含む）、Composer、Docker Engine + Composeを使う。M1は完成版プラグインではなく研究用ツールである。

## オフライン検査

    python3 -m venv .local/venv
    . .local/venv/bin/activate
    pip install -r requirements-dev.txt
    composer install --no-interaction --prefer-dist
    python3 -m unittest discover -s tests
    php tests/test-versioned-transfer.php
    php tests/test-temporary-role-auth.php

クラウド操作なしで実行できる。Composerは初回のみ依存物を取得する。

## M1の新しい模擬環境

旧M1と同じImage IDは公開レジストリから取得できない場合がある。新しい基準データを採取する場合は、使用する3イメージを取得して明示的に固定する。元のM1とバイト単位で同じ環境を再現したとは扱わない。

    mkdir -p .local
    git clone https://github.com/ozekihiroshi/secure-s3-storage-for-wordpress.git .local/upstream-plugin
    git -C .local/upstream-plugin checkout 627e47c2b31527ef1486e582b79fd5dba875843f
    composer install --working-dir=.local/upstream-plugin --no-interaction
    bash tools/prepare-m1-plugin.sh .local/upstream-plugin
    docker pull wordpress:php8.3-apache
    docker pull mariadb:11.8
    docker pull nginx:alpine
    python3 tools/pin-m1-images.py --output .local/images.env
    OWR_IMAGE_LOCK=.local/images.env bash tools/m1-lab.sh prepare
    bash tools/m1-lab.sh up
    bash tools/m1-lab.sh seed
    bash tools/m1-lab.sh verify
    python3 tools/verify-m1-http.py

同じポート18081や専用プロジェクトが既に使用中の環境では実行しない。新しいイメージで元の版の基準検査が失敗する場合は、その差分を調べ、基準を黙って書き換えない。

## 外部保存・復元の準備

examples/m1/live-target.example.jsonを.local/live-target.jsonへコピーし、自己所有の実験用バケット・所有者・リージョン・プレフィックス・SSH接続先・重複しないset_idを設定する。例示値では実クラウド処理を拒否する。資格情報はEC2ロールの一時認証を使う。S3のVersioningとIAMはs3-iam-setup.mdを参照する。実資産の保存・転送には費用が発生する。

capture-m1-assets.pyで収集したE1を指定してprepare-m1-bundle.py --capture E1_PATH --baseline evidence/m1/phase1/source-baseline.json --set-id NEW_ID --output .local/NEW_BUNDLEを実行する。新しい基準の梱包では--images .local/images.envも指定する。収集対象の稼働イメージと一致していることを確認する。出力は既存ディレクトリへ上書きしない。

OWR_BUNDLE_DIRには生成したバンドルの絶対パスを設定する。m1-live-storage.py setupで専用コードと設定を保存側へ配置し、小さなcanaryの転送を先に確認する。publish-m1-set.pyで保存・取得検証後、07-independent-recovery-procedure.mdに沿って模擬環境を停止し独立復元する。共有ロールでの成功を権限分離の成功とはしない。

本手順は新規試験の入口であり、アカウント・ネットワーク・OSの準備や既存資産の無断削除を自動実行しない。公開用集計はevidence-public/、実行時の原本はGit対象外のevidence/へ保存する。
