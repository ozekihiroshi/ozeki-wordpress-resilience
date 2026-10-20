import json
from common import OUT,name,run,remote,poweroff
n=name()
assert n.startswith('owr-two-vm-') and n.replace('-','').isalnum()
info=json.loads(run('docker','inspect',n).stdout)[0]
assert info['HostConfig']['NetworkMode']=='none' and info['Config']['Image']=='owr-systemd-vm:lab'
assert any(m['Source']==str(OUT) and m['Destination']=='/lab' for m in info['Mounts'])
for role in ('source','receiver'):
    assert remote(role,'hostname').stdout.decode().strip()=='owr-two-'+role
for role in ('receiver','source'):poweroff(role)
run('docker','rm','-f','-v',n)
assert run('docker','inspect',n,check=False).returncode!=0
(OUT/'cleanup.json').write_text(json.dumps(dict(removed=True,guests=2,host_rebooted=False,private_evidence_retained=True)))
print('Both dedicated guests and enclosing container removed; evidence retained.')
