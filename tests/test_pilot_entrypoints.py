"""Help and no-argument invocation must not reach private files, AWS, keys or Docker."""
import os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PilotEntryTests(unittest.TestCase):
 def test_inert_entrypoints(self):
  for name in ['publish-protected-candidate.py','sign-protected-candidate.py','restore-s3-candidate.py']:
   with self.subTest(script=name),tempfile.TemporaryDirectory() as directory:
    # Copy only the entry script: no SDK/helper, trust files or repository state.
    path=Path(directory)/name;path.write_bytes((ROOT/'tools/pilot'/name).read_bytes())
    for flags,exitcode,expected in [(['--help'],0,'--execute-pilot'),([],2,'Execution disabled'),(['--unknown'],2,'unrecognized arguments')]:
     result=subprocess.run([sys.executable,str(path),*flags],cwd=directory,capture_output=True,text=True,timeout=10)
     self.assertEqual(result.returncode,exitcode,result.stderr);self.assertIn(expected,result.stdout+result.stderr)
     self.assertEqual([p.name for p in Path(directory).iterdir()],[name])
    result=subprocess.run([sys.executable,'-O',str(path),'--execute-pilot'],cwd=directory,capture_output=True,text=True,timeout=10)
    self.assertEqual(result.returncode,2);self.assertIn('Optimized Python',result.stderr)
    self.assertEqual([p.name for p in Path(directory).iterdir()],[name])
if __name__=='__main__':unittest.main()
