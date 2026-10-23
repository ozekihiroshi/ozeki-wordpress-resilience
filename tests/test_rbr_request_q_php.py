import pathlib,subprocess,unittest
class RequestQPHP(unittest.TestCase):
 def test_pure_request_generator_and_reserved_namespace(self):
  p=subprocess.run(['php',str(pathlib.Path(__file__).with_name('rbr-request-q.php'))],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(p.stdout.count('PASS '),8)
