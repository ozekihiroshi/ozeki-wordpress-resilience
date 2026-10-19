"""Secret-free delivery health report and heartbeat for an independent watchdog."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid


def prepare(db, now):
    db.executescript('''CREATE TABLE IF NOT EXISTS delivery_health_clock(
      channel TEXT,event TEXT,first_seen REAL,accepted_at REAL,PRIMARY KEY(channel,event));
      CREATE TABLE IF NOT EXISTS delivery_health_meta(key TEXT PRIMARY KEY,value REAL);''')
    previous = db.execute("SELECT value FROM delivery_health_meta WHERE key='completed'").fetchone()
    if previous and now < previous[0]:
        raise ValueError('delivery health clock moved backwards')
    db.execute('''INSERT OR IGNORE INTO delivery_health_clock(channel,event,first_seen)
                  SELECT channel,event,? FROM deliveries''', (now,))


def atomic_json(path, body):
    path = Path(path)
    tmp = path.with_name('.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('x') as stream:
            os.chmod(tmp, 0o600)
            json.dump(body, stream, ensure_ascii=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


def publish(db, config, now, channel_errors):
    policy = config.get('health', {})
    backlog = policy.get('backlog_seconds', 300)
    ack = policy.get('ack_seconds', 300)
    db.execute('''UPDATE delivery_health_clock SET accepted_at=? WHERE accepted_at IS NULL
      AND EXISTS(SELECT 1 FROM deliveries d WHERE d.channel=delivery_health_clock.channel
        AND d.event=delivery_health_clock.event AND d.status='accepted')''', (now,))
    rows = db.execute('''SELECT d.rowid AS sequence,d.*,c.first_seen,c.accepted_at
      FROM deliveries d JOIN delivery_health_clock c USING(channel,event) ORDER BY d.rowid''').fetchall()
    problems = []
    def add(channel, kind, event=None):
        # No payloads, addresses, receipt identifiers, API error bodies or credential paths.
        problems.append(dict(channel=channel, kind=kind, event_id=event))
    for channel in sorted(channel_errors):
        add(channel, 'channel_configuration_failed')
    for row in rows:
        resolved = any(other['sequence'] > row['sequence'] and other['channel'] == row['channel'] and
                       other['incident'] == row['incident'] and
                       json.loads(other['payload'])['transition'] == 'resolved' for other in rows)
        if row['status'] in ('unknown', 'rejected'):
            add(row['channel'], 'delivery_' + row['status'], row['event'])
        if row['status'] in ('pending', 'retry', 'sending') and now-row['first_seen'] >= backlog:
            add(row['channel'], 'delivery_backlog', row['event'])
        if row['poll_error']:
            add(row['channel'], 'receipt_check_failed', row['event'])
        if not resolved and row['receipt_state'] == 'expired':
            add(row['channel'], 'ack_expired', row['event'])
        elif not resolved and row['receipt_state'] == 'waiting' and row['accepted_at'] is not None and now-row['accepted_at'] >= ack:
            add(row['channel'], 'ack_overdue', row['event'])
    monitor_id = policy.get('monitor_id', 'delivery-' + hashlib.sha256(
        str(Path(config['state']).resolve()).encode()).hexdigest()[:16])
    stamp = datetime.fromtimestamp(now, timezone.utc).isoformat()
    summary = dict(format='owr-delivery-health-v1', monitor_id=monitor_id, completed_at=stamp,
                   healthy=not problems, problems=problems, thresholds=dict(backlog_seconds=backlog,ack_seconds=ack))
    directory = Path(config['state'])
    atomic_json(directory/'delivery-health.json', summary)
    # Compatibility with the independent watchdog: this count means outstanding health
    # conditions, including missing acknowledgement, not simply unsent messages.
    atomic_json(directory/'delivery-heartbeat.json', dict(format='owr-monitor-heartbeat-v1',
        monitor_id=monitor_id, completed_at=stamp, undelivered=len(problems), open_incidents=len(problems)))
    db.execute("INSERT OR REPLACE INTO delivery_health_meta VALUES('completed',?)", (now,))
    db.commit()
    return summary
