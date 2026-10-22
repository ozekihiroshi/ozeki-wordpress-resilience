import contextlib,importlib.util,io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('ssh_update',Path(__file__).resolve().parents[1]/'tools/trust-registry-ssh.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Protocol(unittest.TestCase):
 def call(self,args,endpoint=None,transport=None):
  out=io.StringIO();stdin=io.TextIOWrapper(io.BytesIO(b'{}'))
  with patch.object(sys,'argv',['tool',*args]),patch.object(sys,'stdin',stdin),contextlib.redirect_stdout(out),patch.object(m,'endpoint',side_effect=endpoint),patch.object(m.t,'ssh',side_effect=transport),patch.object(m.t,'read_file',return_value={}):code=m.main()
  return code,json.loads(out.getvalue())
 def test_endpoint_rejection_is_delivered(self):
  code,x=self.call(['endpoint'],endpoint=ValueError('rejected'));self.assertEqual((code,x['state']),(0,'rejected'))
 def test_endpoint_io_unknown_is_delivered(self):
  code,x=self.call(['endpoint'],endpoint=OSError('io'));self.assertEqual((code,x['state']),(0,'unknown'))
 def test_client_preserves_rejection(self):
  code,x=self.call(['inspect','--connection','unused'],transport=lambda *a:{'state':'rejected'});self.assertEqual((code,x['state']),(2,'rejected'))
 def test_client_disconnect_unknown(self):
  code,x=self.call(['inspect','--connection','unused'],transport=TimeoutError());self.assertEqual((code,x['state']),(2,'unknown'))
if __name__=='__main__':unittest.main()
