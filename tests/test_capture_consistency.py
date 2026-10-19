import importlib.util,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'tools/simulate-capture-consistency.py'
spec=importlib.util.spec_from_file_location('lab',path);lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
class ConsistencyTests(unittest.TestCase):
 def test_actual_snapshot_and_file_scenarios(self):
  for name,expected in lab.SCENARIOS.items():
   with self.subTest(name=name):
    r=lab.run_scenario(name);self.assertEqual(r['assessment']['state'],expected)
    self.assertEqual(r['assessment']['eligible_for_consistency_acceptance'],expected=='consistent')
 def test_unfenced_hash_match_is_not_acceptance(self):
  r=lab.run_scenario('unfenced_stable');self.assertTrue(r['observation']['references_match']);self.assertFalse(r['assessment']['eligible_for_consistency_acceptance'])
 def test_race_produces_real_reference_mismatch(self):
  self.assertFalse(lab.run_scenario('update_between_assets')['observation']['references_match'])
 def test_aba_has_equal_hashes_but_is_rejected(self):
  r=lab.run_scenario('aba_update');o=r['observation'];self.assertEqual(o['file_inventory_before'],o['file_inventory_after']);self.assertTrue(o['references_match']);self.assertEqual(r['assessment']['state'],'inconsistent')
 def test_missing_evidence(self):
  o=lab.run_scenario('quiescent')['observation']
  for key in list(o):
   modified=dict(o);del modified[key]
   with self.subTest(field=key):self.assertFalse(lab.gate.assess(modified,lab.WRITERS)['eligible_for_consistency_acceptance'])
 def test_expected_scope_cannot_be_empty_or_shrunk(self):
  o=lab.run_scenario('quiescent')['observation']
  for scope in [[],['web'],['web','cron','cli','unknown']]:self.assertFalse(lab.gate.assess(o,scope)['eligible_for_consistency_acceptance'])
 def test_operation_order(self):
  o=lab.run_scenario('quiescent')['observation'];o['phases']=['snapshot','fence','drain','copy','verify','release']
  self.assertFalse(lab.gate.assess(o,lab.WRITERS)['eligible_for_consistency_acceptance'])
 def test_mixed_attempt(self):
  o=lab.run_scenario('quiescent')['observation'];o['assets']['files']['attempt_id']='other-attempt'
  self.assertEqual(lab.gate.assess(o,lab.WRITERS)['state'],'inconsistent')
 def test_copied_inventory_mismatch(self):
  o=lab.run_scenario('quiescent')['observation'];o['captured_file_inventory']['image.bin']='0'*64
  self.assertEqual(lab.gate.assess(o,lab.WRITERS)['state'],'inconsistent')
if __name__=='__main__':unittest.main()
