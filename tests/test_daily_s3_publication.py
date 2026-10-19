import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('publication_tests','daily-s3-publication.py')
d=load('daily_s3_tests','daily-backup-lab.py')

class Store:
    def __init__(self):self.objects={};self.reads=0;self.puts=0;self.bad_retention=False;self.fail_put=False
    def factory(self,work):
        store=self
        class Adapter:
            def __init__(self):
                self.work=Path(work);self.work.mkdir(parents=True);self.operations=[]
            def save(self):p.write_json(self.work/'operations.json',self.operations)
            def put(self,bucket,key,body):
                store.puts+=1
                event={'method':'PUT','key':key,'state':'started','sha256':p.gate.sha(body),'bytes':len(body)}
                self.operations.append(event);self.save()
                if store.fail_put:raise RuntimeError('lost PUT response')
                version=secrets.token_hex(8);now=p.gate.now()-timedelta(seconds=1)
                store.objects[key,version]={'body':body,'version_id':version,'reader_identity':'OwrM1RecoveryReader','mode':'GOVERNANCE','last_modified':now.isoformat(),'retain_until':(now+timedelta(days=35,minutes=10)).isoformat()}
                event.update(state='acknowledged',version_id=version);self.save();return version
            def get(self,loc):
                store.reads+=1;r=dict(store.objects[loc['key'],loc['version_id']])
                if store.bad_retention:r['mode']=None
                self.operations.append({'method':'GET','key':loc['key'],'version_id':r['version_id'],'sha256':p.gate.sha(r['body']),'bytes':len(r['body'])});self.save()
                return r
        return Adapter()


