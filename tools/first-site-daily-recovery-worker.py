#!/usr/bin/env python3
"""Durable local recovery request and result delivery. Never automatically rerun recovery."""
import argparse
from contextlib import contextmanager
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
d=load('worker_daily','first-site-daily.py')


class Worker:
    def __init__(self,state):
        self.daily=d.Coordinator(state)
        self.root=self.daily.root

    @contextmanager
    def lock(self):
        with (self.root/'recovery-worker.lock').open('a') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.daily.locked() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS recovery_attempts(
                    n INTEGER PRIMARY KEY,request_id TEXT UNIQUE,day TEXT,inputs TEXT,
                    state TEXT,outcome TEXT,registration TEXT,report_hash TEXT,error_type TEXT)""")
                db.commit()
            yield

    def row(self,request_id):
        with sqlite3.connect((self.root/'daily.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM recovery_attempts WHERE request_id=?',(request_id,)).fetchone()
            return dict(row) if row else None

    def update(self,request_id,**values):
        with self.daily.locked() as db:
            db.execute('UPDATE recovery_attempts SET '+','.join(k+'=?' for k in values)+' WHERE request_id=?',
                       (*values.values(),request_id))
            db.commit()

    def finish_or_interrupt(self,request_id):
        row=self.row(request_id)
        output=self.root/'recovery-attempts'/request_id
        try:
            raw=(output/'result.json').read_bytes()
            report=json.loads(raw)
            final=(report.get('passed') is True and 'completed_at' in report
                   or report.get('passed') is False and 'error_type' in report)
        except (OSError,ValueError):
            final=False
        if final:
            self.update(request_id,state='finished',outcome='succeeded' if report['passed'] else 'failed',
                        registration='pending',report_hash=d.gate.sha(raw))
        else:
            # Preserve the partial original. Do not invent completion or rerun the source operation.
            self.update(request_id,state='interrupted',outcome='unknown',registration='unavailable',
                        error_type='RecoveryInterrupted')

    def deliver(self,request_id,registrar=None):
        row=self.row(request_id)
        if row['state']!='finished' or row['registration']=='recorded':
            return row
        try:
            (registrar or self.daily.record_restore)(
                row['day'],self.root/'recovery-attempts'/request_id,row['report_hash'])
        except Exception as exc:
            self.update(request_id,registration='pending',error_type=type(exc).__name__)
        else:
            self.update(request_id,registration='recorded',error_type=None)
        return self.row(request_id)

    def run(self,request_id,day,trust,recover=None,registrar=None):
        d.gate.check(re.fullmatch('[a-zA-Z0-9_-]{1,64}',request_id) is not None,'unsafe request id')
        trust=str(Path(trust).resolve())
        with self.lock():
            prior=self.row(request_id)
            if prior:
                inputs=json.loads(prior['inputs'])
                d.gate.check(prior['day']==day and inputs['trust']==trust,'request id reused with other inputs')
                if prior['state'] in ('running','interrupted'):
                    self.finish_or_interrupt(request_id)
                return self.deliver(request_id,registrar)
            with self.daily.locked() as db:
                # An uncertain/failed earlier attempt may still have isolated resources. Inspect it first.
                d.gate.check(not db.execute("SELECT 1 FROM recovery_attempts WHERE state!='reviewed_closed' AND (state!='finished' OR outcome!='succeeded' OR registration!='recorded')").fetchone(),
                             'unresolved recovery attempt requires review')
                daily=db.execute('SELECT * FROM runs WHERE day=?',(day,)).fetchone()
                d.gate.check(daily is not None and daily['state']=='approved','approved daily set required')
                work=self.root/daily['id'];r=d.verify_saved(work)
                d.gate.check(d.gate.sha((work/'receipt.json').read_bytes())==daily['digest'],'receipt changed')
                a=json.loads((work/'approval.json').read_bytes())
                d.gate.check(a['state']=='approved' and a['manifest_sha256']==r['manifest_sha256'],
                             'approval mismatch')
                inputs=dict(trust=trust,set_id=r['set_id'],config_hash=r['config_sha256'],
                            document_hash=a['manifest_sha256'],key_hash=a['public_key_sha256'])
                output=self.root/'recovery-attempts'/request_id
                d.gate.check(not output.exists(),'recovery destination already exists')
                db.execute('INSERT INTO recovery_attempts(request_id,day,inputs,state,outcome,registration) VALUES(?,?,?,?,?,?)',
                           (request_id,day,json.dumps(inputs,sort_keys=True),'running','unknown','waiting'))
                db.commit()
            if recover is None:
                recover=load('worker_recovery','first-site-daily-restore.py').recover
            try:
                recover(destination=output,**inputs)
            except Exception as exc:
                # The durable recovery report, not this exception alone, determines registration.
                self.update(request_id,error_type=type(exc).__name__)
            self.finish_or_interrupt(request_id)
            return self.deliver(request_id,registrar)

    def retry_registration(self,request_id,registrar=None):
        with self.lock():
            row=self.row(request_id)
            d.gate.check(row is not None,'unknown request')
            if row['state'] in ('running','interrupted'):
                self.finish_or_interrupt(request_id)
            return self.deliver(request_id,registrar)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',required=True)
    sub=p.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run')
    for name in ('request-id','day','trust'):run.add_argument('--'+name,required=True)
    retry=sub.add_parser('retry-registration');retry.add_argument('--request-id',required=True)
    inspect=sub.add_parser('inspect-interrupted');inspect.add_argument('--request-id',required=True)
    cleanup=sub.add_parser('cleanup-reviewed')
    cleanup.add_argument('--request-id',required=True);cleanup.add_argument('--plan-sha256',required=True)
    args=p.parse_args();os.umask(0o077)
    w=Worker(args.state)
    if args.command in ('inspect-interrupted','cleanup-reviewed'):
        cleanup=load('worker_cleanup','recovery-cleanup.py')
        result=(cleanup.review(w,args.request_id,d) if args.command=='inspect-interrupted'
                else cleanup.clean(w,args.request_id,args.plan_sha256,d))
        print(json.dumps(result,indent=2));return 0
    result=(w.run(args.request_id,args.day,args.trust) if args.command=='run'
            else w.retry_registration(args.request_id))
    # Do not expose local trust paths from the persisted input binding.
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},indent=2))
    return 0 if result['outcome']=='succeeded' and result['registration']=='recorded' else 2


if __name__=='__main__':raise SystemExit(main())
