#!/usr/bin/env python3
"""Read-only preflight for the explicitly provisioned dm MySQL lab; never imports SQL."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

DB = 'owrrecoverylab20261018'
USER = 'owrlab20261018@localhost'

def main():
    if len(sys.argv) != 1:
        raise RuntimeError('Arguments and database overrides are not permitted')
    root = Path.home() / '.local/owr-db-lab'
    for path, mode in [(root, 0o700), (root/'client.cnf', 0o600), (root/'verification.json', 0o600)]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != mode:
            raise RuntimeError('Private lab path ownership or permissions mismatch')
    expected = json.loads((root/'verification.json').read_text())
    if expected.get('database') != DB or expected.get('user') != USER:
        raise RuntimeError('Provisioning record target mismatch')
    def query(sql):
        result = subprocess.run(['mysql', '--defaults-file='+str(root/'client.cnf'),
            '--batch', '--skip-column-names', '--connect-timeout=5'], input=sql,
            capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise RuntimeError('Lab connection failed; diagnostic output withheld')
        return result.stdout.strip()
    if query('SELECT DATABASE(), CURRENT_USER(), @@server_uuid;') != DB+'\t'+USER+'\t'+expected['server_uuid']:
        raise RuntimeError('Connected database, account or server mismatch')
    actual = query('SHOW GRANTS FOR CURRENT_USER;').splitlines()
    identity = "`owrlab20261018`@`localhost`"
    required = {'GRANT USAGE ON *.* TO '+identity,
        'GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER ON `'+DB+'`.* TO '+identity}
    if set(actual) != required or len(actual) != 2:
        raise RuntimeError('Privileges differ from the lab-only grant')
    if query('SELECT @@mandatory_roles;') not in ('', 'NONE'):
        raise RuntimeError('Mandatory roles require a new privilege review')
    print(json.dumps({'passed': True, 'database': DB, 'user': USER,
        'target_and_privileges_verified': True, 'imports_performed': False}))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Preflight failed: '+type(error).__name__, file=sys.stderr)
        sys.exit(1)
