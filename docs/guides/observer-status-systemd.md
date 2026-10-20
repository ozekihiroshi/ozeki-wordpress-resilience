# 独立watchdog報告転送のsystemd・OS再起動検証

転送サービスの導入方法は[定期受渡し手順](observer-status-relay.md)を参照してください。サービスをsource・receiverの2インスタンスで有効化し、WordPressがアクセスされなくても60秒間隔で報告を取得します。

今回の対象は転送サービスです。watchdogと生成側・取得側の試験プロセスはVM外に置き、転送用Ubuntu VMだけを再起動します。WSL、Dockerデーモン、72時間観測の環境は再起動しません。

## 起動と確認

専用ユーザー・鍵・設定・ディレクトリを用意した後、サービス定義を配置します。

    sudo systemctl daemon-reload
    sudo systemctl enable --now owr-observer-status@source owr-observer-status@receiver
    systemctl is-enabled owr-observer-status@source owr-observer-status@receiver
    systemctl is-active owr-observer-status@source owr-observer-status@receiver

両方でenabled・activeを確認し、管理画面を再読み込みして最終取得処理と観測完了時刻が更新されることを確認します。activeだけでは取得成功の証明になりません。転送失敗・古い報告も併せて確認してください。

サービスはowr-relayで動作し、WordPressの実行グループには報告の読取りだけを許可します。NoNewPrivileges、ProtectSystem=strict、ProtectHome、PrivateTmpを指定し、書込み先を専用ディレクトリへ限定します。RequiresMountsForで保存先のマウントを起動の前提にします。実装ファイルはroot所有、ディレクトリ0755・通常ファイル0644とし、サービス実行ユーザーに変更を許可しません。

## 停止・再開

    sudo systemctl stop owr-observer-status@source owr-observer-status@receiver
    sudo systemctl start owr-observer-status@source owr-observer-status@receiver

stopは今回の稼働を止めますが、自動起動設定は維持します。OS起動後も停止させたい場合は、明示的にdisable --nowを使います。

停止中も直前の報告・警報履歴を保持します。取得記録が5分以上古くなると、管理画面は「定期取得の記録が更新されていない」と表示し、報告も期限超過なら「現在の状態は不明」と表示します。再開して新しい報告を取得すると回復します。画面の再読み込みが必要です。

## OS再起動後

サービス有効化済みの専用VMをOS再起動し、Boot IDが変わったこと、両インスタンスがenabled・activeになったこと、新しい報告が取得できたことを分けて確認します。

    cat /proc/sys/kernel/random/boot_id
    systemctl status owr-observer-status@source owr-observer-status@receiver
    sudo journalctl -b -u owr-observer-status@source -u owr-observer-status@receiver

再起動後に手動startを行わず回復することが自動起動の確認です。ネットワークやSSH接続の回復前は転送失敗として記録し、古い報告を正常扱いしません。

## 検証範囲

再現入口は tools/run-observer-relay-vm-lab.py --output ＜新しい専用フォルダ＞。専用Ubuntu KVMゲスト、VM外の実watchdog、固定コマンドSSHとホスト鍵固定、専用WordPress/MariaDB/Chromiumを使用します。試験用の生成報告のみで、S3・本番データ・本番鍵を使いません。

管理画面の試験には専用9p共有を介してゲストの出力ファイルを読取り専用で渡します。転送自体はVM内のsystemdサービスが実SSHで行い、別処理が報告時刻を書き換えたり転送を代行したりしません。9p共有は試験設備であり、本番で必要な構成ではありません。

同じ物理PC上の試験です。別物理ホスト全体の障害、実通知サービス、他のOS、強制電源断による破損は今回の合格範囲に含めません。

停止表示には5分の猶予があるため、短時間のOS再起動では停止表示を経ずに更新が再開する場合があります。再起動試験ではBoot IDの変化と新しい報告時刻を証拠にし、常に停止表示が出るとは説明しません。

再現試験には、[既存のVM試験設備](../../lab/systemd-vm/README.md)で用意するKVM・専用Dockerイメージ・キャッシュ済みUbuntuイメージが必要です。出力フォルダには試験専用SSH鍵とVMディスクを含むため非公開で保管し、公開にはevidence-publicの整理済み結果だけを使います。
