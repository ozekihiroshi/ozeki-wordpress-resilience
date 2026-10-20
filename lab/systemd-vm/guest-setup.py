import os
"""Run only as root inside disposable OWR VM."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
def run(*args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
assert os.geteuid()==0 and Path('/etc/hostname').read_text().strip()=='owr-dedicated-vm'
run('mkdir','-p','/tmp/owr-payload')
run('tar','xf','/tmp/payload.tar','-C','/tmp/owr-payload')
shutil.move('/tmp/owr-payload/code','/opt/owr')
shutil.move('/tmp/owr-payload/state','/var/lib/owr-daily')
for group in ('owr-status-read','owr-ledger-read','owr-status-relay'):
    run('groupadd','--system',group)
for user,group,supp in [('owr-status-publisher','owr-status-read','owr-ledger-read'),
                        ('owr-status-reader','owr-status-read',None),
                        ('owr-status-relay','www-data','owr-status-relay')]:
    run('useradd','--system','--no-create-home','--shell','/bin/sh','--gid',group,*(['--groups',supp] if supp else []),user)
    run('usermod','-p','*',user)
run('chown','-R','root:owr-ledger-read','/var/lib/owr-daily')
for p in [Path('/var/lib/owr-daily'),*Path('/var/lib/owr-daily').rglob('*')]:
    p.chmod(0o750 if p.is_dir() else 0o640)
run('chmod','-R','a+rX,go-w','/opt/owr')
for path,owner in [('/var/lib/owr-status-source','owr-status-publisher:owr-status-read'),
                   ('/var/lib/owr-status-web','owr-status-relay:www-data')]:
    Path(path).mkdir();run('chown',owner,path);Path(path).chmod(0o2750)
Path('/etc/owr').mkdir()
examples=Path('/opt/owr/examples/daily-status-transfer')
for name,group in [('publish','owr-status-read'),('read','owr-status-read'),('relay','owr-status-relay')]:
    data=json.loads((examples/('daily-status-'+name+'.json')).read_text())
    if name=='relay':data['host']='127.0.0.1'
    path=Path('/etc/owr')/('daily-status-'+name+'.json')
    path.write_text(json.dumps(data));path.chmod(0o640);run('chown','root:'+group,str(path))
run('ssh-keygen','-q','-t','ed25519','-N','','-f','/etc/owr/daily-status-client')
run('chown','owr-status-relay:owr-status-relay','/etc/owr/daily-status-client')
Path('/etc/owr/daily-status-client').chmod(0o600)
Path('/etc/owr/daily-status-authorized-keys').write_text(
    'restrict,command="/usr/bin/python3 /opt/owr/tools/daily-status-transfer.py --config /etc/owr/daily-status-read.json serve" '+
    Path('/etc/owr/daily-status-client.pub').read_text())
Path('/etc/owr/daily-status-known-hosts').write_text('owr-daily-generated-first-site '+Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text())
run('chown','root:owr-status-relay','/etc/owr/daily-status-known-hosts')
Path('/etc/owr/daily-status-known-hosts').chmod(0o640)
Path('/etc/ssh/sshd_config.d/80-owr-reader.conf').write_text('Match User owr-status-reader\n    AuthorizedKeysFile /etc/owr/daily-status-authorized-keys\n    AuthenticationMethods publickey\n    DisableForwarding yes\n    PermitTTY no\nMatch all\n')
run('sshd','-t')
run('systemctl','reload','ssh')
units=['owr-daily-status-publisher.service','owr-daily-status-relay.service']
for name in units:
    target=Path('/etc/systemd/system')/name
    shutil.copy2(examples/name,target)
    target.chmod(0o644)
Path('/etc/owr/world-writable-probe').write_text('dedicated fixture');Path('/etc/owr/world-writable-probe').chmod(0o666)
Path('/home/owr-home-probe').mkdir(mode=0o755)
Path('/home/owr-home-probe/readable').write_text('dedicated fixture')
Path('/home/owr-home-probe/readable').chmod(0o644)
Path('/tmp/owr-host-tmp-probe').write_text('dedicated fixture')
Path('/tmp/owr-host-tmp-probe').chmod(0o644)
run('systemctl','daemon-reload')
run('systemd-analyze','verify',*[str(Path('/etc/systemd/system')/n) for n in units])
run('systemctl','enable','--now',*units)
hashes={str(p.relative_to('/var/lib/owr-daily')):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/var/lib/owr-daily').rglob('*') if p.is_file()}
Path('/root/owr-source-before.json').write_text(json.dumps(hashes,sort_keys=True))
print('production example services enabled unchanged; dedicated configuration installed')
