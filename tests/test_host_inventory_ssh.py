import importlib.util, json, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('hostssh',ROOT/'tools/host-inventory-ssh.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class HostSSHTests(unittest.TestCase):
 def setUp(self):
  self.c=dict(site_id='site',host='127.0.0.1',user='inspector',port=2222,identity_file='/key',known_hosts='/known')
 def test_restrictions(self):
  cmd=m.command(self.c)
  for flag in ['StrictHostKeyChecking=yes','IdentityAgent=none','BatchMode=yes','ClearAllForwardings=yes','HostKeyAlias=owr-inventory-site','IdentitiesOnly=yes']:self.assertIn(flag,cmd)
  self.assertEqual(cmd[-1],'host-inventory')
 def test_endpoint_binding(self):
  for p in [{},{'site_id':'wrong','config_sha256':'a'*64,'nonce':'a'*32},{'site_id':'site','config_sha256':'b'*64,'nonce':'a'*32},{'site_id':'site','config_sha256':'a'*64,'nonce':'$(id)'}]:
   with self.assertRaises(ValueError):m.endpoint(dict(site_id='site',config_sha256='a'*64),p)
 def test_injection(self):
  for k,v in [('host','-oProxyCommand=id'),('user','x;id'),('port',True)]:
   with self.assertRaises(ValueError):m.command(dict(self.c,**{k:v}))
 def test_failures_no_stale_success(self):
  c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
  c['storage']['destination_ref']='generated';c['trust'].update(operator='lab',public_pin_ref='generated')
  conn=dict(self.c,site_id=c['site_id'])
  import tempfile
  with tempfile.TemporaryDirectory() as work:
   for error in [TimeoutError(),RuntimeError(),ValueError(),OSError()]:
    def fail(*args):raise error
    r=m.inspect(conn,c,{},work,fail)
    self.assertEqual(r['host_observation']['state'],'unavailable');self.assertFalse(r['production_ready']);self.assertNotIn('transport',r)
if __name__=='__main__':unittest.main()
