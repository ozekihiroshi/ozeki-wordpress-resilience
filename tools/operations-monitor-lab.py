#!/usr/bin/env python3
"""Read-only lab observation and durable, idempotent local operator inbox delivery."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

JST = timezone(timedelta(hours=9))


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('timezone required')
    return result


def observe(config, now):
    """A failed domain remains unknown, never resolves previously open incidents."""
    if now.tzinfo is None:
        raise ValueError('timezone required')
    active, valid = {}, set()

    def add(domain, kind, subject):
        key = ':'.join((domain, kind, subject))
        active[key] = dict(domain=domain, kind=kind, subject=subject)

    for domain in ('daily', 'restore'):
        before = set(active)
        try:
            if domain == 'daily':
                ledger = Path(config['daily_state']) / 'state.sqlite'
                with sqlite3.connect(ledger.resolve().as_uri() + '?mode=ro', uri=True, timeout=5) as db:
                    db.row_factory = sqlite3.Row
                    db.execute('BEGIN')  # Runs and events must come from one SQLite snapshot.
                    if db.execute("SELECT value FROM settings WHERE key='storage'").fetchone()[0] != 's3':
                        raise ValueError('S3 ledger required')
                    rows = {r['day']: dict(r) for r in db.execute('SELECT * FROM runs')}
                    events = list(db.execute('SELECT at,day,state FROM events ORDER BY n'))
                start = date.fromisoformat(config['start_day'])
                end = now.astimezone(JST).date()
                if (end - start).days > 3660 or start > end:
                    raise ValueError('invalid monitoring interval')
                day = start
                while day <= end:
                    label = day.isoformat()
                    due = datetime.combine(day, time(config.get('hour_jst', 3)), JST)
                    row = rows.get(label)
                    state = row['state'] if row else None
                    if state not in (None, 'running', 'failed', 'unknown', 'awaiting_approval', 'approved'):
                        raise ValueError('unexpected S3 state')
                    if now >= due + timedelta(seconds=config.get('capture_grace_seconds', 7200)) and state not in ('awaiting_approval', 'approved'):
                        add(domain, 'backup_missing', label)
                    if state in ('failed', 'unknown'):
                        add(domain, 'backup_' + state, label)
                    if state == 'awaiting_approval':
                        candidate = json.loads((Path(row['report']).parent / 'candidate/candidate.json').read_text())
                        if instant(candidate['expires_at']) <= now:
                            add(domain, 'approval_expired', label)
                        times = [instant(e['at']) for e in events if e['day'] == label and e['state'] == state]
                        if not times:
                            raise ValueError('pending timestamp missing')
                        if min(times) > now:
                            raise ValueError('future pending timestamp')
                        if now >= min(times) + timedelta(seconds=config.get('pending_seconds', 86400)):
                            add(domain, 'approval_pending', label)
                    if state == 'approved':
                        approval = json.loads((Path(row['report']).parent / 'approval.json').read_text())
                        if approval['state'] != 'approved':
                            raise ValueError('invalid approval')
                        if instant(approval['approval_expires_at']) <= now:
                            add(domain, 'approval_expired', label)
                    day += timedelta(days=1)
            else:
                directory = Path(config['restore_journal'])
                if not directory.is_dir():
                    raise ValueError('restore journal unavailable')
                latest = {}
                for path in sorted(directory.glob('*.json')):
                    record = json.loads(path.read_text())
                    if record['format'] != 'owr-restore-attempt-v1':
                        raise ValueError('invalid restore journal')
                    at = instant(record['started_at'])
                    if at > now:
                        raise ValueError('future restore attempt')
                    state = record['state']
                    if not re.fullmatch(r'AWS-[0-9a-f]{16}', record['set_id']):
                        raise ValueError('unexpected lab set')
                    if state not in ('running', 'failed', 'succeeded'):
                        raise ValueError('invalid restore state')
                    # Failed attempts resolve only after a later successful attempt for this set.
                    latest.setdefault(record['set_id'], []).append((at, record['attempt_id'], state))
                for set_id, attempts in latest.items():
                    attempts.sort()
                    success = max((at for at, _, s in attempts if s == 'succeeded'), default=None)
                    for at, _, state in attempts:
                        if success is not None and at <= success:
                            continue
                        if state == 'failed':
                            add(domain, 'restore_failed', set_id)
                        if state == 'running' and now >= at + timedelta(seconds=config.get('restore_timeout_seconds', 2100)):
                            add(domain, 'restore_incomplete', set_id)
            valid.add(domain)
        except (OSError, ValueError, KeyError, TypeError, IndexError, sqlite3.Error):
            for key in set(active) - before:
                del active[key]
            add('monitor', 'source_unreadable', domain)
    valid.add('monitor')
    return active, valid


def inbox_delivery(directory, payload):
    """Test receiver: durable atomic receipt. Stable event IDs make retries idempotent."""
    import os
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / (payload['event_id'] + '.json')
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True) + '\n'
    if target.exists():
        if target.read_text() != body:
            raise ValueError('receipt conflict')
        return
    temp = directory / ('.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x') as out:
            os.chmod(temp, 0o600)
            out.write(body)
            out.flush()
            os.fsync(out.fileno())
        os.link(temp, target)
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temp.unlink(missing_ok=True)


def tick(config, now, send=None):
    if now.tzinfo is None:
        raise ValueError('timezone required')
    for key, default in [('capture_grace_seconds',7200), ('pending_seconds',86400), ('restore_timeout_seconds',2100)]:
        value = config.get(key, default)
        if type(value) is not int or not 0 <= value <= 604800:
            raise ValueError('invalid threshold')
    if type(config.get('hour_jst',3)) is not int or not 0 <= config.get('hour_jst',3) <= 23:
        raise ValueError('invalid schedule hour')
    directory = Path(config['monitor_state'])
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    # A single transaction serializes detection and delivery; a lost acknowledgement
    # rolls back locally and retries the same durable event ID on the next tick.
    with sqlite3.connect(directory / 'monitor.sqlite', timeout=5) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''
          CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
          CREATE TABLE IF NOT EXISTS incidents (key TEXT PRIMARY KEY, domain TEXT, data TEXT, open INTEGER, generation INTEGER);
          CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, payload TEXT, delivered INTEGER DEFAULT 0, attempts INTEGER DEFAULT 0);
        ''')
        db.execute('BEGIN IMMEDIATE')
        binding = json.dumps(config, sort_keys=True)
        old = db.execute("SELECT value FROM settings WHERE key='config'").fetchone()
        if old and old[0] != binding:
            raise ValueError('monitor configuration changed; use a new state directory')
        db.execute("INSERT OR IGNORE INTO settings VALUES ('config',?)", (binding,))
        db.execute("INSERT OR IGNORE INTO settings VALUES ('instance',?)", (uuid.uuid4().hex,))
        instance = db.execute("SELECT value FROM settings WHERE key='instance'").fetchone()[0]
        previous = db.execute("SELECT value FROM settings WHERE key='last_tick'").fetchone()
        if previous and instant(previous[0]) > now:
            raise ValueError('clock moved backwards')
        active, valid = observe(config, now)
        existing = {r['key']: dict(r) for r in db.execute('SELECT * FROM incidents')}
        for key in sorted(set(existing) | set(active)):
            old = existing.get(key)
            item = active.get(key) or json.loads(old['data'])
            if item['domain'] not in valid:
                continue
            opened = key in active
            if old and bool(old['open']) == opened:
                continue
            generation = old['generation'] + 1 if old else 1
            event_id = hashlib.sha256((instance + ':' + key + ':' + str(generation)).encode()).hexdigest()
            payload = dict(format='owr-operator-notification-v1', event_id=event_id,
                           site=config['site'], transition='opened' if opened else 'resolved',
                           observed_at=now.isoformat(), **item)
            db.execute('INSERT OR REPLACE INTO incidents VALUES (?,?,?,?,?)', (key, item['domain'], json.dumps(item), int(opened), generation))
            db.execute('INSERT INTO outbox(id,payload) VALUES (?,?)', (event_id, json.dumps(payload)))
        db.execute("INSERT OR REPLACE INTO settings VALUES ('last_tick',?)", (now.isoformat(),))
        db.commit()  # Never lose events even if delivery fails or the process terminates.
        db.execute('BEGIN IMMEDIATE')
        sender = send or (lambda p: inbox_delivery(config['test_inbox'], p))
        for row in db.execute('SELECT * FROM outbox WHERE delivered=0 ORDER BY rowid').fetchall():
            db.execute('UPDATE outbox SET attempts=attempts+1 WHERE id=?', (row['id'],))
            try:
                sender(json.loads(row['payload']))
            except Exception:
                break  # Keep FIFO ordering; no exception strings or secrets in messages.
            db.execute('UPDATE outbox SET delivered=1 WHERE id=?', (row['id'],))
        result = dict(open_incidents=[json.loads(r[0]) for r in db.execute('SELECT data FROM incidents WHERE open=1 ORDER BY key')],
                      undelivered=db.execute('SELECT count(*) FROM outbox WHERE delivered=0').fetchone()[0],
                      delivered_total=db.execute('SELECT count(*) FROM outbox WHERE delivered=1').fetchone()[0])
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    a = p.parse_args()
    result = tick(json.loads(a.config.read_text()), datetime.now(timezone.utc))
    print(json.dumps(result, indent=2))
    return 2 if result['open_incidents'] or result['undelivered'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
