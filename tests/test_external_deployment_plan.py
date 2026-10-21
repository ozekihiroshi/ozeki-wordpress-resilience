import copy, hashlib, importlib.util, json, os, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('plan',ROOT/'tools/external-deployment-plan.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DeploymentPlan(unittest.TestCase):
 def setUp(self):
  self.profile=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
  self.top=dict(format='owr-deployment-topology-v1',site_id=self.profile['site_id'],hosts={k:dict(host=k+'.example.invalid',port=22,user='inspector' if k=='inventory' else 'owr-status') for k in m.ROLES})
 def build(self):return m.compile_plan(self.profile,self.top)
 def test_deterministic(self):self.assertEqual(self.build(),self.build())
 def test_not_ready(self):
  p,f=self.build();self.assertFalse(p['production_ready']);self.assertFalse(p['apply_supported']);self.assertEqual(p['state'],'requires_operator_configuration')
 def test_no_password(self):
  p,f=self.build();v=json.loads(f['inventory/endpoint.draft.json']);self.assertIsNone(v['probe']['DB_PASSWORD']);self.assertIsNone(v['probe']['DB_USER'])
 def test_notification_blocker(self):
  p,f=self.build();self.assertTrue(any(x['code']=='notifications_not_configured' for x in p['required_actions']));self.assertNotIn('alerts',json.loads(f['observer/source-observer.json']))
 def test_hashes(self):
  p,f=self.build()
  for x in p['files']:self.assertEqual(x['sha256'],hashlib.sha256(f[x['file']]).hexdigest())
 def test_no_shared_output_on_same_host(self):
  p,f=self.build();targets=[(x['role'],x['target']) for x in p['files']];self.assertEqual(len(targets),len(set(targets)))
 def test_bindings(self):
  p,f=self.build()
  for role in ('scanner','wordpress'):
   v=json.loads(f[role+'/watchdog-probe.json']);self.assertEqual(v['config_sha256'],p['config_sha256']);self.assertEqual(v['site_id'],p['site_id'])
  for side in ('source','receiver'):
   observe=json.loads(f['observer/'+side+'-observer.json']);pull=json.loads(f['wordpress/'+side+'-pull.json']);self.assertEqual(observe['monitor_id'],pull['monitor_id']);self.assertEqual(observe['ssh']['site_id'],observe['monitor_id'])
 def test_profile_change_changes_binding(self):
  p,_=self.build();self.profile['operations']['owner']='another';q,_=self.build();self.assertNotEqual(p['config_sha256'],q['config_sha256'])
 def test_host_injection(self):
  self.top['hosts']['scanner']['host']='x;touch /tmp/test'
  with self.assertRaises(ValueError):self.build()
 def test_unknown_field_secret_refused(self):
  self.top['password']='not-a-real-secret'
  with self.assertRaises(ValueError):self.build()
 def test_port_bool(self):
  self.top['hosts']['observer']['port']=True
  with self.assertRaises(ValueError):self.build()
 def test_wrong_site(self):
  self.top['site_id']='other'
  with self.assertRaises(ValueError):self.build()
 def test_shared_observer(self):
  self.top['hosts']['observer']['host']=self.top['hosts']['scanner']['host']
  with self.assertRaises(ValueError):self.build()
 def test_missing_role(self):
  del self.top['hosts']['inventory']
  with self.assertRaises(ValueError):self.build()
 def test_generate_private_and_refuse_overwrite(self):
  p,f=self.build()
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'bundle';m.generate(p,f,out);before={x.relative_to(out):x.read_bytes() for x in out.rglob('*') if x.is_file()}
   for x in out.rglob('*'):self.assertEqual(x.stat().st_mode & 0o777,0o700 if x.is_dir() else 0o600)
   with self.assertRaises(ValueError):m.generate(p,f,out)
   self.assertEqual(before,{x.relative_to(out):x.read_bytes() for x in out.rglob('*') if x.is_file()})
 def test_symlink_output_parent(self):
  p,f=self.build()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'link').symlink_to(root,target_is_directory=True)
   with self.assertRaises(ValueError):m.generate(p,f,root/'link'/'bundle')
 def test_relative_output(self):
  p,f=self.build()
  with self.assertRaises(ValueError):m.generate(p,f,'relative')
 def test_readonly_compilation(self):
  a=copy.deepcopy(self.profile);b=copy.deepcopy(self.top);self.build();self.assertEqual(a,self.profile);self.assertEqual(b,self.top)
 def test_existing_transport_contracts(self):
  p,f=self.build();wire=m.pre.capture # Validate via the exact transport argument builder, no SSH process.
  s=importlib.util.spec_from_file_location('transfer',ROOT/'tools/notification-transfer.py');t=importlib.util.module_from_spec(s);s.loader.exec_module(t)
  for n in ('scanner/inventory-ssh.json','wordpress/receiver.json','wordpress/source-pull.json','wordpress/receiver-pull.json'):
   argv=t.command(json.loads(f[n]));self.assertIn('StrictHostKeyChecking=yes',argv);self.assertIn('IdentityAgent=none',argv)
if __name__=='__main__':unittest.main()
