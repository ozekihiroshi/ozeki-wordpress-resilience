"""Validate a bounded host probe report and combine it with declared preflight."""
from datetime import datetime, timezone
import re

def integrate(result, profile, report, nonce, now=None):
    now = now or datetime.now(timezone.utc)

    def add(code, category='configuration'):
        result['issues'].append(dict(code=code, category=category, action='実測結果と未確認項目を確認してください。自動修正・取得は行いません。'))
    if isinstance(report, dict) and report == {'format': 'owr-host-inventory-v1', 'status': 'probe_failed', 'stage': report.get('stage')} and (report.get('stage') in ('configuration', 'database', 'files')):
        add('host_probe_' + report['stage'] + '_failed', 'configuration' if report['stage'] == 'configuration' else 'environment')
        result['host_observation'] = {'state': 'probe_failed'}
        result['state'] = 'unsupported' if any((x['category'] == 'unsupported' for x in result['issues'])) else 'needs_configuration'
        return result
    try:
        if not (isinstance(nonce, str) and re.fullmatch('[a-f0-9]{32}', nonce)):
            raise ValueError('invalid host report')
        if not (isinstance(report, dict) and set(report) == {'format', 'site_id', 'config_sha256', 'nonce', 'observed_at', 'status', 'facts', 'unverified'}):
            raise ValueError('invalid host report')
        if not (report['format'] == 'owr-host-inventory-v1' and report['status'] == 'observed'):
            raise ValueError('invalid host report')
        if not (report['site_id'] == profile['site_id'] and report['config_sha256'] == result['config_sha256'] and (report['nonce'] == nonce)):
            raise ValueError('invalid host report')
        at = datetime.fromisoformat(report['observed_at'])
        if not (at.tzinfo and -5 <= (now - at).total_seconds() <= 300):
            raise ValueError('invalid host report')
        f = report['facts']
        if not set(f) == {'database', 'files', 'wordpress', 'runtime'}:
            raise ValueError('invalid host report')
        db = f['database']
        files = f['files']
        wp = f['wordpress']
        runtime = f['runtime']
        if not (set(db) == {'name', 'prefix', 'engines', 'tables'} and set(files) == {'root', 'entries', 'bytes', 'links', 'special'}):
            raise ValueError('invalid host report')
        if not (set(wp) == {'standard_upload_path', 'external_upload_url', 'multisite_tables'} and all((type(x) is bool for x in wp.values()))):
            raise ValueError('invalid host report')
        if not (set(runtime) == {'php_version', 'os_family'} and isinstance(runtime['php_version'], str) and re.fullmatch('\\d+\\.\\d+\\.\\d+(?:[A-Za-z0-9.+~-]*)', runtime['php_version'])):
            raise ValueError('invalid host report')
        if not isinstance(runtime['os_family'], str):
            raise ValueError('invalid host report')
        for x in [db['tables'], files['entries'], files['bytes'], files['links'], files['special']]:
            if not (type(x) is int and 0 <= x <= 2 ** 53):
                raise ValueError('invalid host report')
        if not (db['tables'] > 0 and isinstance(db['engines'], list) and all((isinstance(x, str) for x in db['engines']))):
            raise ValueError('invalid host report')
        unknown = ['writers', 'queue', 'dependencies', 'runtime_image_binding', 'multisite_config', 'storage', 'trust', 'operational_ledgers', 'file_snapshot_consistency']
        if not report['unverified'] == unknown:
            raise ValueError('invalid host report')
        if db['name'] != profile['database']['name'] or db['prefix'] != profile['database']['prefix']:
            add('host_database_mismatch')
        if db['engines'] != ['InnoDB']:
            add('host_engine_unsupported', 'unsupported')
        if files['root'] != profile['files']['root']:
            add('host_file_root_mismatch')
        if files['links'] or files['special']:
            add('host_file_type_unsupported', 'unsupported')
        if files['bytes'] > profile['operations']['max_bytes']:
            add('host_asset_size_limit', 'unsupported')
        if not wp['standard_upload_path'] or wp['external_upload_url'] or wp['multisite_tables']:
            add('host_wordpress_unsupported', 'unsupported')
        if runtime['os_family'] != 'Linux' or tuple(map(int, runtime['php_version'].split('.')[:2])) < (8, 1):
            add('host_runtime_unsupported', 'unsupported')
        result['host_observation'] = {'state': 'validated_report', 'summary': {'tables': db['tables'], 'entries': files['entries'], 'bytes': files['bytes'], 'links': files['links'], 'special': files['special'], 'innodb_only': db['engines'] == ['InnoDB']}, 'unverified': unknown, 'authenticated': False}
        result['evidence_scope']['host'] = 'bounded_report_bound_to_nonce_not_remote_attestation'
        add('host_unverified_scope_remaining')
    except (AssertionError, ValueError, TypeError, KeyError, AttributeError):
        add('host_report_invalid')
        result['host_observation'] = {'state': 'invalid'}
    result['state'] = 'unsupported' if any((x['category'] == 'unsupported' for x in result['issues'])) else 'needs_configuration'
    return result
