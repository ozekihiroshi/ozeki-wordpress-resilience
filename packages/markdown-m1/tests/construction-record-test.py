"""Small checks for operation-time capture, ordered references and interruption."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('record', Path(__file__).parents[1] / 'tools/construction-record.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
Record = module.ConstructionRecord

class RecordChecks(unittest.TestCase):
    def test_capture_before_execution_and_replay_in_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'source'; calls = []
            def execute(op, value):
                self.assertEqual(json.loads(source.read_text().splitlines()[-1])['event'], 'attempt')
                calls.append((op, value))
                return {'id': 12 if op == 'create' else 13}
            record = Record(source, execute)
            record.execute('page', 'create', {'title': 'original'})
            record.execute('settings', 'set', {'page': {'ref': 'page.id'}})
            self.assertEqual(calls[-1][1], {'page': 12})
            target_calls = []
            def replay(op, value):
                target_calls.append((op, value)); return {'id': 91}
            Record.replay(source, root/'target', replay)
            self.assertEqual(target_calls, [('create', {'title':'original'}), ('set', {'page':91})])

    def test_unconfirmed_attempt_prevents_any_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def interrupted(op, value):raise RuntimeError('lost response')
            record = Record(root/'source', interrupted)
            with self.assertRaises(RuntimeError):record.execute('page','create',{})
            with self.assertRaises(ValueError):record.execute('page','create',{})
            calls = []
            with self.assertRaises(ValueError):Record.replay(root/'source',root/'target',lambda *a:calls.append(a))
            self.assertEqual(calls, [])
            self.assertFalse((root/'target').exists())

    def test_missing_reference_does_not_invent_object(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []; record = Record(Path(directory)/'source', lambda *a:calls.append(a))
            with self.assertRaises(ValueError):record.execute('settings','set',{'page':{'ref':'absent.id'}})
            self.assertEqual(calls, [])

if __name__ == '__main__':unittest.main()
