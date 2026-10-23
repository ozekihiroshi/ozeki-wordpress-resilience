import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('preparation',Path(__file__).resolve().parents[1]/'tools/rbr-kit-preparation-worker.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Preparation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.b=Path(self.tmp.name)
  for n in ['inbox','state']:(self.b/n).mkdir()
  (self.b/'profile').write_text('{"schema":"owr-rbr-request-profile-v1"}')
  self.c={n:str(self.b/n) for n in ['inbox','state','profile','report']};self.receipt=json.dumps({'state':'applied','sequence':1,'generation':{'sha256':'a'*64},'expected_ref':{'sha256':'b'*64}});self.ph=m.sha((self.b/'profile').read_bytes());self.job=m.sha(self.receipt.encode()+self.ph.encode());self.calls=0
 def queue(self,attempt=0):
  q={'job_id':self.job,'attempt':attempt,'profile_sha256':self.ph,'receipt':self.receipt};(self.b/'inbox'/f'{self.job}-{attempt}.json').write_text(json.dumps(q))
 def state(self):return m.read(self.b/'state'/self.job/'status.json')
 def runner(self,receipt,profile,work,log):
  self.calls+=1;self.assertEqual(receipt.read_text(),self.receipt);self.assertEqual(m.read(self.b/'report')['items'][0]['state'],'running')
  return {'state':'stored_awaiting_independent_approval','generation_ref':json.loads(self.receipt)['generation'],'root_receipt':{'sha256':'c'*64},'public_activation':False}
 def test_success_duplicate_never_runs_again(self):
  self.queue();m.cycle(self.c,self.runner);m.cycle(self.c,self.runner);self.assertEqual(self.calls,1);self.assertEqual(self.state()['state'],'stored_awaiting_independent_approval')
 def test_explicit_resume_same_work(self):
  self.queue();seen=[]
  def fail(*a):seen.append(a[2]);raise RuntimeError('secret must not appear')
  m.cycle(self.c,fail);self.assertEqual(self.state()['state'],'failed');self.assertNotIn('secret',json.dumps(self.state()));m.cycle(self.c,self.runner);self.assertEqual(self.calls,0)
  self.queue(1);m.cycle(self.c,self.runner);self.assertEqual(self.calls,1);self.assertEqual(seen[0],self.b/'state'/self.job/'work')
 def test_unknown_put_blocks_resume(self):
  self.queue()
  def unknown(receipt,profile,work,log):
   (work/'transport').mkdir(parents=True);(work/'transport/operations.json').write_text('[{"method":"PUT","state":"unknown"}]');raise RuntimeError()
  m.cycle(self.c,unknown);self.assertEqual(self.state()['state'],'blocked');self.queue(1);m.cycle(self.c,self.runner);self.assertEqual(self.calls,0)
 def test_interrupted_requires_next_explicit_attempt(self):
  self.queue();directory=self.b/'state'/self.job;directory.mkdir();m.atomic(directory/'status.json',{'state':'interrupted','attempt':0})
  m.cycle(self.c,self.runner);self.assertEqual(self.calls,0);self.queue(1);m.cycle(self.c,self.runner);self.assertEqual(self.calls,1)
 def test_safe_reason_retention_without_private_error(self):
  self.queue()
  def fail(receipt,profile,work,log):log.write_text('private host secret: retention insufficient');raise RuntimeError()
  m.cycle(self.c,fail);self.assertIn('保持',self.state()['reason']);self.assertNotIn('secret',json.dumps(m.read(self.b/'report')))
 def test_skip_attempt_rejected(self):
  self.queue(2);m.cycle(self.c,self.runner);self.assertEqual(self.calls,0)
 def test_profile_change_does_not_execute_old_request(self):
  self.queue();(self.b/'profile').write_text('{"schema":"owr-rbr-request-profile-v1","changed":true}');m.cycle(self.c,self.runner);self.assertEqual(self.calls,0)
 def test_symlink_request_rejected(self):
  self.queue();p=next((self.b/'inbox').iterdir());raw=p.read_bytes();p.unlink();(self.b/'outside').write_bytes(raw);p.symlink_to(self.b/'outside');m.cycle(self.c,self.runner);self.assertEqual(self.calls,0)
 def test_result_mismatch_is_not_success(self):
  self.queue();m.cycle(self.c,lambda *a:{'state':'stored_awaiting_independent_approval','generation_ref':{},'public_activation':False});self.assertEqual(self.state()['state'],'failed')
if __name__=='__main__':unittest.main()
