#!/usr/bin/env python3
"""Read-only deployment assessment; no capture, credentials, SSH or cloud calls."""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys

sys.dont_write_bytecode = True
from datetime import datetime, timezone
from pathlib import Path

s = importlib.util.spec_from_file_location('capture_contract', Path(__file__).with_name('first-site-capture.py'))
capture = importlib.util.module_from_spec(s)
s.loader.exec_module(capture)
LIMIT = 65536


def read_json(path):
    # Refuse links, devices and FIFOs before reading; bound all input.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('regular file required')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('input too large')
        def pairs(items):
            result = {}
            for k, v in items:
                if k in result:
                    raise ValueError('duplicate key')
                result[k] = v
            return result
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    finally:
        os.close(fd)


def assess(profile, inventory, workspace, now=None):
    now = now or datetime.now(timezone.utc)
    issues = []
    def issue(code, category, action):
        issues.append(dict(code=code, category=category, action=action))
    def finish(config_hash=None):
        categories = {x['category'] for x in issues}
        state = ('unsupported' if 'unsupported' in categories else
                 'needs_configuration' if issues else 'eligible_for_dedicated_trial')
        return dict(format='owr-deployment-preflight-v1', assessed_at=now.isoformat(),
                    state=state, production_ready=False, capture_started=False,
                    config_sha256=config_hash, issues=issues,
                    evidence_scope={'profile': 'operator_declaration',
                                    'inventory': 'operator_supplied_not_authenticated',
                                    'workspace': 'local_metadata_only'},
                    not_verified=['live_writer_fencing', 'database_credentials', 's3_permissions_and_retention',
                                  'signing_host_independence', 'malware_absence', 'production_restore'])
    if not isinstance(profile, dict):
        issue('invalid_profile', 'configuration', '構成情報をJSONオブジェクトで用意してください。')
        return finish()
    valid = False
    try:
        capture.validate(profile)
        valid = True
    except capture.Rejected as exc:
        reason = str(exc)
        issue(reason, 'unsupported' if reason.startswith('unsupported_') else 'configuration',
              '対応範囲と構成情報を確認してください。取得は開始していません。')
    except (TypeError, KeyError, AttributeError, ValueError):
        issue('malformed_profile', 'configuration', '構成情報の項目と型を修正してください。')
    if not valid:
        return finish()
    config_hash = capture.digest(profile)
    for group, names in [('storage', ['destination_ref', 'writer_ref', 'reader_ref']),
                         ('trust', ['operator', 'public_pin_ref']),
                         ('runtime', ['wordpress_ref', 'database_ref'])]:
        for name in names:
            if profile[group][name].strip().lower() in {'not-connected', 'unknown', 'todo', 'unset'}:
                issue(group+'_'+name+'_unset', 'configuration', '未設定の参照情報を確定してください。秘密の値は入力しないでください。')
    expected = {'format', 'config_sha256', 'observed_at', 'site_id', 'wordpress', 'database',
                'files', 'writers', 'queue', 'dependencies', 'runtime', 'incomplete_runs', 'uncertain_puts'}
    if not isinstance(inventory, dict) or set(inventory) != expected:
        issue('inventory_missing_or_invalid', 'configuration', '対象サイトの棚卸し情報を指定された形式で用意してください。')
    else:
        if inventory['format'] != 'owr-deployment-inventory-v1' or inventory['site_id'] != profile['site_id'] or inventory['config_sha256'] != config_hash:
            issue('inventory_binding_mismatch', 'configuration', 'サイトと設定版が一致する棚卸し情報を取り直してください。')
        try:
            observed = datetime.fromisoformat(inventory['observed_at'])
            if observed.tzinfo is None or not -5 <= (now-observed).total_seconds() <= 86400:
                raise ValueError()
        except (TypeError, ValueError, OverflowError):
            issue('inventory_time_invalid', 'configuration', '24時間以内の時刻付き棚卸し情報を用意してください。')
        # Exact equality is deliberate: extra writers, engines or dependencies cannot disappear.
        for group in ('wordpress', 'database', 'files', 'writers', 'queue', 'dependencies', 'runtime'):
            if json.dumps(inventory[group], sort_keys=True) != json.dumps(profile[group], sort_keys=True):
                issue(group+'_inventory_mismatch', 'configuration', '設定と棚卸しが一致しません。差異を調査し、対象を黙って縮小しないでください。')
        for key in ('incomplete_runs', 'uncertain_puts'):
            if type(inventory[key]) is not int or inventory[key] < 0:
                issue(key+'_invalid', 'configuration', '既存処理の台帳を確認し、件数を記録してください。')
            elif inventory[key] > 0:
                issue(key+'_present', 'operational', '未完了処理・結果不明送信の照合を先に行ってください。自動再送しません。')
    required = 2 * profile['operations']['max_bytes'] + profile['operations']['reserve_bytes']
    try:
        fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            st = os.fstat(fd)
            if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) & 0o077:
                issue('workspace_not_private', 'environment', '実行ユーザー所有の0700作業領域を別途用意してください。検査は権限を変更しません。')
            if stat.S_IMODE(st.st_mode) & 0o700 != 0o700:
                issue('workspace_owner_permissions', 'environment', '所有者の読取り・書込み・検索権限を確認してください。')
            fs = os.fstatvfs(fd)
            if fs.f_bavail * fs.f_frsize < required:
                issue('workspace_capacity_insufficient', 'environment', '一時保管を含む必要容量を確保してください。検査は削除しません。')
            if fs.f_flag & os.ST_RDONLY:
                issue('workspace_readonly_filesystem', 'environment', '保存先ファイルシステムが読取り専用です。')
        finally:
            os.close(fd)
    except OSError:
        issue('workspace_unavailable', 'environment', '存在する作業領域を指定し、読取り可能か確認してください。')
    result = finish(config_hash)
    result['workspace_required_bytes'] = required
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', required=True)
    p.add_argument('--inventory', required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--host-report')
    p.add_argument('--host-nonce')
    a = p.parse_args()
    try:
        profile = read_json(a.profile)
        result = assess(profile, read_json(a.inventory), a.workspace)
        if a.host_report or a.host_nonce:
            spec = importlib.util.spec_from_file_location('host_check', Path(__file__).with_name('host-inventory-check.py'))
            host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
            result = host.integrate(result, profile, read_json(a.host_report) if a.host_report else None, a.host_nonce)
    except (OSError, ValueError, RecursionError):
        result = dict(format='owr-deployment-preflight-v1', state='needs_configuration',
                      production_ready=False, capture_started=False,
                      issues=[dict(code='input_unreadable_or_invalid', category='configuration',
                                   action='入力ファイルの形式・サイズ・権限を確認してください。')])
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result['state']=='eligible_for_dedicated_trial' else 2


if __name__ == '__main__':
    raise SystemExit(main())
