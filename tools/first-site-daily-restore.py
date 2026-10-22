#!/usr/bin/env python3
"""Explicit generated-site recovery from independent trust and fixed S3 versions."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


d = load('restore_daily', 'first-site-daily.py')
c = load('restore_capture', 'first-site-capture.py')
g = d.gate
current_trust = load('daily_current_trust', 'current-recovery-trust.py')


def recover(trust, destination, set_id, config_hash, document_hash, key_hash,
            adapter_factory=None, restore=None):
    """No publisher workspace/ledger/source server is read; no PUT or signing operation."""
    trust, destination = Path(trust).resolve(), Path(destination).resolve()
    g.check(not trust.is_relative_to(destination) and not destination.is_relative_to(trust),
            'trust and recovery workspace must be separate')
    checkpoint = current_trust.current(trust, trust/'approved.json', d.SITE, set_id)
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    report = dict(format='owr-first-site-daily-restore-v1', set_id=set_id,
                  passed=False, assets_verified=False, restore_started=False,
                  production_recovery_approved=False, malware_cleanliness='unverified')
    def save():
        d.io.write_json(destination/'result.json', report)
    save()
    try:
        snapshot = destination/'trust-snapshot'; snapshot.mkdir(mode=0o700)
        for name in ('pin.json','approved.json','approved.sig','public.pem'):
            g.check((trust/name).stat().st_size < 65536, 'oversize trust input')
            shutil.copyfile(trust/name, snapshot/name)
        doc, sig = snapshot/'approved.json', snapshot/'approved.sig'
        g.check(g.sha(doc.read_bytes()) == document_hash, 'operator document hash mismatch')
        g.check(g.sha((snapshot/'public.pem').read_bytes()) == key_hash, 'operator key hash mismatch')
        m, pin = g.authorize(snapshot, doc, sig, d.SITE, set_id)
        g.check(m['paired']['site_id'] == 'generated-first-site', 'generated fixture only')
        g.check(m['paired']['config_sha256'] == config_hash, 'operator configuration pin mismatch')
        g.check(pin['bucket'] == d.transport.BUCKET and pin['region'] == d.transport.REGION,
                'dedicated experimental bucket required')
        g.check(sum(e['locator']['size_bytes'] for e in m['assets']) <= 128*1024**2, 'lab size limit')
        current_trust.unchanged(checkpoint, snapshot, doc, d.SITE, set_id)
        report['current_trust'] = checkpoint
        adapter = (adapter_factory or d.transport.S3Adapter)(destination/'reader-receipts')
        assets, verified = g.fetch_verified(snapshot, doc, sig, d.SITE, set_id, config_hash, adapter.get)
        target = destination/'verified-assets'; target.mkdir(mode=0o700)
        for role, name in g.NAMES.items():
            (target/name).write_bytes(assets[role])
        inventory = c.archive_inventory(target/g.NAMES['files'], 512*1024**2)
        g.check(c.digest(inventory) == m['paired']['inventory_sha256'], 'captured inventory mismatch')
        report.update(assets_verified=True, verification=verified,
                      verified_bytes=sum(map(len, assets.values())),
                      source_workspace_used=False, source_server_used=False,
                      signature_source='independent local signed document; asset versions from S3')
        save()
        current_trust.unchanged(checkpoint, snapshot, doc, d.SITE, set_id)
        report['restore_started'] = True; save()
        outcome = (restore or restore_offline)(target, inventory, destination)
        g.check(outcome['passed'] is True and outcome['resources_removed'] is True, 'restore/cleanup incomplete')
        report.update(passed=True, isolated_restore=outcome, completed_at=g.now().isoformat())
        save()
        return report
    except Exception as exc:
        report['error_type'] = type(exc).__name__; save()
        raise


def run(*args, input=None, timeout=120, must=True):
    env = None
    if args and args[0] == 'docker':
        args = ('/usr/bin/docker', '--host', 'unix:///var/run/docker.sock', *args[1:])
        env = {k: v for k, v in os.environ.items() if not k.startswith('DOCKER_')}
    p = subprocess.run(args, input=input, capture_output=True, timeout=timeout, env=env)
    if must and p.returncode:
        # Do not expose dump contents, environment values or command output.
        raise RuntimeError('isolated recovery command failed: '+args[0])
    return p


def restore_offline(target, inventory, workspace):
    """Fresh generated Docker targets; no published ports, source mounts or AWS credentials."""
    password = secrets.token_hex(24)
    prefix = 'owr-daily-restore-'+secrets.token_hex(6)
    db, web = prefix+'-db', prefix+'-web'
    ownership_token = secrets.token_hex(16)
    d.io.write_json(workspace/'ownership.json',dict(token=ownership_token,containers=[db,web]))
    images = dict(x.split('=',1) for x in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in x)
    runtime = load('same_host_runtime', 'same-host-runtime.py')
    created = []
    outcome = dict(passed=False, resources_removed=False, containers=[db,web])
    d.io.write_json(workspace/'isolation.json', outcome)
    def wait(args):
        deadline=time.monotonic()+90
        while run(*args, must=False).returncode:
            if len(args)>2 and args[:2]==['docker','exec']:
                state=json.loads(run('docker','inspect',args[2]).stdout)[0]['State']
                g.check(state['Running'] is True, 'isolated target exited during startup')
            g.check(time.monotonic()<deadline, 'isolated target startup timeout')
            time.sleep(1)
    try:
        with tempfile.TemporaryDirectory(prefix='owr-daily-restore-env-') as tmp:
            env = Path(tmp)/'env'
            env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true);\n')
            env.chmod(0o600)
            # Record intended names before creating resources, including timeout/unknown outcomes.
            db_image = json.loads(run('docker','image','inspect',images['OWR_DB_IMAGE']).stdout)[0]['Id']
            web_image = json.loads(run('docker','image','inspect',images['OWR_WP_IMAGE']).stdout)[0]['Id']
            created.append(db)
            db_id = run(*runtime.create_args('db', db, db_image, ownership_token, env)).stdout.decode().strip()
            created.append(web)
            web_id = run(*runtime.create_args('web', web, web_image, ownership_token, env, db_id)).stdout.decode().strip()
            config = dict(format=runtime.FORMAT, workspace=str(workspace), production_paths=[],
                          token=ownership_token, db_id=db_id, web_id=web_id,
                          db_image=db_image, web_image=web_image)
            d.io.write_json(workspace/'runtime-config.json', config)
            outcome['preflight'] = runtime.require(config, 'prepared')
            d.io.write_json(workspace/'isolation.json', outcome)
            run('docker','start',db_id)
            wait(['docker','exec',db_id,'healthcheck.sh','--connect','--innodb_initialized'])
            outcome['before_database'] = runtime.require(config, 'db_started')
            run('docker','exec','-i',db_id,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',
                input=(target/g.NAMES['database']).read_bytes())
            run('docker','start',web_id)
            wait(['docker','exec',web_id,'test','-f','/var/www/html/wp-config.php'])
            outcome['before_files'] = runtime.require(config, 'running')
            run('docker','exec','-i',web,'tar','xzf','-','-C','/var/www/html','--no-same-owner',
                input=(target/g.NAMES['files']).read_bytes())
            run('docker','exec',web,'chown','-R','www-data:www-data','/var/www/html')
            # Docker WordPress fixture uses getenv for DB credentials. Use newly generated target values.
            code = """require '/var/www/html/wp-load.php';global $wpdb;
