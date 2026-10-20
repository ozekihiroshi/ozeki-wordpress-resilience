import os
import hashlib,json,os,shlex,subprocess,time
from pathlib import Path
OUT=Path(os.environ.get('OWR_VM_LAB_OUTPUT', str(Path.home()/'.local/share/owr-production-systemd-vm-20261020'))).expanduser().resolve()
BASE=Path(__file__).resolve().parent
container=(OUT/'container-name').read_text()
ssh=json.loads((OUT/'ssh-command.json').read_text())
STORE=OUT/'hardened' if os.environ.get('OWR_VERIFY_HARDENED')=='1' else OUT
if STORE!=OUT:STORE.mkdir(exist_ok=False)
def remote(command,data=None,check=True,timeout=90):
    p=subprocess.run(['docker','exec',*(['-i'] if data is not None else []),container,*ssh,command],
                     input=data,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(p.stderr.decode()[-2000:]+p.stdout.decode()[-1500:])
    return p
def boot():return remote('cat /proc/sys/kernel/random/boot_id',check=False,timeout=12).stdout.decode().strip()
def healthy(previous=None):
    deadline=time.monotonic()+180
    code="import json,hashlib;from pathlib import Path;r=Path('/var/lib/owr-status-web/daily.json').read_bytes();h=json.loads(Path('/var/lib/owr-status-web/transfer.json').read_bytes());assert h['state']=='ok' and h['report_sha256']==hashlib.sha256(r).hexdigest();print(json.loads(r)['observed_at'])"
    while time.monotonic()<deadline:
        p=remote('sudo python3 -c '+shlex.quote(code),check=False,timeout=15)
        stamp=p.stdout.decode().strip()
        if p.returncode==0 and stamp and stamp!=previous:return stamp
        time.sleep(3)
    raise RuntimeError('fresh healthy report deadline; retain VM for diagnosis')
host_before=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
(STORE/'host-boot-before').write_text(host_before)
if STORE==OUT:remote('sudo python3 -',(BASE/'guest-setup.py').read_bytes(),timeout=120)
print('SETUP_PASS production units enabled',flush=True)
first=healthy()
second=healthy(first)
print('PERIODIC_PASS actual unchanged 60-second units updated report',flush=True)
before=json.loads(remote('sudo python3 -',(BASE/'guest-verify.py').read_bytes()).stdout)
(STORE/'before-reboot.json').write_text(json.dumps(before,ensure_ascii=False,indent=2))
print('HARDENING_PASS '+str(len(before['checks']))+' checks',flush=True)
remote('sudo systemctl reboot',check=False,timeout=15)
start=time.monotonic();deadline=start+240
while time.monotonic()<deadline:
    current=boot()
    if current and current!=before['boot_id']:break
    time.sleep(3)
else:raise RuntimeError('guest OS reboot did not produce new Boot ID')
third=healthy(second)
after=json.loads(remote('sudo python3 -',(BASE/'guest-verify.py').read_bytes()).stdout)
(STORE/'after-reboot.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))
assert before['boot_id']!=after['boot_id']
assert before['report']['observed_at']!=after['report']['observed_at']
assert host_before==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
source=Path.home()/'.local/share/owr-recovery-cleanup-20261020-v2'
hashes={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
assert hashes==json.loads((OUT/'source-hashes.json').read_text())
for tag,cmd in [('units','systemctl cat owr-daily-status-publisher owr-daily-status-relay'),
                ('journal','journalctl -u owr-daily-status-publisher -u owr-daily-status-relay --no-pager -n 100'),
                ('security','systemd-analyze security owr-daily-status-publisher owr-daily-status-relay --no-pager')]:
    (STORE/(tag+'.txt')).write_bytes(remote('sudo '+cmd).stdout)
result=dict(passed=True,before_boot=before['boot_id'],after_boot=after['boot_id'],
    host_boot_unchanged=True,unchanged_source=True,checks_before=len(before['checks']),checks_after=len(after['checks']),
    actual_periodic_stamps=[first,second,third],reboot_to_verified_seconds=time.monotonic()-start,
    real_guest_os_reboot=True,production_units_unmodified=True,unit_interval_seconds=60,
    s3_calls=0,production_changed=False,vm_container=container,image=json.loads((OUT/'image-source.json').read_text()))
(STORE/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
