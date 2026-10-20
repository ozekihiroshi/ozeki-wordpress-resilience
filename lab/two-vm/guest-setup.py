import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
role=sys.argv[1];assert role in ('source','receiver') and os.geteuid()==0
assert Path('/etc/hostname').read_text().strip()=='owr-two-'+role
def run(*args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
run('mkdir','-p','/tmp/owr-payload');run('tar','xf','/tmp/payload.tar','-C','/tmp/owr-payload')
shutil.move('/tmp/owr-payload/code','/opt/owr')
run('chmod','-R','a+rX,go-w','/opt/owr');Path('/etc/owr').mkdir()
examples=Path('/opt/owr/examples/daily-status-transfer')
if role=='source':
    shutil.move('/tmp/owr-payload/state','/var/lib/owr-daily')
    for group in ('owr-status-read','owr-ledger-read'):run('groupadd','--system',group)
    for user,supp in [('owr-status-publisher','owr-ledger-read'),('owr-status-reader',None)]:
        run('useradd','--system','--no-create-home','--shell','/bin/sh','--gid','owr-status-read',*(['--groups',supp] if supp else []),user)
        run('usermod','-p','*',user)
    run('chown','-R','root:owr-ledger-read','/var/lib/owr-daily')
    for p in [Path('/var/lib/owr-daily'),*Path('/var/lib/owr-daily').rglob('*')]:
        p.chmod(0o750 if p.is_dir() else 0o640)
    path=Path('/var/lib/owr-status-source');path.mkdir();run('chown','owr-status-publisher:owr-status-read',str(path));path.chmod(0o2750)
    for mode in ('publish','read'):
        p=Path('/etc/owr')/('daily-status-'+mode+'.json');shutil.copyfile(examples/p.name,p);p.chmod(0o640);run('chown','root:owr-status-read',str(p))
    Path('/etc/ssh/sshd_config.d/80-owr-reader.conf').write_text('Match User owr-status-reader\n    AuthorizedKeysFile /etc/owr/daily-status-authorized-keys\n    AuthenticationMethods publickey\n    DisableForwarding yes\n    PermitTTY no\nMatch all\n')
    run('sshd','-t');run('systemctl','reload','ssh')
    unit='owr-daily-status-publisher.service'
    hashes={str(p.relative_to('/var/lib/owr-daily')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/var/lib/owr-daily').rglob('*') if p.is_file()}
    Path('/root/source-before.json').write_text(json.dumps(hashes,sort_keys=True))
else:
    assert not Path('/tmp/owr-payload/state').exists()
    run('groupadd','--system','owr-status-relay')
    run('useradd','--system','--no-create-home','--shell','/bin/sh','--gid','www-data','--groups','owr-status-relay','owr-status-relay')
    path=Path('/var/lib/owr-status-web');path.mkdir();run('chown','owr-status-relay:www-data',str(path));path.chmod(0o2750)
    data=json.loads((examples/'daily-status-relay.json').read_text());data['host']='192.0.2.10'
    p=Path('/etc/owr/daily-status-relay.json');p.write_text(json.dumps(data));p.chmod(0o640);run('chown','root:owr-status-relay',str(p))
    run('ssh-keygen','-q','-t','ed25519','-N','','-f','/etc/owr/daily-status-client')
    run('chown','owr-status-relay:owr-status-relay','/etc/owr/daily-status-client');Path('/etc/owr/daily-status-client').chmod(0o600)
    unit='owr-daily-status-relay.service'
target=Path('/etc/systemd/system')/unit;shutil.copyfile(examples/unit,target);target.chmod(0o644)
run('systemctl','daemon-reload');run('systemd-analyze','verify',str(target))
print('prepared '+role)
