import copy,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('deployment-preflight');h=load('host-inventory-check')
class Host(unittest.TestCase):
 def setUp(self):
  self.c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());self.n='a'*32;self.now=datetime.now(timezone.utc)
  self.r={'format':'owr-host-inventory-v1','status':'observed','site_id':self.c['site_id'],'config_sha256':p.capture.digest(self.c),'nonce':self.n,'observed_at':self.now.isoformat(),
   'facts':{'database':{'name':'lab','prefix':'wp_','engines':['InnoDB'],'tables':3},'files':{'root':'/var/www/html','entries':3,'bytes':100,'links':0,'special':0},'wordpress':{'standard_upload_path':True,'external_upload_url':False,'multisite_tables':False},'runtime':{'php_version':'8.3.0','os_family':'Linux'}},
   'unverified':['writers','queue','dependencies','runtime_image_binding','multisite_config','storage','trust','operational_ledgers','file_snapshot_consistency']}
 def assess(self,r=None):return h.integrate({'issues':[],'config_sha256':p.capture.digest(self.c),'evidence_scope':{},'production_ready':False},self.c,self.r if r is None else r,self.n,self.now)
 def test_unknown_never_ready(self):
  v=self.assess();self.assertEqual(v['state'],'needs_configuration');self.assertFalse(v['production_ready']);self.assertFalse(v['host_observation']['authenticated'])
 def test_binding(self):
  for field in ('site_id','config_sha256','nonce'):
   r=copy.deepcopy(self.r);r[field]='wrong';self.assertEqual(self.assess(r)['host_observation']['state'],'invalid')
 def test_times(self):
  for t in ((self.now-timedelta(minutes=6)).isoformat(),(self.now+timedelta(minutes=1)).isoformat(),'2026-01-01T00:00:00'):
   self.r['observed_at']=t;self.assertEqual(self.assess()['host_observation']['state'],'invalid')
 def test_missing_unknowns(self):
  self.r['unverified']=[];self.assertEqual(self.assess()['host_observation']['state'],'invalid')
 def test_bad_types(self):
  for value in (None,True,{},'secret',-1):
   self.r['facts']['files']['bytes']=value;self.assertEqual(self.assess()['host_observation']['state'],'invalid')
 def test_unsupported_engine(self):
  self.r['facts']['database']['engines']=['MyISAM'];self.assertEqual(self.assess()['state'],'unsupported')
 def test_unsupported_files(self):
  for field in ('links','special'):
   r=copy.deepcopy(self.r);r['facts']['files'][field]=1;self.assertEqual(self.assess(r)['state'],'unsupported')
 def test_wordpress_limits(self):
  for key,value in [('standard_upload_path',False),('external_upload_url',True),('multisite_tables',True)]:
   r=copy.deepcopy(self.r);r['facts']['wordpress'][key]=value;self.assertEqual(self.assess(r)['state'],'unsupported')
 def test_runtime_limit(self):
  self.r['facts']['runtime']['php_version']='7.4.1';self.assertEqual(self.assess()['state'],'unsupported')
 def test_probe_failure(self):
  v=self.assess({'format':'owr-host-inventory-v1','status':'probe_failed','stage':'database'})
  self.assertEqual(v['state'],'needs_configuration');self.assertEqual(v['issues'][0]['category'],'environment')
 def test_secrets_not_echoed(self):
  self.r['facts']['database']['engines']=['NEVER_RENDER_SECRET'];self.r['facts']['files']['root']='NEVER_RENDER_SECRET'
  self.assertNotIn('NEVER_RENDER_SECRET',json.dumps(self.assess()))
if __name__=='__main__':unittest.main()
