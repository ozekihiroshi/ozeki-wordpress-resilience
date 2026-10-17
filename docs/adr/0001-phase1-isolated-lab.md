# Phase 1の模擬環境と検査基準

日付：2026年10月17日。状態：Phase 1実装で採用。

## 背景

利用者はPhase 1の進行を承認し、実行環境は原則WSL上のUbuntuと指定した。復旧実験へ進む前に、比較可能な模擬サイトと機能検査を用意する必要がある。

## 採用内容

ソース管理先はD:\workspace\ozeki-wordpress-resilience、実行はWSL Ubuntuの/mnt/d/workspace/ozeki-wordpress-resilienceとする。Docker Composeに専用のsourceとrecoveryネットワーク・ボリュームを定義し、それぞれ異なるランダムなDB資格情報を使用する。Phase 1で起動するのはsource側と専用プレビュー用nginxとする。

WordPressとDBはinternalネットワークに置き、プレビュー用nginxのみがアクセス用ネットワークにも接続する。公開ポートはnginxのループバックに限定する。WordPress外部HTTP、メール、Cron、自動更新を止める。ダミーフォームはnonce検証と固定文字列への応答を行い、送信・保存はしない。

既存プラグインは調査コミット627e47c2b31527ef1486e582b79fd5dba875843fの依存物として.local/へ展開し、ローカルvendorの版・参照をそのcomposer.lockと照合する。既存リポジトリは変更せず、実装コードを新製品へ統合しない。Phase 1では有効化のみ行い、S3設定・書込みはしない。内部Recovery APIの採用はPhase 2前に検討する。

画像・PDF・日本語・絵文字・構造化option・ページ間リンク・HTTPログイン・ダミーフォームを基準に含める。DBやファイルの存在だけでなく、実際のHTTP応答を検査する。

## 検討した選択肢

既存wp-rescue環境の流用は、データ・ネットワーク・資格情報の混同を避けるため採用しない。クラウドの新規環境はPhase 1では不要。公開版プラグインのみへの限定は内部資産の調査を妨げるため、ローカル実験では開発コミットを固定する。

## 費用と残余リスク

Phase 1はローカル資源を使用し、クラウド課金を発生させない。同じDockerホスト上での分離はホスト侵害への耐性を証明しない。フォーム検査は実メール配送を証明しない。ソースサイトの正常性は独立復旧成功のE3ではない。

## 柔軟な見直し

新しい発見は影響・採否・理由を仕様やADRに反映する。低リスクの実装改善は進め、基本ポリシーの変更や課金・実運用影響を伴う変更は先に報告する。

## 実装中の発見

WordPressのローカルイメージに配布元RepoDigestがないことを確認した。内容IDへの固定に加え、.local/images/wordpress-phase1.tarへイメージを保存し、証拠にSHA-256を記録する。再現に必要な配布物を取得できるという仮定を避けるための補完であり、外部保護の完了とは扱わない。

Dockerの初回ネットワーク作成は all predefined address pools have been fully subnetted で失敗した。既存DockerネットワークとUbuntuのIPv4ルートを確認し、sourceに10.203.106.0/28、recoveryに10.203.106.16/28を指定した。他環境へ移す場合は重複を再確認する。既存ネットワークの削除やデーモンの全体設定変更は行わない。

初回HTTP検査で内部ネットワーク上の公開ポートが実際には割り当てられないことを確認したため、上記のプロキシ方式を採用した。ホスト設定上のPortBindingsだけでは検証が不足することも分かり、実際のNetworkSettings.PortsとHTTP応答を検査する。WordPress自体を外部接続ネットワークへ置く案は採用しない。参考：[Dockerのポート公開](https://docs.docker.com/engine/network/port-publishing/)。
