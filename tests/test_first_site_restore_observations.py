import importlib.util
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
o=load('obs','first-site-restore-observations.py')
g=load('g','protected-first-site-set.py')

class Observations(unittest.TestCase):
    def row(self):
        return dict(manifest_sha256='doc',approved_key_sha256='key')
    def record(self,n,passed,time):
        payload=g.encode(dict(manifest_sha256='doc',public_key_sha256='key',report_sha256=str(n),
                              report=dict(passed=passed,completed_at=time)))
        return dict(n=n,payload=payload.decode(),payload_hash=g.sha(payload),report_hash=str(n),
                    registered_at=time)
    def aggregate(self,records):
        row=self.row();o.aggregate(row,records,SimpleNamespace(gate=g));return row
    def test_none(self):
        self.assertEqual(self.aggregate([])['restore_state'],'not_observed')
    def test_success(self):
        self.assertTrue(self.aggregate([self.record(1,True,'2026-10-20T10:00:00Z')])['restore_verified'])
    def test_failure_preserves_prior_success(self):
        row=self.aggregate([self.record(1,True,'2026-10-20T10:00:00Z'),
                            self.record(2,False,'2026-10-20T11:00:00Z')])
        self.assertEqual(row['restore_state'],'failed');self.assertTrue(row['previous_restore_verified'])
        self.assertFalse(row['restore_verified'])
    def test_late_old_success_does_not_hide_failure(self):
        row=self.aggregate([self.record(1,False,'2026-10-20T11:00:00Z'),
                            self.record(2,True,'2026-10-20T10:00:00Z')])
        self.assertEqual(row['restore_state'],'failed')
    def test_corrupted_evidence(self):
        record=self.record(1,True,'2026-10-20T10:00:00Z');record['payload']='{}'
        self.assertEqual(self.aggregate([record])['restore_state'],'evidence_error')
    def test_wrong_document_binding(self):
        row=self.row();row['manifest_sha256']='other'
        o.aggregate(row,[self.record(1,True,'2026-10-20T10:00:00Z')],SimpleNamespace(gate=g))
        self.assertFalse(row['restore_verified']);self.assertTrue(row['restore_evidence_error'])

if __name__=='__main__':unittest.main()
