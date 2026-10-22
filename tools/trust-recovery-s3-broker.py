"""Dedicated test broker: existing real S3 reader, exact locator allow-list, no secrets in guest."""
import importlib.util,json,os,socketserver,threading
from pathlib import Path
s=importlib.util.spec_from_file_location('real_reader',Path(__file__).with_name('queue-s3-adapter.py'));a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Broker:
 def __init__(self,workspace,manifest):
  self.root=Path(workspace);self.allow=[e['locator'] for e in manifest['assets']];self.events=[];self.adapter=a.S3Adapter(self.root/'real-reader-receipts')
  owner=self
  class Handler(socketserver.StreamRequestHandler):
   def handle(self):
    try:
     loc=json.loads(self.rfile.readline(8193));assert loc in owner.allow and len(owner.events)<2
     event={'locator':loc,'state':'started'};owner.events.append(event);owner.save()
     result=owner.adapter.get(loc);body=result.pop('body');path=owner.root/('download-'+str(len(owner.events))+'.bin');path.write_bytes(body);path.chmod(0o600)
     event['state']='received';owner.save();response=dict(result,body_file=str(path))
    except Exception:response={'error':'real S3 retrieval failed; inspect dedicated receipts before retry'}
    self.wfile.write(json.dumps(response).encode()+b'\n')
  self.server=socketserver.UnixStreamServer(str(self.root/'s3-reader.sock'),Handler);os.chmod(self.root/'s3-reader.sock',0o600)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def save(self):(self.root/'real-get-events.json').write_text(json.dumps(self.events,indent=2))
 def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
