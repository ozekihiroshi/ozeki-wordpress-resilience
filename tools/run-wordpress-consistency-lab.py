#!/usr/bin/env python3
"""Disposable, offline, real WordPress/MariaDB gate tests. WSL Docker required."""
import argparse
import importlib.util
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import select
import subprocess as sp
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]

def check(ok, message):
    if not ok:
        raise RuntimeError(message)

def run(*args, input=None, timeout=60, must=True):
    p = sp.run(args, input=input, capture_output=True, timeout=timeout)
    if must and p.returncode:
        raise RuntimeError(f'{args[0]} failed ({p.returncode}): {p.stderr.decode()[-600:]}')
    return p

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-lab', action='store_true')
    parser.add_argument('--routes', action='store_true', help='Also test real admin, REST, cron and the evidence adapter')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--external',action='store_true',help='Include restricted SSH and independent queue tests')
    parser.add_argument('--lab-image',help='Locally built ExternalLab image, required for --external')
    parser.add_argument('--s3-lab',action='store_true',help='Explicit real AWS experiment with generated lab assets and isolated roles')
    parser.add_argument('--s3-resume-set',help='Resume an existing independently signed AWS lab set after inspection')
    parser.add_argument('--daily-s3-stage', type=Path, help='Publish generated assets unsigned to the real lab bucket; never sign or restore')
    parser.add_argument('--approved-trust',type=Path)
    parser.add_argument('--approved-set-id')
    parser.add_argument('--approved-document-sha256')
    parser.add_argument('--approved-key-sha256')
    parser.add_argument('--approved-read-receipts',type=Path)
    args = parser.parse_args()
    approved_restore=None
    selected=[args.approved_trust,args.approved_set_id,args.approved_document_sha256,args.approved_key_sha256,args.approved_read_receipts]
    if any(selected):
        if not all(selected):parser.error('approved restore requires trust, set, both hashes and a NEW receipt directory')
        if args.s3_lab or args.s3_resume_set or args.daily_s3_stage:parser.error('approved restore cannot publish or auto-sign')
        args.external=True
        approved_restore=dict(trust=args.approved_trust,set_id=args.approved_set_id,document_hash=args.approved_document_sha256,key_hash=args.approved_key_sha256,receipts=args.approved_read_receipts)
    if args.daily_s3_stage:
        if args.s3_lab or args.s3_resume_set: parser.error('daily publication cannot use automatic signing/resume')
        args.external=True
    if args.s3_resume_set and not args.s3_lab:parser.error('--s3-resume-set requires --s3-lab')
    if args.s3_lab: args.external=True
    if args.external:
        check(bool(args.lab_image),'--external requires --lab-image')
        args.routes=True
    if not args.execute_lab:
        parser.print_help(); return
    check(args.output is not None and not args.output.exists(), 'Choose a NEW output file')
    prefix = 'owr-consistency-' + secrets.token_hex(5)
    db, web = prefix + '-db', prefix + '-web'
    print('LAB_RESOURCE_PREFIX ' + prefix, flush=True)
    images = dict(line.split('=', 1) for line in (ROOT / 'lab/m1/images.env').read_text().splitlines() if '=' in line)
    if args.external:
        images['OWR_WP_IMAGE']=json.loads(run('docker','image','inspect',args.lab_image).stdout)[0]['Id']
    password = secrets.token_hex(24)
    created = []
    results = []
    holders = []
    route_evidence = None
    external_evidence = None

    def php(code):
        return run('docker', 'exec', '-u', 'www-data', web, 'php', '-r', code).stdout

    def sql(query):
        return run('docker', 'exec', '-i', db, 'sh', '-c', 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot --batch --skip-column-names lab', input=query.encode()).stdout

    def writer(delay=0):
        return sp.Popen(['docker', 'exec', '-u', 'www-data', web, 'php', '/lab/writer.php', str(delay)], stdout=sp.PIPE, stderr=sp.PIPE)

    def finish_writer(p):
        out, err = p.communicate(timeout=15)
        check(p.returncode == 0 and out.startswith(b'{'), 'fixture writer failed: '+(out+err).decode()[-600:])
        check(json.loads(out)['state'] == 'written', 'writer did not resume/finish')

    def event(p, expected, timeout=12):
        # Unbuffered pipe prevents select from overlooking lines buffered in Python.
        check(bool(select.select([p.stdout], [], [], timeout)[0]), 'gate event timeout: ' + expected)
        raw = bytearray()
        while not raw.endswith(b'\n'):
            ch = os.read(p.stdout.fileno(), 1)
            check(bool(ch), 'gate exited before ' + expected)
            raw.extend(ch)
        obj = json.loads(raw)
        check(obj['state'] == expected, f'expected {expected}, got {obj}')
        return obj

    def hold(wait=5, lease=60):
        token = secrets.token_hex(16)
        p = sp.Popen(['docker', 'exec', '-i', '-u', 'www-data', web, 'php', '/lab/gate.php', 'hold', token, str(wait), str(lease)], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE, bufsize=0)
        holders.append(p)
        event(p, 'fenced')
        return p, token

    def ready(p):
        event(p, 'drained'); event(p, 'ready')

    def release(p, token):
        p.stdin.write((token + '\n').encode()); p.stdin.flush()
        event(p, 'release_requested'); event(p, 'released')
        check(p.wait(timeout=5) == 0, 'release process failed')

    def resumed():
        finish_writer(writer())
        check(php("echo file_exists('/tmp/owr-gate.fence') ? 'bad' : 'ok';") == b'ok', 'stale fence')

    try:
        for image in (images['OWR_DB_IMAGE'], images['OWR_WP_IMAGE']):
            run('docker', 'image', 'inspect', image)
        with tempfile.TemporaryDirectory(prefix='owr-lab-env-') as work:
            env = Path(work) / 'env'
            env.write_text(f'MARIADB_ROOT_PASSWORD={password}\nMARIADB_ROOT_HOST=%\nMARIADB_DATABASE=lab\nMARIADB_USER=lab\nMARIADB_PASSWORD={password}\nWORDPRESS_DB_HOST=127.0.0.1:3306\nWORDPRESS_DB_NAME=lab\nWORDPRESS_DB_USER=lab\nWORDPRESS_DB_PASSWORD={password}\nLAB_ROOT_PASSWORD={password}\nLAB_ADMIN_PASSWORD={password}\nWORDPRESS_CONFIG_EXTRA=define("DISABLE_WP_CRON",true); define("WP_HTTP_BLOCK_EXTERNAL",true); define("DISALLOW_FILE_MODS",true);\n')
            env.chmod(0o600)
            run('docker', 'run', '-d', '--name', db, '--network', 'none', '--memory', '512m', '--env-file', str(env), images['OWR_DB_IMAGE'])
            created.append(db)
            deadline = time.monotonic() + 90
            while run('docker', 'exec', db, 'healthcheck.sh', '--connect', '--innodb_initialized', must=False).returncode:
                check(time.monotonic() < deadline, 'DB startup timeout'); time.sleep(1)
            run('docker', 'run', '-d', '--name', web, '--network', 'container:' + db, '--memory', '512m', '--env-file', str(env), '-v', str(ROOT / 'lab/consistency') + ':/lab:ro', *(['-v','/run/owr-dispatch'] if args.external else []), images['OWR_WP_IMAGE'])
            created.append(web)
            inspected=json.loads(run('docker','inspect',db,web).stdout)
            check(inspected[0]['HostConfig']['NetworkMode']=='none','DB network isolation missing')
            check(inspected[1]['HostConfig']['NetworkMode'].startswith('container:'),'WP network isolation missing')
            check(all(not x['HostConfig']['PortBindings'] for x in inspected),'unexpected published port')
            deadline = time.monotonic() + 90
            while run('docker', 'exec', web, 'test', '-f', '/var/www/html/wp-config.php', must=False).returncode:
                check(time.monotonic() < deadline, 'WP startup timeout'); time.sleep(1)
            installed=php("define('WP_INSTALLING',true); require '/var/www/html/wp-load.php'; require_once ABSPATH.'wp-admin/includes/upgrade.php'; wp_install('Isolated consistency lab','labadmin','lab@example.invalid',false,'',getenv('LAB_ADMIN_PASSWORD')); @mkdir(WP_CONTENT_DIR.'/uploads',0775,true); echo 'installed';")
            check(installed.endswith(b'installed'),'WordPress installation failed')
            # Only explicit fixture endpoint is a supported web writer in this lab.
            run('docker', 'exec', web, 'sh', '-c', 'printf \'<?php require "/lab/writer.php";\' > /var/www/html/lab-write.php')
            finish_writer(writer())

            active = writer(3)
            deadline = time.monotonic() + 8
            while php("echo file_exists('/tmp/owr-writer-active') ? 'yes' : 'no';") != b'yes':
                check(time.monotonic() < deadline, 'writer startup timeout'); time.sleep(.05)
            start = time.monotonic()
            try:
                p, token = hold(); ready(p)
            except Exception:
                # Keep the gate failure. Observe the fixture writer before container cleanup.
                diagnostic = {'format': 'owr-fixture-drain-failure-v1', 'elapsed_seconds': round(time.monotonic()-start, 3), 'storage_started': False}
                try:
                    out, err = active.communicate(timeout=15)
                    diagnostic.update(writer_returncode=active.returncode, writer_stdout=out.decode(errors='replace')[-1000:], writer_stderr_sha256=hashlib.sha256(err).hexdigest())
                except sp.TimeoutExpired:
                    diagnostic['writer_still_running_after_observation'] = True
                args.output.parent.mkdir(parents=True, exist_ok=True)
                with args.output.with_suffix('.drain-failure.json').open('x') as evidence:
                    json.dump(diagnostic, evidence, indent=2)
                raise
            drained_seconds = time.monotonic() - start
            finish_writer(active)
            check(drained_seconds > 1, 'did not wait for in-flight writer')
            results.append({'case':'inflight_writer_drained', 'passed':True, 'wait_seconds':round(drained_seconds, 3)})

            rejected = writer(); out, _ = rejected.communicate(timeout=5)
            check(rejected.returncode == 3 and json.loads(out)['state'] == 'fenced', 'CLI write not rejected')
            response = php("$c=curl_init('http://127.0.0.1/lab-write.php'); curl_setopt($c,CURLOPT_RETURNTRANSFER,true); $s=curl_exec($c); echo curl_getinfo($c,CURLINFO_HTTP_CODE).' '.$s;")
            check(response.startswith(b'503 ') and b'fenced' in response, 'HTTP write not rejected')
            results.append({'case':'http_and_cli_rejected_while_fenced','passed':True})

            blocked = run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_PASSWORD" mariadb -ulab lab',input=b"SET SESSION lock_wait_timeout=1; INSERT INTO wp_options(option_name,option_value,autoload) VALUES('lock_probe','bad','no');",must=False)
            check(blocked.returncode != 0 and b'1205' in blocked.stderr, 'direct DB insert not blocked by read lock')
            results.append({'case':'direct_database_write_blocked','passed':True})

            dump = run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables lab').stdout
            archive = run('docker','exec',web,'tar','-czf','-','-C','/var/www/html/wp-content/uploads','.').stdout
            rows = sql("SELECT p.meta_value,h.meta_value FROM wp_postmeta p JOIN wp_postmeta h ON p.post_id=h.post_id WHERE p.meta_key='_lab_file' AND h.meta_key='_lab_sha256';").decode().splitlines()
            with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tar:
                for row in rows:
                    name, digest = row.split('\t')
                    check(hashlib.sha256(tar.extractfile('./'+name).read()).hexdigest()==digest, 'DB/media mismatch')
            check(len(rows) >= 2 and len(dump)>1000, 'capture empty')
            results.append({'case':'captured_db_media_references_match','passed':True,'references':len(rows),'dump_bytes':len(dump),'archive_bytes':len(archive)})
            release(p,token); resumed()
            results.append({'case':'normal_release_resumes_writes','passed':True})
            sql('CREATE DATABASE restored;')
            run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot restored',input=dump)
            restored_rows=sql("SELECT p.meta_value,h.meta_value FROM restored.wp_postmeta p JOIN restored.wp_postmeta h ON p.post_id=h.post_id WHERE p.meta_key='_lab_file' AND h.meta_key='_lab_sha256';").decode().splitlines()
            check(sorted(restored_rows)==sorted(rows),'dump restore references differ')
            results.append({'case':'dump_restored_and_captured_media_match','passed':True})

            p, token = hold(); ready(p)
            try:
                run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --single-transaction --skip-lock-tables nonexistent_database')
                raise ValueError('injected dump failure did not fail')
            except RuntimeError:
                pass
            finally:
                release(p,token)
            resumed()
            results.append({'case':'capture_failure_finally_resumes_writes','passed':True})

            active = writer(3)
            deadline=time.monotonic()+8
            while php("echo file_exists('/tmp/owr-writer-active') ? 'yes' : 'no';") != b'yes':
                check(time.monotonic()<deadline,'active timeout'); time.sleep(.05)
            p, token = hold(wait=.2)
            event(p,'drain_timeout'); event(p,'released'); p.wait(timeout=5)
            finish_writer(active); resumed()
            results.append({'case':'drain_timeout_releases_owned_fence','passed':True})

            p, token = hold(lease=2); ready(p)
            event(p,'lease_expired'); event(p,'released'); p.wait(timeout=5)
            resumed()
            results.append({'case':'lease_expiry_resumes_writes','passed':True})

            p, token = hold(); ready(p)
            other = sp.Popen(['docker','exec','-u','www-data',web,'php','/lab/gate.php','hold','other','1','2'],stdout=sp.PIPE)
            out,_=other.communicate(timeout=5)
            check(other.returncode==2 and json.loads(out)['state']=='busy','second coordinator not excluded')
            check(php("echo file_exists('/tmp/owr-gate.fence') ? 'yes' : 'no';")==b'yes','non-owner released fence')
            p.stdin.close()
            event(p,'owner_disconnected'); event(p,'released'); p.wait(timeout=5)
            resumed()
            results.append({'case':'concurrent_owner_rejected_and_disconnect_releases','passed':True})
            check(sql("SELECT COUNT(*) FROM wp_options WHERE option_name='lock_probe';").strip()==b'0','timed-out DB write later committed')
            if args.routes:
                spec=importlib.util.spec_from_file_location('routes',ROOT/'tools/wordpress-route-lab.py')
                routes=importlib.util.module_from_spec(spec);spec.loader.exec_module(routes)
                route_evidence=routes.run_routes(db,web,php,sql,hold,ready,release,results,run,check)
            if args.external:
                spec=importlib.util.spec_from_file_location('external',ROOT/'tools/wordpress-external-lab.py')
                external=importlib.util.module_from_spec(spec);spec.loader.exec_module(external)
                external_evidence=external.run_external(db,web,php,sql,hold,ready,release,results,run,check,images['OWR_WP_IMAGE'],route_evidence,s3_lab=args.s3_lab,s3_resume_set=args.s3_resume_set,daily_s3_stage=args.daily_s3_stage,approved_restore=approved_restore)
    finally:
        for p in holders:
            if p.poll() is None:
                if p.stdin and not p.stdin.closed: p.stdin.close()
                try: p.wait(timeout=20)
                except sp.TimeoutExpired: p.kill(); p.wait()
        for name in reversed(created):
            run('docker','rm','-f','-v',name)
    report = {'format':'owr-wordpress-consistency-lab-v1','recorded_at':datetime.now(timezone.utc).isoformat(),'results':results,'all_passed':True,
              'images':images,'isolated_network':'none / shared loopback only','resources_removed':True,
              'scope':'Dedicated cooperative fixture writers only; no production approval, arbitrary plugin/SSH file writes excluded.'}
    if route_evidence is not None: report['route_evidence']=route_evidence
    if external_evidence is not None:report['external_evidence']=external_evidence
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f: json.dump(report,f,indent=2); f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['route_evidence','external_evidence']},indent=2))

if __name__ == '__main__':
    main()
