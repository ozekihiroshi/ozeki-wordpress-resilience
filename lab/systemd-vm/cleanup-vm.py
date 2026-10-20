import os
"""Power off only the recorded dedicated VM; retain private evidence/disks."""
import json,subprocess,time
from pathlib import Path
out=Path(os.environ.get('OWR_VM_LAB_OUTPUT', str(Path.home()/'.local/share/owr-production-systemd-vm-20261020'))).expanduser().resolve()
name=(out/'container-name').read_text()
assert name.startswith('owr-production-vm-') and name.replace('-','').isalnum()
def run(*args,**kw):return subprocess.run(args,capture_output=True,timeout=30,**kw)
info=json.loads(run('docker','inspect',name,check=True).stdout)[0]
assert info['HostConfig']['NetworkMode']=='none'
assert info['Config']['Image']=='owr-systemd-vm:lab'
assert any(m['Source']==str(out) and m['Destination']=='/lab' for m in info['Mounts'])
ssh=json.loads((out/'ssh-command.json').read_text())
p=run('docker','exec',name,*ssh,'hostname',check=True)
assert p.stdout.decode().strip()=='owr-dedicated-vm'
run('docker','exec',name,*ssh,'sudo systemctl poweroff')
# Allow guest shutdown, but never stop the enclosing WSL or Docker daemon.
time.sleep(4)
run('docker','rm','-f','-v',name,check=True)
assert run('docker','inspect',name).returncode!=0
(out/'cleanup.json').write_text(json.dumps(dict(vm_removed=True,host_rebooted=False,evidence_retained=True)))
print('Dedicated VM container removed; private evidence retained.')
