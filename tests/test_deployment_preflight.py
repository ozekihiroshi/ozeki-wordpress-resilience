import copy, hashlib, importlib.util, json, os, subprocess, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('preflight',ROOT/'tools/deployment-preflight.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class Preflight(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.work=self.root/'work';self.work.mkdir(mode=0o700)
  self.c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
  self.c['storage']['destination_ref']='generated-storage';self.c['trust'].update(operator='lab-operator',public_pin_ref='generated-pin')
  self.now=datetime.now(timezone.utc)
  self.v={k:copy.deepcopy(self.c[k]) for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')}
  self.v.update(format='owr-deployment-inventory-v1',config_sha256=m.capture.digest(self.c),observed_at=self.now.isoformat(),incomplete_runs=0,uncertain_puts=0)
 def tearDown(self):self.tmp.cleanup()
 def check(self,code):self.assertIn(code,[x['code'] for x in m.assess(self.c,self.v,self.work,self.now)['issues']])
 def test_eligible_never_production(self):
  r=m.assess(self.c,self.v,self.work,self.now);self.assertEqual(r['state'],'eligible_for_dedicated_trial');self.assertFalse(r['production_ready']);self.assertFalse(r['capture_started']);self.assertIn('s3_permissions_and_retention',r['not_verified'])
 def test_original_example_is_unconfigured(self):
  self.c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());self.check('storage_destination_ref_unset');self.check('trust_public_pin_ref_unset')
 def test_unsupported(self):
  for group,key,value in [('wordpress','multisite',True),('database','engines',['MyISAM']),('files','exclusions',['uploads']),('queue','state','present')]:
   with self.subTest(group=group):
    c=copy.deepcopy(self.c);c[group][key]=value;self.assertEqual(m.assess(c,self.v,self.work,self.now)['state'],'unsupported')
 def test_external_dependencies(self):
  self.c['dependencies']=['redis'];self.check('unsupported_dependencies')
 def test_missing_writer(self):
  del self.c['writers']['direct_db'];self.check('writer_scope_incomplete')
 def test_extra_observed_writer(self):
  self.v['writers']['unknown']={};self.check('writers_inventory_mismatch')
 def test_all_inventory_groups(self):
  for group in ('wordpress','database','files','queue','dependencies','runtime'):
   with self.subTest(group=group):
    old=self.v[group];self.v[group]=None;self.check(group+'_inventory_mismatch');self.v[group]=old
 def test_wrong_binding(self):
  for key in ('site_id','config_sha256'):
   old=self.v[key];self.v[key]='wrong';self.check('inventory_binding_mismatch');self.v[key]=old
 def test_stale_future_naive_inventory(self):
  for stamp in ((self.now-timedelta(days=2)).isoformat(),(self.now+timedelta(minutes=1)).isoformat(),'2026-01-01T00:00:00',None):
   self.v['observed_at']=stamp;self.check('inventory_time_invalid')
 def test_uncertain_and_incomplete(self):
  for key in ('uncertain_puts','incomplete_runs'):
   self.v[key]=1;self.check(key+'_present');self.v[key]=True;self.check(key+'_invalid');self.v[key]=0
 def test_unset_runtime(self):
  self.c['runtime']['wordpress_ref']='not-connected';self.check('runtime_wordpress_ref_unset')
 def test_same_roles(self):
  self.c['storage']['reader_ref']=self.c['storage']['writer_ref'];self.check('roles_not_separated')
 def test_bad_types(self):
  for value in (None,[],{},'secret'):
   self.assertNotEqual(m.assess(value,self.v,self.work,self.now)['state'],'eligible_for_dedicated_trial')
  self.c['operations']=None;self.check('invalid_fields')
 def test_missing_inventory(self):
  self.v=None;self.check('inventory_missing_or_invalid')
 def test_permissions(self):
  self.work.chmod(0o755);self.check('workspace_not_private');self.work.chmod(0o500);self.check('workspace_owner_permissions')
 def test_symlink_workspace(self):
  link=self.root/'link';link.symlink_to(self.work);self.work=link;self.check('workspace_unavailable')
 def test_missing_workspace(self):
  self.work=self.root/'absent';self.check('workspace_unavailable');self.assertFalse(self.work.exists())
 def test_low_capacity(self):
  class FS:f_bavail=0;f_frsize=4096;f_flag=0
  with patch.object(m.os,'fstatvfs',return_value=FS()):self.check('workspace_capacity_insufficient')
 def test_readonly_filesystem(self):
  class FS:f_bavail=10000000;f_frsize=4096;f_flag=os.ST_RDONLY
  with patch.object(m.os,'fstatvfs',return_value=FS()):self.check('workspace_readonly_filesystem')
 def test_input_bounds_and_duplicate(self):
  p=self.root/'input'
  for raw in ('{"a":1,"a":2}','NaN','x'*65537):
   p.write_text(raw)
   with self.assertRaises(ValueError):m.read_json(p)
  link=self.root/'link';link.symlink_to(p)
  with self.assertRaises(OSError):m.read_json(link)
  fifo=self.root/'fifo';os.mkfifo(fifo)
  with self.assertRaises(ValueError):m.read_json(fifo)
 def test_cli_readonly_and_redaction(self):
  p=self.root/'profile.json';i=self.root/'inventory.json';p.write_text(json.dumps(self.c));i.write_text(json.dumps(self.v))
  (self.work/'sentinel').write_bytes(b'preserved')
  def snapshot():return {str(f.relative_to(self.root)):(f.stat().st_mode,hashlib.sha256(f.read_bytes()).hexdigest()) for f in self.root.rglob('*') if f.is_file()}
  before=snapshot()
  command=['python3','-B',str(ROOT/'tools/deployment-preflight.py'),'--profile',str(p),'--inventory',str(i),'--workspace',str(self.work)]
  result=subprocess.run(command,capture_output=True,text=True,timeout=10);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(snapshot(),before)
  self.assertNotIn(str(self.work),result.stdout)
  p.write_text('{"password":"NEVER_RENDER_SECRET"}');result=subprocess.run(command,capture_output=True,text=True,timeout=10)
  self.assertEqual(result.returncode,2);self.assertNotIn('NEVER_RENDER_SECRET',result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
