# Phase 1 模擬WordPress環境

更新日：2026年10月17日。Phase 1完了。模擬サイトの正常性と比較基準を確認した。独立復旧試験は未実施。

## 保存先と実行環境

Windows側のプロジェクトはD:\workspace\ozeki-wordpress-resilience。コマンドはWSL Ubuntu-24.04上の/mnt/d/workspace/ozeki-wordpress-resilienceで実行する。Docker、PHP、Python、Git等もUbuntu側を基本とする。

構成はlab/m1/compose.yml。プロジェクト名はowr-m1。sourceとrecoveryは別ネットワーク、別DB、別ボリューム、別のランダムな資格情報を使う。Phase 1ではsource、source-dbとプレビュー用nginxを起動し、recoveryは将来の試験用profileとして定義する。

ブラウザの入口はhttp://localhost:18081。公開バインドはプレビュー用nginxの127.0.0.1のみ。WordPressとDBにはホスト公開ポートを設けない。復旧側のHTTP入口はPhase 4で別途定義する。既存プロジェクトのコンテナ、ネットワーク、ボリュームを変更しない。

## 固定した依存物

Dockerイメージはtools/pin-m1-images.pyでローカルイメージを内容IDへ固定し、lab/m1/images.envとimages.lock.jsonへ記録する。タグは初回の発見にだけ用いる。別マシンでは記録されたRepoDigest、または保存したイメージアーカイブから同一イメージを準備し、内容IDを照合する。WordPressのローカルイメージにはRepoDigestがないため、.local/images/wordpress-phase1.tarとSHA-256を保管する。このコピーは同一ホスト内であり、外部保護はPhase 3で別途行う。自動pullはしない。

バックアッププラグインはコミット627e47c2b31527ef1486e582b79fd5dba875843f、版0.3.0を使用する。tools/prepare-m1-plugin.shで.local/backup-pluginへ依存物として展開する。vendorは既存のローカルコピーを用い、composer.lockの版とsource referenceに照合し、全ファイルの集約ハッシュを記録する。依存物はGitに含めない。

## 再現手順

WSLのプロジェクトルートで実行する。

```sh
test -f lab/m1/images.env || python3 tools/pin-m1-images.py
bash tools/prepare-m1-plugin.sh
bash tools/m1-lab.sh prepare
bash tools/m1-lab.sh up
bash tools/m1-lab.sh seed
bash tools/m1-lab.sh verify
python3 tools/verify-m1-http.py
python3 tools/verify-m1-isolation.py
```

初回のpin、依存物準備、seedは再実行による上書きを拒否する。すでに準備済みの場合はupとverifyを利用する。seedは未インストールの専用DBだけに実行する。停止はbash tools/m1-lab.sh stop。ボリューム削除は自動化していない。

管理者名はowradmin。ランダムな模擬サイト専用パスワードは.local/runtime.envのOWR_ADMIN_PASSWORD。ファイルはGit対象外であり、パスワードを証拠やログへ出力しない。実運用の資格情報は利用しない。

## 外部作用の制限

WordPressとDBをDocker内部ネットワークへ置く。プレビュー用nginxだけが別のアクセス用ネットワークにも接続し、固定のWordPress宛に中継する。これに加え、WordPressの外部HTTP・メール・Cron・自動更新を無効化する。S3バケットとAWS資格情報は設定しない。フォームは固定模擬文字列の受付だけを検査し、メール送信や個人情報の保存はしない。

sourceのWebサービスにfixtureと固定プラグインを読み取り専用でマウントする。これらは実験用の供給方法であり、M1の復旧資産保護が完了したことを意味しない。将来の復旧側にはsourceのDB・サイト・秘密情報・プラグイン作業ディレクトリを共有しない。

## 検証記録

evidence/m1/phase1/にsource-baseline.json、http-checks.json、plugin-provenance.jsonを保存する。これらは模擬本番の正常性の記録であり、独立復旧成功のE3ではない。

## 発見と対応

開始時はWSLの起動に時間がかかり、systemd user session警告、Dockerソケット不在、API待ちが発生した。再確認ではDockerサービスが起動処理中と分かった。Docker未導入とは扱わず、既存サービスの復元・起動が終わるまで待ち、他プロジェクトを停止・削除しない。

Dockerの初回ネットワーク作成は all predefined address pools have been fully subnetted で失敗した。既存DockerネットワークとUbuntuのIPv4ルートを確認し、sourceに10.203.106.0/28、recoveryに10.203.106.16/28を指定した。他環境へ移す場合は重複を再確認する。既存ネットワークの削除やデーモンの全体設定変更は行わない。

HTTP検査の初回は接続失敗。内部ネットワークだけのsourceでは、HostConfig.PortBindingsに要求があってもNetworkSettings.Portsはnullであり、実際には公開されていなかった。プレビュー用nginxと10.203.106.32/28のアクセス用ネットワークを追加し、検査も実際のポート割当を確認する方式へ変更した。初回失敗の記録は日時付きで保持する。

初回のisolation-checks-initial-config-only.jsonは設定値だけを確認した旧方式の記録であり、公開ポートが実際に使える証拠には採用しない。最終判定は改善後のisolation-checks.jsonとhttp-checks.jsonを併用する。

## 完了結果

| 検査 | 結果 | 記録 |
| --- | --- | --- |
| DB・ファイル・設定・プラグイン・外部作用の抑止 | 16項目合格 | evidence/m1/phase1/source-baseline.json |
| ページ・日本語・画像・PDF・リンク・ログイン・フォーム | 14項目合格 | evidence/m1/phase1/http-checks.json |
| 別資格情報・ボリューム・ネットワーク・実際のポート割当等 | 18項目合格 | evidence/m1/phase1/isolation-checks.json |
| Windows側の閲覧 | 127.0.0.1:18081への要求でHTTP 200とOWR-HOMEを確認 | 作業時確認 |

固定した実測環境はWordPress 7.0.2、PHP 8.3.33、MariaDB 11.8.8、Twenty Twenty-Five 1.5、Ozeki Database Backup for S3 0.3.0。ホストUbuntuのPHP 8.3.6とは区別する。画像・PDFの原本2件に生成ファイルを含めたuploads全5ファイルを基準記録へ保存した。

構文検査とShellCheckも実施した。Gitをmainブランチで初期化し、.local/、環境ファイル、SQL、アーカイブを追跡対象から除外した。コミット・pushは行っていない。

クラウド資源は作成せず、S3操作・実顧客データ利用・既存プラグインのソース変更は行っていない。復旧側のサービスは起動していない。模擬サイトは起動状態で残し、停止コマンドを上記に記載した。

## 次段階

Phase 2では上位RAMと既存RecoveryManifestの対応、全資産の固定参照、Bootstrap、M1で必要な真正性確認の範囲を決める。実装前に既存内部APIの契約を評価し、既存プラグインの責任範囲を維持する。
