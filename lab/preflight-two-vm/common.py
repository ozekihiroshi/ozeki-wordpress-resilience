import json,os,subprocess,time,shlex
from pathlib import Path
OUT=Path(os.environ.get('OWR_TWO_VM_OUTPUT',str(Path.home()/'.local/share/owr-two-vm-20261021'))).resolve()
def run(*args,data=None,check=True,timeout=120):
    p=subprocess.run(args,input=data,capture_output=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError(p.stderr.decode()[-2000:]+p.stdout.decode()[-1000:])
    return p
def name():return (OUT/'container-name').read_text().strip()
def ex(*args,**kw):return run('docker','exec',*(['-i'] if kw.get('data') is not None else []),name(),*args,**kw)
def remote(role,command,**kw):
    return ex(*json.loads((OUT/role/'ssh.json').read_text()),command,**kw)
def boot(role):
    return remote(role,'cat /proc/sys/kernel/random/boot_id',check=False,timeout=12).stdout.decode().strip()
def wait_ssh(role,old=None):
    end=time.monotonic()+240
    while time.monotonic()<end:
        b=boot(role)
        if b and (old is None or b!=old):return b
        time.sleep(3)
    raise RuntimeError(role+' boot deadline; preserve output and inspect serial log')
def cat(role,path):
    return remote(role,'sudo cat '+shlex.quote(path)).stdout
def qmp(role,command,args):
    code="""import json,socket
s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect(%r)
f=s.makefile('rwb');json.loads(f.readline())
for req in [{'execute':'qmp_capabilities'},{'execute':%r,'arguments':%r}]:
 f.write(json.dumps(req).encode()+b'\\n');f.flush()
 while True:
  v=json.loads(f.readline())
  if 'error' in v:raise RuntimeError(v['error'])
  if 'return' in v:break
print('QMP_OK')
"""%('/lab/'+role+'/qmp.sock',command,args)
    return ex('python3','-c',code)
def start(role):
    return ex(*json.loads((OUT/role/'qemu.json').read_text()))
def poweroff(role):
    remote(role,'sudo systemctl poweroff',check=False,timeout=15)
    end=time.monotonic()+90
    while time.monotonic()<end:
        code="from pathlib import Path;p=Path('/lab/"+role+"/qemu.pid');s=p.read_text().strip() if p.exists() else '';f=Path('/proc/'+s+'/cmdline');print(int(f.exists() and b'/lab/"+role+"/disk.qcow2' in f.read_bytes()))"
        if ex('python3','-c',code).stdout.strip()==b'0':return
        time.sleep(2)
    raise RuntimeError('guest failed to power off: '+role)
