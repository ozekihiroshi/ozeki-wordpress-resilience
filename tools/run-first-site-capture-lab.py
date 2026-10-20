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
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.external=False
    if not args.execute_lab:
        parser.print_help(); return
    check(args.output is not None and not args.output.exists(), 'Choose a NEW output file')
    prefix = 'owr-first-site-' + secrets.token_hex(5)
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
            run('docker', 'run', '-d', '--name', db, '--label', 'owr.first-site=generated', '--network', 'none', '--memory', '512m', '--env-file', str(env), images['OWR_DB_IMAGE'])
            created.append(db)
            deadline = time.monotonic() + 90
            while run('docker', 'exec', db, 'healthcheck.sh', '--connect', '--innodb_initialized', must=False).returncode:
                check(time.monotonic() < deadline, 'DB startup timeout'); time.sleep(1)
            run('docker', 'run', '-d', '--name', web, '--label', 'owr.first-site=generated', '--network', 'container:' + db, '--memory', '512m', '--env-file', str(env), '-v', str(ROOT / 'lab/consistency') + ':/lab:ro', *(['-v','/run/owr-dispatch'] if args.external else []), images['OWR_WP_IMAGE'])
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


            spec=importlib.util.spec_from_file_location('first_site_cases',ROOT/'tools/first-site-lab-cases.py')
            cases=importlib.util.module_from_spec(spec);spec.loader.exec_module(cases)
            cases.exercise(db,web,php,sql,hold,ready,release,run,check,results,args.output)
    finally:
        for p in holders:
            if p.poll() is None:
                if p.stdin and not p.stdin.closed:p.stdin.close()
                try:p.wait(timeout=20)
                except sp.TimeoutExpired:p.kill();p.wait()
        for name in reversed(created):run('docker','rm','-f','-v',name)
    report={'format':'owr-first-site-lab-v1','recorded_at':datetime.now(timezone.utc).isoformat(),'results':results,'images':images,'all_passed':True,'resources_removed':all(run('docker','inspect',name,must=False).returncode!=0 for name in created),'scope':'generated isolated WP/MariaDB; external capture adapter, not plugin end-to-end acceptance; no S3/signing'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
