#!/usr/bin/env python3
"""One-shot scheduled monitor and separate dead-man watchdog. No signing or backup execution."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import uuid

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


monitor = load('operations-monitor-lab')
delivery = load('monitor-delivery')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name('.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x') as out:
            os.chmod(temporary, 0o600)
            json.dump(value, out)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory/'runtime.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def selected_sender(config, injected):
    if injected is not None:
        return injected
    return lambda event: delivery.send(config['delivery'], event)


def run_monitor(config, now=None, sender=None):
    injected_clock = now is not None
    now = now or datetime.now(timezone.utc)
    path = Path(config['heartbeat_file'])
    with locked(Path(config['monitor']['monitor_state'])):
        # Never touch the heartbeat when observation or durable state processing fails.
        result = monitor.tick(config['monitor'], now, selected_sender(config, sender))
        completed = now if injected_clock else datetime.now(timezone.utc)
        write_json(path, dict(format='owr-monitor-heartbeat-v1', monitor_id=config['monitor_id'],
                             completed_at=completed.isoformat(), undelivered=result['undelivered'],
                             open_incidents=len(result['open_incidents'])))
        if config.get('heartbeat_ssh_config'):
            transfer = load('heartbeat-ssh')
            ssh_config = json.loads(Path(config['heartbeat_ssh_config']).read_text())
            transfer.send(ssh_config, path.read_bytes())
            result['heartbeat_delivery'] = 'acknowledged'
        return result


def heartbeat_state(config, now, started, last_seen):
    threshold = config.get('stale_after_seconds', 900)
    if type(threshold) is not int or not 1 <= threshold <= 86400:
        raise ValueError('invalid heartbeat deadline')
    path = Path(config['heartbeat_file'])
    try:
        if not path.exists():
            return ({'monitor_stopped'} if (now-started).total_seconds() >= threshold else set()), last_seen
        h = json.loads(path.read_text())
        stamp = monitor.instant(h['completed_at'])
        if (h['format'] != 'owr-monitor-heartbeat-v1' or h['monitor_id'] != config['monitor_id']
                or stamp > now + timedelta(seconds=5) or (last_seen and stamp < last_seen)
                or type(h['undelivered']) is not int or h['undelivered'] < 0):
            raise ValueError('invalid heartbeat')
        active = set()
        if (now-stamp).total_seconds() >= threshold:
            active.add('monitor_stopped')
        if h['undelivered']:
            active.add('notification_delivery_failed')
        return active, stamp
    except (OSError, ValueError, KeyError, TypeError):
        return {'heartbeat_invalid'}, last_seen


def run_watchdog(config, now=None, sender=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('timezone required')
    directory = Path(config['watchdog_state'])
    with locked(directory), sqlite3.connect(directory/'watchdog.sqlite') as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        db.executescript('''CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
            CREATE TABLE IF NOT EXISTS incidents(kind TEXT PRIMARY KEY,active INTEGER);
            CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT,delivered INTEGER DEFAULT 0);''')
        db.execute('BEGIN IMMEDIATE')
        binding = json.dumps(config, sort_keys=True)
        saved = dict(db.execute('SELECT key,value FROM settings'))
        if saved.get('config', binding) != binding:
            raise ValueError('watchdog configuration changed; use new state directory')
        if saved.get('last_tick') and monitor.instant(saved['last_tick']) > now:
            raise ValueError('watchdog clock moved backwards')
        started = monitor.instant(saved.get('started', now.isoformat()))
        last_seen = monitor.instant(saved['last_seen']) if saved.get('last_seen') else None
        active, stamp = heartbeat_state(config, now, started, last_seen)
        old = dict(db.execute('SELECT kind,active FROM incidents'))
        if 'heartbeat_invalid' in active or 'monitor_stopped' in active:
            active |= {kind for kind, opened in old.items() if opened}
        for kind in sorted(set(old) | active):
            opened = kind in active
            if bool(old.get(kind, 0)) == opened:
                continue
            event = dict(format='owr-operator-notification-v1', event_id=uuid.uuid4().hex,
                         site=config['monitor_id'], domain='watchdog', kind=kind,
                         subject=config['monitor_id'], transition='opened' if opened else 'resolved',
                         observed_at=now.isoformat())
            db.execute('INSERT OR REPLACE INTO incidents VALUES(?,?)', (kind, int(opened)))
            db.execute('INSERT INTO outbox(id,payload) VALUES(?,?)', (event['event_id'],json.dumps(event)))
        values = dict(config=binding, started=started.isoformat(), last_tick=now.isoformat())
        if stamp:
            values['last_seen'] = stamp.isoformat()
        db.executemany('INSERT OR REPLACE INTO settings VALUES(?,?)', values.items())
        db.commit()
        db.execute('BEGIN IMMEDIATE')
        send = selected_sender(config, sender)
        for row in db.execute('SELECT * FROM outbox WHERE delivered=0 ORDER BY rowid').fetchall():
            try:
                send(json.loads(row['payload']))
            except Exception:
                break
            db.execute('UPDATE outbox SET delivered=1 WHERE id=?', (row['id'],))
        return dict(active=sorted(active), undelivered=db.execute('SELECT count(*) FROM outbox WHERE delivered=0').fetchone()[0])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['monitor','watchdog'])
    p.add_argument('--config', type=Path, required=True)
    a = p.parse_args()
    try:
        config = json.loads(a.config.read_text())
        result = (run_monitor if a.action == 'monitor' else run_watchdog)(config)
        print(json.dumps(result))
        return 2 if result.get('open_incidents') or result.get('active') or result['undelivered'] else 0
    except Exception as exc:
        print(json.dumps({'completed': False, 'error_type': type(exc).__name__}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
