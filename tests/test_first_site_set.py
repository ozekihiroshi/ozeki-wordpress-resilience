import copy,datetime as dt,importlib.util,json,tempfile,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('gate',ROOT/'tools/protected-first-site-set.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
class FirstSiteSet(unittest.TestCase):
 def setUp(self):
  self.assets={'database':b'sql','files':b'archive'}
  self.c={'format':'owr-first-site-capture-v1','attempt_id':'a'*32,'site_id':'generated-first-site','config_sha256':'b'*64,'state':'consistent','eligible_for_consistency_acceptance':True,'release_confirmed':True,'production_recovery_approved':False,'queue':{'state':'absent','evidence':'isolated'},'assets':{k:{'attempt_id':'a'*32,'bytes':len(v),'sha256':g.sha(v)} for k,v in self.assets.items()}}
  self.store={};self.calls=[]
 def put(self,b,k,body):
  self.calls.append(k);self.store[k]=body;return 'fixed1'
 def get(self,l):
  return {'body':self.store[l['key']],'version_id':'fixed1','reader_identity':'OwrM1RecoveryReader','mode':'GOVERNANCE','last_modified':self.modified,'retain_until':self.until}
 def build(self):
  self.modified=g.now().isoformat();self.until=(g.now()+dt.timedelta(days=35,minutes=10)).isoformat()
  return g.build(self.assets,self.c,'isolated-queue-lab','AWS-'+'1'*16,'bucket','region','my-ssm-role','OwrM1RecoveryReader',self.put,self.get)
 def test_capture_refusals_before_put(self):
  for field,value in [('state','unverified'),('release_confirmed',False),('eligible_for_consistency_acceptance',False),('queue',{'state':'present'}),('attempt_id','c'*32)]:
   with self.subTest(field=field):
    old=copy.deepcopy(self.c);self.c[field]=value
    with self.assertRaises((ValueError,KeyError)):self.build()
    self.assertEqual(self.calls,[]);self.c=old
 def test_byte_mismatch_before_put(self):
  self.assets['database']=b'bad'
  with self.assertRaises(ValueError):self.build()
  self.assertEqual(self.calls,[])
 def test_missing_asset(self):
  del self.assets['files']
  with self.assertRaises(ValueError):self.build()
 def test_signature_and_fixed_versions(self):
  m=self.build()
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);pub=root/'publisher';pub.mkdir();doc=pub/'candidate.json';doc.write_bytes(g.encode(m));trust=root/'operator'
   subprocess.run(['python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(doc),'--operator',str(trust)],check=True,capture_output=True)
   sig=trust/'approved.sig'
   a,v=g.fetch_verified(trust,doc,sig,m['site_id'],m['set_id'],'b'*64,self.get);self.assertEqual(a,self.assets);self.assertEqual(v['assets_verified'],2)
   calls=[]
   def forbidden(l):calls.append(l);raise AssertionError('GET before rejection')
   with self.assertRaises(ValueError):g.fetch_verified(trust,doc,sig,m['site_id'],m['set_id'],'c'*64,forbidden)
   sig.write_bytes(b'bad')
   with self.assertRaises(ValueError):g.fetch_verified(trust,doc,sig,m['site_id'],m['set_id'],'b'*64,forbidden)
   self.assertEqual(calls,[])
 def test_signed_metadata_and_download_mutations(self):
  original=self.build()
  for case in ['missing','duplicate','expired','short','version','bytes','retain_shortened']:
   with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
    m=copy.deepcopy(original);root=Path(tmp);pub=root/'publisher';pub.mkdir();doc=pub/'candidate.json';trust=root/'operator'
    if case=='missing':m['assets'].pop()
    if case=='duplicate':m['assets'][1]=copy.deepcopy(m['assets'][0])
    if case=='expired':m['expires_at']=(g.now()-dt.timedelta(seconds=1)).isoformat()
    if case=='short':m['assets'][0]['retention']['retain_until']=(g.now()+dt.timedelta(days=1)).isoformat()
    doc.write_bytes(g.encode(m))
    subprocess.run(['python3',str(ROOT/'tools/first-site-lab-sign.py'),'--candidate',str(doc),'--operator',str(trust)],check=True,capture_output=True)
    calls=[]
    def changed(loc):
     calls.append(loc);r=self.get(loc)
     if case=='version':r['version_id']='other'
     if case=='bytes':r['body']=b'changed'
     if case=='retain_shortened':r['retain_until']=(g.now()+dt.timedelta(days=34)).isoformat()
     return r
    with self.assertRaises(ValueError):g.fetch_verified(trust,doc,trust/'approved.sig',m['site_id'],m['set_id'],'b'*64,changed)
    if case in ['missing','duplicate','expired','short']:self.assertEqual(calls,[])
 def test_download_fail_closed(self):
  self.build();loc={'size_bytes':3,'sha256':g.sha(b'sql'),'version_id':'fixed1'}
  response={'version_id':'other','reader_identity':'OwrM1RecoveryReader','mode':'GOVERNANCE','last_modified':self.modified,'retain_until':self.until}
  with self.assertRaises(ValueError):g.observe('database',b'sql',loc,response,'OwrM1RecoveryReader')
  response['version_id']='fixed1';response['retain_until']=(g.now()+dt.timedelta(days=34)).isoformat()
  with self.assertRaises(ValueError):g.observe('database',b'sql',loc,response,'OwrM1RecoveryReader')
if __name__=='__main__':unittest.main()
