import importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('broker',ROOT/'tools/rbr-coordinator-transport.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TransportTests(unittest.TestCase):
 def args(self):return {'Bucket':m.BUCKET,'ExpectedBucketOwner':'121426368082','Key':m.PREFIX+'coordinator/test/commits/000000000001.json'}
 def test_denied_head_requires_successful_empty_list(self):
  with patch.object(m,'request',side_effect=m.Failure(403)),patch.object(m,'metadata',return_value={'success':True,'response':{'Contents':[]}}):
   with self.assertRaises(m.Failure) as e:m.serve({'operation':'HeadObject','args':self.args()})
   self.assertEqual(e.exception.status,404)
 def test_denied_list_stays_denied(self):
  with patch.object(m,'request',side_effect=m.Failure(403)),patch.object(m,'metadata',return_value={'success':False}):
   with self.assertRaises(m.Failure) as e:m.serve({'operation':'HeadObject','args':self.args()})
   self.assertEqual(e.exception.status,403)
 def test_existing_list_stays_denied(self):
  with patch.object(m,'request',side_effect=m.Failure(403)),patch.object(m,'metadata',return_value={'success':True,'response':{'Contents':[{'Key':self.args()['Key']}]}}):
   with self.assertRaises(m.Failure) as e:m.serve({'operation':'HeadObject','args':self.args()})
   self.assertEqual(e.exception.status,403)
 def test_fixed_denial_never_discovered(self):
  a=dict(self.args(),VersionId='fixed')
  with patch.object(m,'request',side_effect=m.Failure(403)),patch.object(m,'metadata') as listing:
   with self.assertRaises(m.Failure):m.serve({'operation':'HeadObject','args':a})
   listing.assert_not_called()
 def test_scope_and_mutation_rejected(self):
  for op,a in [('DeleteObject',self.args()),('PutObjectRetention',self.args()),('HeadObject',dict(self.args(),Key='production/file'))]:
   with patch.object(m,'request') as req:
    with self.assertRaises(m.Failure):m.serve({'operation':op,'args':a})
    req.assert_not_called()
 def test_get_requires_version(self):
  with self.assertRaises(m.Failure):m.serve({'operation':'GetObject','args':self.args()})
if __name__=='__main__':unittest.main()