echo json_encode(['post'=>(int)$wpdb->get_var("SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_title='First site normal post'"),
'attachment'=>$wpdb->get_var("SELECT meta_value FROM {$wpdb->postmeta} WHERE meta_key='_wp_attached_file'"),
'media'=>hash_file('sha256',WP_CONTENT_DIR.'/uploads/one.png'),
'cron_disabled'=>defined('DISABLE_WP_CRON') && DISABLE_WP_CRON,
'http_blocked'=>defined('WP_HTTP_BLOCK_EXTERNAL') && WP_HTTP_BLOCK_EXTERNAL]);"""
            value = json.loads(run('docker','exec','-u','www-data',web,'php','-r',code).stdout)
            g.check(value['post']==1 and value['attachment']=='one.png'
                    and value['media']==inventory['wp-content/uploads/one.png']
                    and value['cron_disabled'] and value['http_blocked'], 'restored contents/configuration mismatch')
            http = json.loads(run('docker','exec',web,'php','-r',
                "$c=curl_init('http://127.0.0.1/');curl_setopt($c,CURLOPT_RETURNTRANSFER,true);$b=curl_exec($c);echo json_encode(['status'=>curl_getinfo($c,CURLINFO_HTTP_CODE),'post'=>strpos($b,'First site normal post')!==false]);").stdout)
            g.check(http['status']==200 and http['post'], 'restored HTTP failed')
            outcome.update(passed=True, network='none + shared private namespace', published_ports=False,
                           source_mounts=False, fresh_database_credentials=True,
                           wordpress=value, http=http)
    except Exception as exc:
        outcome["error_type"] = type(exc).__name__
        if hasattr(exc, "assessment"): outcome["blocked_preflight"] = exc.assessment
        raise
    finally:
        for name in reversed(created):
            found = run('docker','inspect',name,must=False)
            if found.returncode==0:
                obj=json.loads(found.stdout)[0]
                g.check(obj['Config']['Labels'].get('owr.daily-restore')=='generated' and obj['Config']['Labels'].get('owr.recovery-token')==ownership_token, 'cleanup ownership mismatch')
                run('docker','rm','-f','-v',name)
        run('docker','info','--format','{{.ServerVersion}}')
        outcome['resources_removed'] = all(run('docker','inspect',n,must=False).returncode!=0 for n in created)
        d.io.write_json(workspace/'isolation.json',outcome)
    return outcome


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-lab',action='store_true')
    for arg in ('trust','output','set-id','config-sha256','document-sha256','key-sha256'):
        p.add_argument('--'+arg, required=True)
    a=p.parse_args()
    if not a.execute_lab:
        p.error('--execute-lab required')
    os.umask(0o077)
    print(json.dumps(recover(a.trust,a.output,a.set_id,a.config_sha256,a.document_sha256,a.key_sha256),indent=2))


if __name__=='__main__':
    main()
