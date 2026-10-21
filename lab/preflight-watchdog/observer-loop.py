"""Independent observer and local HTTP notification receiver, outside both guests."""
import importlib.util
import json
import os
from pathlib import Path
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen

ROOT = Path('/lab/watchdog')
spec = importlib.util.spec_from_file_location('observer', '/lab/code/tools/watchdog-observer.py')
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if (ROOT/'fail-delivery').exists():
            self.send_response(503); self.end_headers(); return
        event = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        with (ROOT/'delivered.jsonl').open('a') as f:
            f.write(json.dumps(event)+'\n'); f.flush(); os.fsync(f.fileno())
        self.send_response(204); self.end_headers()
    def log_message(self, *args): pass
server = HTTPServer(('127.0.0.1', 18765), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
def send(event):
    with urlopen(Request('http://127.0.0.1:18765/', data=json.dumps(event).encode(),
                         headers={'Content-Type':'application/json'}), timeout=3) as response:
        assert response.status == 204
while not (ROOT/'stop').exists():
    for role in ('source', 'receiver'):
        result = observer.observe(json.loads((ROOT/(role+'.json')).read_text()), sender=send)
        observer.transfer.atomic(ROOT/(role+'-status.json'), result)
    observer.transfer.atomic(ROOT/'loop-tick.json', dict(pid=os.getpid(), at=datetime.now(timezone.utc).isoformat()))
    time.sleep(3)
