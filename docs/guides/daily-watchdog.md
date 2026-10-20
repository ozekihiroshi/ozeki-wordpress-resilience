# 日次状態報告の独立watchdog

生成側・取得側それぞれへ、第三の実行環境から読取り専用SSHプローブを行います。既存の `watchdog-observer.py` が警報・回復の遷移と未配送記録を保持します。

## 判定

| 観測 | 表示・警報の意味 |
|---|---|
| SSH到達が途絶える | reachability の `monitor_stopped`。原因がネットワークかOS停止かは断定しない |
| SSHは到達するが報告時刻が更新されない | watchdog の `monitor_stopped`。生成または転送の進捗停止 |
| 対象サイト違い・形式不正・未来時刻 | `heartbeat_invalid` |
| SSHだけ復旧 | 到達性のみ回復。古い報告では進捗停止は解除しない |
| 新しい有効な報告を取得 | 進捗停止の回復通知 |

`daily-watchdog-probe.py` は固定した日次JSONを検査し、その `observed_at` を完了時刻として返します。照会時刻では更新しません。バックアップそのものの成否を判定する機能ではなく、状態報告の更新停止を監視する入口です。取得側の報告は生成側の時刻なので、生成周期・取得周期・通信時間を合算して十分な猶予を設定します。

## 配置

1. 各ホストに `tools` 一式を管理者所有・一般ユーザー書込み不可で配置する。
2. `owr-daily-probe` のような専用SSHユーザーを作り、日次報告だけ読めるグループへ所属させる。台帳・署名鍵・復旧権限を付与しない。
3. 管理者所有の設定に `monitor_id`、`site_id`、`report_file` の固定値を記載する。生成側と取得側は別の `monitor_id` にする。
4. 独立watchdogの公開鍵を、次の強制コマンド付きで登録する。

```text
restrict,command="/usr/bin/python3 /opt/owr/tools/daily-watchdog-probe.py --config /etc/owr/watchdog-probe.json" ssh-ed25519 <公開鍵>
```

5. SSH設定でパスワード・転送・TTYを禁止する。watchdog側ではホスト鍵を固定する。
6. 既存watchdogの設定を対象ごとに作る。`monitor_id` はプローブと一致、`state` は対象ごとに独立させる。`ssh` と通知設定は [独立watchdog手順](watchdog-observer.md) に従う。
7. 既存observerの定期実行へ接続する。再起動時にも同じ永続stateを使用し、台帳を消して再送しない。

生成側のプローブ設定例（管理者が固定するファイル）：

```json
{
  "monitor_id": "daily-source",
  "site_id": "generated-first-site",
  "report_file": "/var/lib/owr-status-source/daily.json"
}
```

取得側は `monitor_id` を `daily-receiver`、パスを `/var/lib/owr-status-web/daily.json` に変更します。`site_id` は実際の報告の値と一致させます。試験の100秒は本番推奨値ではありません。生成60秒・取得60秒の構成では少なくとも両周期と通信・処理の余裕を見込み、例えば300秒から運用要件に合わせて調整します。

本番の通知は既存dispatcherへ接続します。試験のローカルHTTP受信先を本番通知先として使わないでください。

## 専用試験と限界

2台の独立したゲストOSと、その外側のwatchdogプロセスで検証します。データ通信断、生成VM停止、取得VM停止、通知先503、watchdog再起動を試します。時計を進める模擬試験ではなく、実際の経過時間で確認します。

試験では通知を専用ローカルHTTP受信先へ配送します。Pushover・メール・iPhoneでの追加受信試験ではありません。ゲストOSから独立していますが同一PC上なので、PC全体の停止に耐えることは証明しません。本番では別ホスト・必要に応じ別障害領域に配置します。

生データには試験専用SSH秘密鍵とVMディスクを含むため公開しません。再試験には新しい `OWR_TWO_VM_OUTPUT` を指定し、既存の観測領域や試験出力を再利用しないでください。

この報告はホスト鍵で接続相手を確認した運用情報であり、独立署名による復旧承認とは別です。侵害された生成ホストが偽の新しい時刻を返すことを、この監視だけで防げるとは扱いません。


## 再現手順（WSL、専用KVM環境）

既存の [2台VMの前提条件](daily-two-vm-recovery.md) を準備し、リポジトリ直下から実行します。

```sh
export OWR_TWO_VM_OUTPUT="$HOME/.local/share/owr-daily-watchdog-new-trial"
python3 lab/two-vm/start.py
python3 lab/daily-watchdog/exercise.py
python3 lab/two-vm/cleanup.py
```

失敗時は出力とVMを保存し、稼働中処理を確認してください。同じ出力へ最初から再実行しないでください。

今回の実測は [公開検証記録](../../evidence-public/daily-watchdog.json) を参照。最初の起動には試験スクリプトのDocker引数位置の誤りがありました。watchdog起動・障害注入前に修正し、準備済みVMから再開しました。プラグイン障害や環境障害として集計していません。


## 遅いSSH応答の時刻判定修正

初回VM試験では生成側再起動直後に一過性の `heartbeat_invalid` がありました。調査により、SSH要求前の時刻と応答中に更新された完了時刻を比較する実装上の問題を、実時間6秒の遅延試験で再現しました。これは環境問題ではなくwatchdogの判定不備として修正しました。

明示的な試験時刻を指定しない実行では、応答受信後の現在時刻で判定します。報告時刻自体は更新せず、本当に未来の時刻、巻戻り、同時刻で内容が異なる報告は引き続き拒否します。初回結果は `daily-watchdog-first-trial.json` に保持し、新しい2台VMで全障害試験を再実施した最終結果を `daily-watchdog.json` に保存しています。
