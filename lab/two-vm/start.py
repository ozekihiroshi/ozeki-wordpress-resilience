import hashlib,json,os,secrets,shutil,tarfile,time
from pathlib import Path
from common import OUT,run,ex,start,wait_ssh,remote
ROOT=Path(__file__).resolve().parents[2]
OUT.mkdir(mode=0o700,parents=True,exist_ok=False)
container='owr-two-vm-'+secrets.token_hex(5)
(OUT/'container-name').write_text(container)
(OUT/'host-boot-before').write_text(Path('/proc/sys/kernel/random/boot_id').read_text())
image=Path.home()/'.local/share/owr-vm-images'
meta=json.loads((image/'image-source.json').read_text())
assert hashlib.file_digest((image/'noble-server-cloudimg-amd64.img').open('rb'),'sha256').hexdigest()==meta['sha256']
(OUT/'image-source.json').write_text(json.dumps(meta))
source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
(OUT/'source-hashes.json').write_text(json.dumps({str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}))
for role in ('source','receiver'):
    p=OUT/role;p.mkdir(mode=0o700)
    for key in ('admin','host'):run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(p/key))
    user={'name':'lab','sudo':'ALL=(ALL) NOPASSWD:ALL','shell':'/bin/bash','lock_passwd':True,
          'ssh_authorized_keys':[(p/'admin.pub').read_text().strip()]}
    cloud={'users':[user],'ssh_pwauth':False,'disable_root':True,'ssh_deletekeys':False,
           'ssh_keys':{'ed25519_private':(p/'host').read_text(),'ed25519_public':(p/'host.pub').read_text().strip()}}
    (p/'user-data').write_text('#cloud-config\n'+json.dumps(cloud))
    (p/'meta-data').write_text('instance-id: '+container+'-'+role+'\nlocal-hostname: owr-two-'+role+'\n')
    number=1 if role=='source' else 2
    mac1='52:54:00:12:0'+str(number)+':01';mac2='52:54:00:12:0'+str(number)+':02'
    net={'version':2,'ethernets':{'mgmt0':{'match':{'macaddress':mac1},'set-name':'mgmt0','dhcp4':True},
        'data0':{'match':{'macaddress':mac2},'set-name':'data0','addresses':['192.0.2.'+('10' if role=='source' else '20')+'/24'],'optional':True}}}
    (p/'network-config').write_text(json.dumps(net))
    port=2222 if role=='source' else 2223
    (p/'known_hosts').write_text('[127.0.0.1]:'+str(port)+' '+(p/'host.pub').read_text())
    (p/'ssh.json').write_text(json.dumps(['ssh','-i','/lab/'+role+'/admin','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes',
        '-o','UserKnownHostsFile=/lab/'+role+'/known_hosts','-o','ConnectTimeout=5','-p',str(port),'lab@127.0.0.1']))
    with tarfile.open(p/'payload.tar','w') as t:
        for item in ('tools','schemas','examples/daily-status-transfer'):t.add(ROOT/item,arcname='code/'+item)
        if role=='source':t.add(source,arcname='state')
    args=['qemu-system-x86_64','-enable-kvm','-cpu','host','-smp','1','-m','1024','-display','none','-daemonize',
          '-pidfile','/lab/'+role+'/qemu.pid','-serial','file:/lab/'+role+'/serial.log',
          '-qmp','unix:/lab/'+role+'/qmp.sock,server=on,wait=off',
          '-drive','file=/lab/'+role+'/disk.qcow2,if=virtio,format=qcow2',
          '-drive','file=/lab/'+role+'/seed.iso,media=cdrom,readonly=on',
          '-netdev','user,id=mgmt,restrict=on,hostfwd=tcp:127.0.0.1:'+str(port)+'-:22',
          '-device','virtio-net-pci,netdev=mgmt,mac='+mac1,
          '-netdev','stream,id=data,server='+('on' if role=='source' else 'off')+',addr.type=inet,addr.host=127.0.0.1,addr.port=17000'+('' if role=='source' else ',reconnect-ms=1000'),
          '-device','virtio-net-pci,id=data0,netdev=data,mac='+mac2]
    (p/'qemu.json').write_text(json.dumps(args))
run('docker','run','-d','--name',container,'--network','none','--memory','3200m','--cpus','2','--device','/dev/kvm',
    '-v',str(OUT)+':/lab','-v',str(image)+':/images:ro','--entrypoint','sleep','owr-systemd-vm:lab','infinity')
for role in ('source','receiver'):
    ex('genisoimage','-quiet','-output','/lab/'+role+'/seed.iso','-volid','cidata','-joliet','-rock',
       '/lab/'+role+'/user-data','/lab/'+role+'/meta-data','/lab/'+role+'/network-config')
    ex('qemu-img','create','-f','qcow2','-F','qcow2','-b','/images/noble-server-cloudimg-amd64.img','/lab/'+role+'/disk.qcow2','8G')
    start(role)
for role in ('source','receiver'):
    wait_ssh(role)
    remote(role,'sudo cloud-init status --wait',timeout=120)
    port='2222' if role=='source' else '2223'
    ex('scp','-i','/lab/'+role+'/admin','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/'+role+'/known_hosts',
       '-P',port,'/lab/'+role+'/payload.tar','lab@127.0.0.1:/tmp/payload.tar')
    print('VM_READY '+role,flush=True)
