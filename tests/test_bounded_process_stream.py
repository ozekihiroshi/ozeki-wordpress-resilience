import importlib.util,sys,time,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stream',ROOT/'tools/bounded-process-stream.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Rejected(ValueError):pass
class Tests(unittest.TestCase):
 def test_consumer_pause_does_not_stop_producer(self):
  with tempfile.TemporaryDirectory() as d:
   done=Path(d)/'done';code='import sys,pathlib;sys.stdout.buffer.write(b"x"*(2*1024*1024));sys.stdout.flush();pathlib.Path(sys.argv[1]).write_text("done")'
   g=m.stream([sys.executable,'-c',code,str(done)],time.monotonic()+10,3*1024*1024,d,Rejected)
   first=next(g)
   end=time.monotonic()+5
   while not done.exists() and time.monotonic()<end:time.sleep(.01)
   self.assertTrue(done.exists(),'control-side pause must not block producer exit')
   self.assertEqual(len(first)+sum(map(len,g)),2*1024*1024)
   self.assertEqual([p.name for p in Path(d).iterdir()],['done'])
 def test_size_bound(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(Rejected,'capture_size_limit'):list(m.stream([sys.executable,'-c','import sys;sys.stdout.buffer.write(b"x"*1000000)'],time.monotonic()+5,100,d,Rejected))
   self.assertEqual(list(Path(d).iterdir()),[])
 def test_deadline(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(Rejected,'capture_window_lost'):list(m.stream([sys.executable,'-c','import time;time.sleep(10)'],time.monotonic()+.2,100,d,Rejected))
 def test_failure_and_close(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(Rejected,'stream_process_failed'):list(m.stream([sys.executable,'-c','raise SystemExit(2)'],time.monotonic()+5,100,d,Rejected))
   g=m.stream([sys.executable,'-c','import sys,time;print("x",flush=True);time.sleep(10)'],time.monotonic()+5,100,d,Rejected)
   next(g);g.close();self.assertEqual(list(Path(d).iterdir()),[])
if __name__=='__main__':unittest.main()
