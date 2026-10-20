import os
import hashlib,json,os,secrets,shutil,subprocess,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ.get('OWR_VM_LAB_OUTPUT', str(Path.home()/'.local/share/owr-production-systemd-vm-20261020'))).expanduser().resolve()
def run(*args,check=True,timeout=120):
    p=subprocess.run(args,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(p.stderr.decode()[-1800:])
    return p
OUT.mkdir(mode=0o700,parents=True,exist_ok=False)
name='owr-production-vm-'+secrets.token_hex(5)
(OUT/'container-name').write_text(name)
for k in ('admin','host'):
    run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(OUT/k))
user={'name':'lab','sudo':'ALL=(ALL) NOPASSWD:ALL','shell':'/bin/bash','lock_passwd':True,
      'ssh_authorized_keys':[(OUT/'admin.pub').read_text().strip()]}
cloud={'users':[user],'ssh_pwauth':False,'disable_root':True,'ssh_deletekeys':False,
       'ssh_keys':{'ed25519_private':(OUT/'host').read_text(),'ed25519_public':(OUT/'host.pub').read_text().strip()},
       'write_files':[{'path':'/etc/ssh/sshd_config.d/90-owr-lab.conf','content':'PasswordAuthentication no\nKbdInteractiveAuthentication no\n'}]}
(OUT/'user-data').write_text('#cloud-config\n'+json.dumps(cloud))
(OUT/'meta-data').write_text('instance-id: '+name+'\nlocal-hostname: owr-dedicated-vm\n')
(OUT/'known_hosts').write_text('[127.0.0.1]:2222 '+(OUT/'host.pub').read_text())
image=Path.home()/'.local/share/owr-vm-images'
shutil.copy2(image/'image-source.json',OUT/'image-source.json')
source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
(OUT/'source-hashes.json').write_text(json.dumps(hashes,sort_keys=True))
with tarfile.open(OUT/'payload.tar','w') as t:
    for n in ('tools','schemas','examples/daily-status-transfer'):
        t.add(ROOT/n,arcname='code/'+n)
    t.add(source,arcname='state')
run('docker','run','-d','--name',name,'--network','none','--memory','2300m','--cpus','2',
    '--device','/dev/kvm','-v',str(OUT)+':/lab','-v',str(image)+':/images:ro',
    '--entrypoint','sleep','owr-systemd-vm:lab','infinity')
def ex(*args,**kw):return run('docker','exec',name,*args,**kw)
ex('genisoimage','-quiet','-output','/lab/seed.iso','-volid','cidata','-joliet','-rock','/lab/user-data','/lab/meta-data')
ex('qemu-img','create','-f','qcow2','-F','qcow2','-b','/images/noble-server-cloudimg-amd64.img','/lab/disk.qcow2','8G')
ex('qemu-system-x86_64','-enable-kvm','-cpu','host','-smp','2','-m','1536','-display','none','-daemonize',
   '-pidfile','/lab/qemu.pid','-serial','file:/lab/serial.log',
   '-drive','file=/lab/disk.qcow2,if=virtio,format=qcow2',
   '-drive','file=/lab/seed.iso,media=cdrom,readonly=on',
   '-netdev','user,id=n0,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22','-device','virtio-net-pci,netdev=n0')
ssh=['ssh','-i','/lab/admin','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','ConnectTimeout=5','-p','2222','lab@127.0.0.1']
(OUT/'ssh-command.json').write_text(json.dumps(ssh))
deadline=time.monotonic()+240
while True:
    p=ex(*ssh,'true',check=False,timeout=12)
    if p.returncode==0:break
    if time.monotonic()>deadline:raise RuntimeError('VM SSH boot deadline; inspect dedicated serial.log')
    time.sleep(3)
ex(*ssh,'sudo cloud-init status --wait',timeout=120)
ex(*ssh,'uname -r; cat /proc/sys/kernel/random/boot_id')
ex('scp','-i','/lab/admin','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-P','2222','/lab/payload.tar','lab@127.0.0.1:/tmp/payload.tar')
print(json.dumps({'vm_ready':True,'container':name,'output':str(OUT)}),flush=True)
