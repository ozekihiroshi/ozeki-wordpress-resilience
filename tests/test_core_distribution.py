import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class DistributionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);(self.root/'composer.json').write_text('{}')
 def run_tool(self,*args):
  return subprocess.run([sys.executable,str(ROOT/'tools/vendor-backup-core.py'),'--target',str(self.root),*args],capture_output=True,text=True)
 def test_generated_copy_round_trip_and_drift(self):
  self.assertEqual(self.run_tool().returncode,0)
  self.assertEqual(self.run_tool('--check').returncode,0)
  changed=self.root/'libs/backup-core/src/Database/DatabaseConnection.php'
  changed.write_text('local change')
  self.assertNotEqual(self.run_tool('--check').returncode,0)
  self.assertNotEqual(self.run_tool().returncode,0)
  self.assertEqual(changed.read_text(),'local change')
 def test_refuse_unmanaged_destination(self):
  path=self.root/'libs/backup-core';path.mkdir(parents=True)
  (path/'keep.txt').write_text('user file')
  self.assertNotEqual(self.run_tool().returncode,0)
  self.assertEqual((path/'keep.txt').read_text(),'user file')
