"""New operational connections only: generated signatures, temporary root registry, no network."""
import copy
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_first_site_daily_restore as f

s = importlib.util.spec_from_file_location('recurring_ssh', f.ROOT/'tools/trust-registry-ssh.py')
ssh = importlib.util.module_from_spec(s); s.loader.exec_module(ssh)
u = ssh.u

@unittest.skipUnless(hasattr(os, 'geteuid') and os.geteuid() == 0, 'dedicated root lab required')
class Operations(unittest.TestCase):
    factory = f.Recovery.factory
    restore = f.Recovery.restore
    recover = f.Recovery.recover

    def setUp(self):
        f.Recovery.setUp(self)
        self.addCleanup(self.tmp.cleanup)
        temp = tempfile.TemporaryDirectory(dir='/run', prefix='owr-recurring-')
        self.addCleanup(temp.cleanup)
        self.hosts = [Path(temp.name)/name for name in ('host-a.json', 'host-b.json')]
        self.approval_before = {p.name: p.read_bytes() for p in self.trust.iterdir() if p.is_file()}
        now = dt.datetime.now(dt.timezone.utc)
        self.record = dict(format='owr-current-recovery-trust-v1', revision=1,
            issued_at=(now-dt.timedelta(seconds=2)).isoformat(),
            expires_at=(now+dt.timedelta(hours=1)).isoformat(), revoked_key_sha256=[],
            sets=[dict(site_id=f.r.d.SITE, set_id='AWS-'+'1'*16, status='active', minimum_sequence=1,
                public_key_sha256=self.key_hash, approved_document_sha256=self.doc_hash)])
        for host in self.hosts:
            self.deploy(host, self.record, 'absent')
        p = patch.object(f.r.current_trust, 'AUTHORITY', self.hosts[0]); p.start(); self.addCleanup(p.stop)

    def deploy(self, host, record, expected):
        candidate = host.parent/'candidate.json'; candidate.write_text(json.dumps(record))
        with patch.object(u.g, 'AUTHORITY', host):
            return u.deploy(candidate, expected, u.sha(candidate.read_bytes()), True)

    def inspect(self, host):
        with patch.object(u.g, 'AUTHORITY', host):
            return ssh.endpoint({'action': 'inspect'})

    def unchanged_approval(self):
        self.assertEqual(self.approval_before,
            {p.name: p.read_bytes() for p in self.trust.iterdir() if p.is_file()})

    def refreshed(self):
        record = copy.deepcopy(self.record); record['revision'] = 2
        record['expires_at'] = (dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=12)).isoformat()
        return record

    def test_refresh_preserves_signature_and_all_hosts_confirm_exact_hash(self):
        record = self.refreshed(); hashes = []
        for host in self.hosts:
            result = self.deploy(host, record, self.inspect(host)['sha256'])
            observed = self.inspect(host)
            self.assertEqual((observed['revision'], observed['sha256']), (2, result['sha256']))
            hashes.append(observed['sha256'])
        self.assertEqual(hashes[0], hashes[1]); self.unchanged_approval()
        self.assertTrue(self.recover()['passed']); self.assertEqual(self.gets, 2)

    def test_fresh_registry_does_not_extend_expired_signed_approval(self):
        self.deploy(self.hosts[0], self.refreshed(), self.inspect(self.hosts[0])['sha256'])
        approval = json.loads((self.trust/'approved.json').read_bytes())
        expired_time = f.r.g.date(approval['expires_at'])+dt.timedelta(seconds=1)
        # Simulate the signature gate clock only; the independent registry stays current.
        with patch.object(f.r.g, 'now', return_value=expired_time):
            with self.assertRaisesRegex(ValueError, 'expired/future approval'):
                self.recover()
        self.assertEqual((self.gets, self.restores), (0, 0)); self.unchanged_approval()

    def test_failed_refresh_then_expiry_blocks_until_reviewed_higher_revision(self):
        host = self.hosts[0]; old = host.read_bytes(); record = self.refreshed()
        with patch.object(u.os, 'replace', side_effect=OSError('injected write failure')):
            with self.assertRaises(OSError): self.deploy(host, record, u.sha(old))
        self.assertEqual(host.read_bytes(), old)
        # Dedicated fixture advances installed checkpoint into expired state; no production clock changes.
        expired = copy.deepcopy(self.record); now = dt.datetime.now(dt.timezone.utc)
        expired.update(issued_at=(now-dt.timedelta(hours=2)).isoformat(), expires_at=(now-dt.timedelta(hours=1)).isoformat())
        host.write_text(json.dumps(expired))
        with self.assertRaisesRegex(ValueError, 'authority expired'):
            self.recover()
        self.assertEqual((self.constructed, self.gets, self.restores), (0, 0, 0))
        self.deploy(host, record, self.inspect(host)['sha256'])
        self.assertTrue(self.recover()['passed']); self.unchanged_approval()

    def test_partial_revocation_rollout_is_not_fleet_success(self):
        revoked = self.refreshed(); revoked['sets'][0]['status'] = 'revoked'
        self.deploy(self.hosts[0], revoked, self.inspect(self.hosts[0])['sha256'])
        a, b = [self.inspect(host) for host in self.hosts]
        self.assertNotEqual(a['sha256'], b['sha256'])
        with self.assertRaisesRegex(ValueError, 'set revoked'): self.recover()
        # Unupdated host still trusts its unexpired checkpoint: explicitly a boundary, not global revocation.
        with patch.object(f.r.current_trust, 'AUTHORITY', self.hosts[1]):
            self.assertEqual(f.r.current_trust.current(self.trust, self.trust/'approved.json', f.r.d.SITE, 'AWS-'+'1'*16)['revision'], 1)
        self.assertEqual(self.gets, 0); self.unchanged_approval()

    def test_unknown_after_replace_inspect_confirms_without_reapply(self):
        host = self.hosts[0]; old_hash = self.inspect(host)['sha256']; record = self.refreshed()
        real = u.os.fsync; calls = []
        def fail(fd):
            calls.append(fd)
            if len(calls) == 2: raise OSError('injected directory sync failure')
            return real(fd)
        with patch.object(u.os, 'fsync', side_effect=fail):
            with self.assertRaises(OSError): self.deploy(host, record, old_hash)
        observed = self.inspect(host)
        self.assertEqual(observed['revision'], 2)
        self.assertEqual(observed['sha256'], u.sha(json.dumps(record).encode()))
        with self.assertRaises(ValueError): self.deploy(host, record, old_hash)
        self.unchanged_approval()

    def test_expired_registry_inspection_is_not_recovery_readiness(self):
        host = self.hosts[0]; record = copy.deepcopy(self.record)
        record['expires_at'] = record['issued_at']; host.write_text(json.dumps(record))
        # Structurally valid expired registry is inspectable (use a positive past interval).
        record['issued_at'] = (dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1)).isoformat()
        host.write_text(json.dumps(record))
        self.assertEqual(self.inspect(host)['state'], 'inspected')
        with self.assertRaisesRegex(ValueError, 'authority expired'): self.recover()
        self.assertEqual(self.gets, 0); self.unchanged_approval()

if __name__ == '__main__': unittest.main()
