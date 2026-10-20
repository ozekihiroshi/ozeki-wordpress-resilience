import os
import json,subprocess
from pathlib import Path
out=Path(os.environ.get('OWR_VM_LAB_OUTPUT', str(Path.home()/'.local/share/owr-production-systemd-vm-20261020'))).expanduser().resolve()
cmd=['docker','exec',(out/'container-name').read_text(),*json.loads((out/'ssh-command.json').read_text()),
     'sudo systemctl status owr-daily-status-publisher owr-daily-status-relay --no-pager; sudo cat /var/lib/owr-status-web/transfer.json; sudo cat /var/lib/owr-status-source/producer.json']
p=subprocess.run(cmd,capture_output=True,timeout=20)
print(p.stdout.decode()[-6000:]);print(p.stderr.decode()[-1000:])
