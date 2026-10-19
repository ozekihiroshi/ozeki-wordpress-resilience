#!/usr/bin/env python3
"""Isolated provider-neutral outbox. Does not modify the existing monitor databases."""
import argparse
import importlib.util
import json
from pathlib import Path
import sqlite3
import time
import re
from datetime import datetime

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


push = load('pushover-adapter')
health = load('notification-health')

KINDS = {'backup_missing', 'backup_failed', 'backup_unknown', 'approval_pending',
         'approval_expired', 'restore_failed', 'restore_incomplete', 'source_unreadable',
         'monitor_stopped', 'heartbeat_invalid', 'notification_delivery_failed'}


def validate_config(config):
    channels = config['channels']
    if not isinstance(channels, list) or not 1 <= len(channels) <= (400 if config.get('managed') else 20):
        raise ValueError('one to twenty channels required')
    ids = []
    for channel in channels:
        name = channel['id']
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name):
            raise ValueError('invalid channel id')
        ids.append(name)
        if channel['provider']['transport'] not in ('pushover','smtp_test','smtp_tls','smtp_starttls'):
            raise ValueError('provider not implemented')
        if 'kinds' in channel:
            kinds = channel['kinds']
            if not isinstance(kinds,list) or not kinds or any(not isinstance(k,str) or k not in KINDS for k in kinds) or len(kinds)!=len(set(kinds)):
                raise ValueError('invalid alarm selection')
    if len(ids) != len(set(ids)):
        raise ValueError('unique channels required')
    policy = config.get('health', {})
    if not isinstance(policy,dict) or set(policy)-{'monitor_id','backlog_seconds','ack_seconds'}:
        raise ValueError('invalid health policy')
    for field in ('backlog_seconds','ack_seconds'):
        value = policy.get(field,300)
        if type(value) is not int or not 1 <= value <= 86400:
            raise ValueError('invalid health threshold')
    if 'monitor_id' in policy and (not isinstance(policy['monitor_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',policy['monitor_id'])):
        raise ValueError('invalid health monitor id')


class SMTP:
    def __init__(self, config):
        self.config = config
    def send(self, event):
        load('monitor-delivery').send(self.config, event)
        return {}


def adapter(config):
    if config['transport'] == 'pushover':
        return push.Adapter(config)
    if config['transport'] in ('smtp_test', 'smtp_tls', 'smtp_starttls'):
        return SMTP(config)
    raise ValueError('unsupported provider')


def validate(event):
    for key in ('event_id', 'site', 'kind', 'domain', 'subject', 'transition', 'observed_at'):
        value = event.get(key)
        if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(ord(c) < 32 for c in value):
            raise ValueError('invalid event')
    if not re.fullmatch(r'[a-f0-9]{32,64}', event['event_id']):
        raise ValueError('invalid event id')
    if event['transition'] not in ('opened', 'resolved') or datetime.fromisoformat(event['observed_at']).tzinfo is None:
        raise ValueError('invalid transition or timestamp')
    # Do not persist arbitrary additional fields containing source logs or secrets.
    return {k: event[k] for k in ('event_id', 'site', 'kind', 'domain', 'subject', 'transition', 'observed_at')}


def import_events(db, config):
    if config.get('managed'):
        return load('notification-live').import_events(db, config, validate)
    # Entire source is read in a consistent snapshot. Never clear its delivered flags.
    source = Path(config['source_outbox']).resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(source, uri=True) as original:
        rows = original.execute('SELECT payload FROM outbox ORDER BY rowid').fetchall()
    for (raw,) in rows:
        event = validate(json.loads(raw))
        body = json.dumps(event, sort_keys=True)
        incident = json.dumps([event[k] for k in ('site', 'domain', 'kind', 'subject')])
        for channel in config['channels']:
            if channel.get('kinds') is not None and event['kind'] not in channel['kinds']:
                continue
            key = (channel['id'], event['event_id'])
            old = db.execute('SELECT payload FROM deliveries WHERE channel=? AND event=?', key).fetchone()
            if old and old[0] != body:
                raise ValueError('event identity conflict')
            db.execute('INSERT OR IGNORE INTO deliveries(channel,event,incident,payload) VALUES(?,?,?,?)',
                       (*key, incident, body))
    return rows


def run(config, now=None, factory=adapter):
    import fcntl
    injected_clock = now is not None
    now = time.time() if now is None else now
    validate_config(config)
    directory = Path(config['state'])
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory/'dispatch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with sqlite3.connect(directory/'dispatch.sqlite') as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA synchronous=FULL')
            db.executescript('''CREATE TABLE IF NOT EXISTS settings(binding TEXT);
              CREATE TABLE IF NOT EXISTS deliveries(
                channel TEXT,event TEXT,incident TEXT,payload TEXT,status TEXT DEFAULT 'pending',
                receipt TEXT,receipt_state TEXT,attempts INTEGER DEFAULT 0,next_at REAL DEFAULT 0,
                poll_at REAL DEFAULT 0,poll_error INTEGER DEFAULT 0,PRIMARY KEY(channel,event));''')
            binding = json.dumps(config, sort_keys=True)
            old = db.execute('SELECT binding FROM settings').fetchone()
            if old and old[0] != binding:
                raise ValueError('configuration changed; explicit migration required')
            if not old:
                db.execute('INSERT INTO settings VALUES(?)', (binding,))
            import_events(db, config)
            health.prepare(db, now)
            # A crash while sending is ambiguous; never blindly resend an emergency.
            db.execute("UPDATE deliveries SET status='unknown' WHERE status='sending'")
            db.commit()
            channel_errors = set()
            for channel in config['channels']:
                name = channel['id']
                if config.get('managed') and not channel.get('active') and not db.execute(
                    "SELECT 1 FROM deliveries WHERE channel=? AND (status IN ('pending','retry') OR receipt_state='waiting') LIMIT 1", (name,)).fetchone():
                    continue
                try:
                    provider = factory(channel['provider'])
                except Exception:
                    channel_errors.add(name)
                    continue  # Broken credentials on one channel cannot block another.
                rows = db.execute('SELECT rowid,* FROM deliveries WHERE channel=? ORDER BY rowid', (name,)).fetchall()
                for row in rows:
                    event = json.loads(row['payload'])
                    # Suppress old, unsent opening alerts once their resolution is imported.
                    resolved = any(r['incident'] == row['incident'] and r['rowid'] > row['rowid'] and
                                   json.loads(r['payload'])['transition'] == 'resolved' for r in rows)
                    if resolved and row['status'] in ('pending', 'retry'):
                        db.execute("UPDATE deliveries SET status='superseded' WHERE channel=? AND event=?", (name,row['event']))
                        continue
                    if row['receipt'] and row['receipt_state'] == 'waiting' and row['poll_at'] <= now:
                        try:
                            if resolved:
                                provider.cancel(row['receipt'])
                                state = 'cancelled'
                            else:
                                check = provider.poll(row['receipt'])
                                state = 'acknowledged' if check['acknowledged'] else 'expired' if check['expired'] else 'waiting'
                            db.execute('UPDATE deliveries SET receipt_state=?,poll_at=?,poll_error=0 WHERE channel=? AND event=?',
                                       (state,now+60,name,row['event']))
                        except Exception:
                            db.execute('UPDATE deliveries SET poll_at=?,poll_error=1 WHERE channel=? AND event=?', (now+300,name,row['event']))
                        db.commit()
                    if row['status'] not in ('pending','retry') or row['next_at'] > now:
                        continue
                    db.execute("UPDATE deliveries SET status='sending',attempts=attempts+1 WHERE channel=? AND event=?", (name,row['event']))
                    db.commit()
                    try:
                        result = provider.send(event)
                        receipt = result.get('receipt')
                        db.execute("UPDATE deliveries SET status='accepted',receipt=?,receipt_state=?,poll_at=? WHERE channel=? AND event=?",
                                   (receipt,'waiting' if receipt else None,now+60,name,row['event']))
                    except Exception as exc:
                        outcome = exc.outcome if isinstance(exc, push.DeliveryError) else 'unknown'
                        delay = min(3600, 60 * 2 ** min(row['attempts'],6))
                        db.execute('UPDATE deliveries SET status=?,next_at=? WHERE channel=? AND event=?',
                                   (outcome,now+delay,name,row['event']))
                    db.commit()
            health.publish(db, config, time.time() if not injected_clock else now, channel_errors)
            if config.get('managed'):
                report_path=directory/'delivery-health.json'
                report=json.loads(report_path.read_text())
                import hashlib
                report['config_hash']=hashlib.sha256(binding.encode()).hexdigest()
                health.atomic_json(report_path,report)
            return [dict(r) for r in db.execute('SELECT channel,status,receipt_state,poll_error,count(*) AS count FROM deliveries GROUP BY channel,status,receipt_state,poll_error')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        result = run(config)
        health_report = json.loads((Path(config['state'])/'delivery-health.json').read_text())
        print(json.dumps(result))
        # Expired receipts for resolved incidents are historical; the health report
        # distinguishes them from outstanding acknowledgement failures.
        return int(not health_report['healthy'] or any(
            r['status'] in ('unknown','rejected','retry','pending') or r['poll_error'] for r in result))
    except Exception as exc:
        print(json.dumps({'error_type': type(exc).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