class DailyS3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=tempfile.TemporaryDirectory();cls.key=Path(cls.keys.name)/'private.pem';cls.public=Path(cls.keys.name)/'public.pem'
        subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(cls.key)],check=True,capture_output=True)
        subprocess.run(['openssl','pkey','-in',str(cls.key),'-pubout','-out',str(cls.public)],check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.keys.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.store=Store();self.dir=self.root/'candidate'
        q=self.root/'queue.sqlite'
        with sqlite3.connect(q) as db:
            db.execute('CREATE TABLE control(id INTEGER,checkpoint TEXT)');db.execute('INSERT INTO control VALUES(1,?)',('a'*32,))
            db.execute('CREATE TABLE jobs(id TEXT,kind TEXT,state TEXT)');db.execute("INSERT INTO jobs VALUES('job','write','pending')")
        self.assets={'database':b'db','files':b'files','queue':q.read_bytes()}
        self.paired={'format':'owr-paired-queue-v1','site_id':p.SITE,'checkpoint':'a'*32,'handler_sha256':p.gate.sha((ROOT/'lab/consistency/external-job.php').read_bytes()),'assets':{k:p.gate.sha(v) for k,v in self.assets.items()}}
        self.now=datetime.now(timezone.utc)
    def publish(self,directory=None):
        return p.publish(self.assets,self.paired,directory or self.dir,lambda name:None,self.store.factory,lambda:{'passed':True})
    def sign(self,doc):
        sig=self.root/('signature-'+secrets.token_hex(4))
        subprocess.run(['openssl','dgst','-sha256','-sign',str(self.key),'-out',str(sig),str(doc)],check=True,capture_output=True)
        return sig
    def approve(self,summary,sig=None,**overrides):
        doc=self.dir/'candidate.json'
        args=dict(document=doc,signature=sig or self.sign(doc),public_key=self.public,expected_hash=summary['manifest_sha256'],expected_key_hash=p.gate.sha(self.public.read_bytes()),operator_dir=self.root/('operator-'+secrets.token_hex(4)),adapter_factory=self.store.factory)
        args.update(overrides);return p.approve(**args)
    def worker(self,work,report):
        saved=self.publish(work/'candidate')
        cases=json.loads((ROOT/'schemas/daily-s3-required-cases.json').read_text())
        p.write_json(report,{'format':'owr-wordpress-consistency-lab-v1','all_passed':True,'resources_removed':True,'results':[{'case':name,'passed':True} for name in cases],'external_evidence':{'queue_recovery':{'saved_set':saved,'restore_performed':False}}})
    def test_publish_unsigned_three_versions_only(self):
        with patch('subprocess.run',side_effect=AssertionError('publisher must not sign')):summary=self.publish()
        p.verify_saved(self.dir,summary)
        self.assertEqual(self.store.puts,3);self.assertEqual(self.store.reads,3)
        self.assertFalse(summary['signature_created']);self.assertFalse(summary['restore_allowed'])
        self.assertEqual(list(self.dir.rglob('*.pem')),[])
    def test_pending_duplicate_suppressed_but_next_day_saved(self):
        c=d.Coordinator(self.root/'daily','s3');row=c.tick(self.now,self.worker)
        self.assertEqual(row['state'],'awaiting_approval')
        self.assertEqual(c.tick(self.now,self.worker,retry=True)['id'],row['id']);self.assertEqual(self.store.puts,3)
        status=c.status(self.now);self.assertEqual(status['missing_days'],[]);self.assertTrue(status['attention_required'])
        self.assertEqual(c.tick(self.now+timedelta(days=1),self.worker)['state'],'awaiting_approval');self.assertEqual(self.store.puts,6)
    def test_uncertain_put_no_automatic_retry(self):
        self.store.fail_put=True
        with self.assertRaises(RuntimeError):self.publish()
        self.assertFalse(json.loads((self.dir/'receipt.json').read_text())['storage_complete'])
        with self.assertRaises(FileExistsError):self.publish()
        self.assertEqual(self.store.puts,1)
    def test_bad_storage_read_never_marks_complete(self):
        self.store.bad_retention=True
        with self.assertRaises(ValueError):self.publish()
        self.assertFalse(json.loads((self.dir/'receipt.json').read_text())['storage_complete'])
    def test_unsigned_signature_rejected_before_network(self):
        summary=self.publish();sig=self.root/'bad.sig';sig.write_bytes(b'unsigned')
        before=self.store.reads
        with self.assertRaises(ValueError):self.approve(summary,sig)
        self.assertEqual(self.store.reads,before)
    def test_independent_key_hash_required(self):
        summary=self.publish();before=self.store.reads
        with self.assertRaises(ValueError):self.approve(summary,expected_key_hash='0'*64)
        self.assertEqual(self.store.reads,before)
    def test_candidate_modified_after_review_rejected(self):
        summary=self.publish();doc=self.dir/'candidate.json';sig=self.sign(doc);doc.write_bytes(doc.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.approve(summary,sig)
        self.assertEqual(self.store.reads,3)
    def test_expired_approval_rejected_before_network(self):
        summary=self.publish();doc=self.dir/'candidate.json';m=json.loads(doc.read_bytes());m['expires_at']=(p.gate.now()-timedelta(seconds=1)).isoformat();p.write_json(doc,m)
        summary['manifest_sha256']=p.gate.sha(doc.read_bytes())
        with self.assertRaises(ValueError):self.approve(summary)
        self.assertEqual(self.store.reads,3)
        m['expires_at']=(p.gate.date(m['issued_at'])+timedelta(days=8)).isoformat();p.write_json(doc,m)
        summary['manifest_sha256']=p.gate.sha(doc.read_bytes())
        with self.assertRaises(ValueError):self.approve(summary)
        self.assertEqual(self.store.reads,3)
    def test_null_version_rejected_before_network(self):
        summary=self.publish();doc=self.dir/'candidate.json';m=json.loads(doc.read_bytes());m['assets'][0]['locator']['version_id']='null';p.write_json(doc,m)
        summary['manifest_sha256']=p.gate.sha(doc.read_bytes())
        with self.assertRaises(ValueError):self.approve(summary)
        self.assertEqual(self.store.reads,3)
    def test_signed_but_fresh_retention_missing_rejected(self):
        summary=self.publish();self.store.bad_retention=True
        with self.assertRaises(ValueError):self.approve(summary)
        self.assertEqual(self.store.puts,3)
    def test_valid_approval_reads_only_and_does_not_restore(self):
        summary=self.publish();result=self.approve(summary)
        self.assertEqual(result['state'],'approved');self.assertEqual(self.store.reads,6);self.assertEqual(self.store.puts,3)
        self.assertFalse(result['isolated_restore_verified']);self.assertFalse(result['production_recovery_approved'])
    def test_missing_put_receipt_refuses_storage_completion(self):
        summary=self.publish();path=self.dir/'transfer-receipts/operations.json';ops=json.loads(path.read_text());ops.pop(0);p.write_json(path,ops)
        with self.assertRaises(ValueError):p.verify_saved(self.dir,summary)
    def test_storage_mode_cannot_change(self):
        c=d.Coordinator(self.root/'daily','s3');c.status(self.now)
        with self.assertRaises(ValueError):d.Coordinator(self.root/'daily').status(self.now)
    def test_reconcile_does_not_upgrade_to_approved(self):
        c=d.Coordinator(self.root/'daily','s3')
        def lose_exit(work,report):self.worker(work,report);raise RuntimeError('exit lost')
        self.assertEqual(c.tick(self.now,lose_exit)['state'],'unknown')
        self.assertEqual(c.reconcile(d.slot(self.now))['state'],'awaiting_approval')
    def test_rejected_approval_stays_pending_then_valid_approval_expires(self):
        c=d.Coordinator(self.root/'daily','s3');row=c.tick(self.now,self.worker)
        doc=Path(row['report']).parent/'candidate/candidate.json';sig=self.sign(doc)
        args=[row['day'],sig,self.public,p.gate.sha(doc.read_bytes()),p.gate.sha(self.public.read_bytes())]
        with patch.object(d,'publication',return_value=p),patch.object(p.transport,'S3Adapter',side_effect=self.store.factory):
            sig.write_bytes(b'invalid')
            with self.assertRaises(ValueError):c.approve(*args,self.root/'bad-operator')
            self.assertEqual(c.status(self.now)['runs'][0]['state'],'awaiting_approval')
            args[1]=self.sign(doc)
            self.assertEqual(c.approve(*args,self.root/'good-operator')['state'],'approved')
        self.assertEqual(c.status(self.now+timedelta(days=8))['expired_or_unreadable_approval_days'],[row['day']])

if __name__=='__main__':unittest.main()
