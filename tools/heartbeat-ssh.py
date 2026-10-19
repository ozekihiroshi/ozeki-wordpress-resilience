#!/usr/bin/env python3
"""Bounded heartbeat receiver and pinned, dedicated-key SSH sender (Linux)."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile

LIMIT = 4096
FIELDS = {'format','monitor_id','completed_at','undelivered','open_incidents'}


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate field')
        value[key] = item
    return value


def parse(raw, monitor_id, now=None):
    if len(raw) > LIMIT:
        raise ValueError('oversized heartbeat')
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('unexpected fields')
    if value['format'] != 'owr-monitor-heartbeat-v1' or value['monitor_id'] != monitor_id:
        raise ValueError('wrong heartbeat identity')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', monitor_id):
        raise ValueError('invalid monitor id')
    for key in ('undelivered','open_incidents'):
        if type(value[key]) is not int or not 0 <= value[key] <= 1000000000:
            raise ValueError('invalid counter')
    stamp = datetime.fromisoformat(value['completed_at'])
    if stamp.tzinfo is None or stamp > (now or datetime.now(timezone.utc)) + timedelta(seconds=5):
        raise ValueError('invalid completion time')
    body = (json.dumps(value, sort_keys=True, separators=(',',':')) + '\n').encode()
    return value, stamp, body


def receive(raw, directory, monitor_id, now=None):
    value, stamp, body = parse(raw, monitor_id, now)
    target = directory/'heartbeat.json'
    # This directory is provisioned by the administrator; no caller-supplied path.
    with (directory/'receive.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = 'accepted'
        if target.exists():
            _, previous_stamp, previous = parse(target.read_bytes(), monitor_id, now)
            if stamp < previous_stamp:
                raise ValueError('older heartbeat')
            if stamp == previous_stamp:
                if body != previous:
                    raise ValueError('conflicting heartbeat at same time')
                state = 'duplicate'
        if state == 'accepted':
            fd, temporary = tempfile.mkstemp(prefix='.heartbeat-',dir=directory)
            try:
                with os.fdopen(fd,'wb') as out:
                    os.fchmod(out.fileno(),0o640)
                    out.write(body);out.flush();os.fsync(out.fileno())
                os.replace(temporary,target)
                fd = os.open(directory,os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
            finally:
                if os.path.exists(temporary):os.unlink(temporary)
    return dict(format='owr-heartbeat-ack-v1',state=state,sha256=hashlib.sha256(body).hexdigest())


def command(config):
    for key in ('host','user'):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',config[key]):
            raise ValueError('invalid SSH endpoint')
    if type(config['port']) is not int or not 1 <= config['port'] <= 65535:
        raise ValueError('invalid port')
    return ['ssh','-F','/dev/null','-T','-p',str(config['port']),
            '-i',str(Path(config['identity_file']).resolve()),
            '-o','IdentitiesOnly=yes','-o','IdentityAgent=none','-o','BatchMode=yes',
            '-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=owr-heartbeat-dm',
            '-o','UserKnownHostsFile='+str(Path(config['known_hosts']).resolve()),
            '-o','GlobalKnownHostsFile=/dev/null','-o','UpdateHostKeys=no',
            '-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',
            '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2',
            config['user']+'@'+config['host'],'heartbeat']


def send(config, raw, runner=subprocess.run):
    _, _, body = parse(raw,config['monitor_id'])
    result = runner(command(config),input=body,capture_output=True,timeout=20)
    if result.returncode:
        raise RuntimeError('SSH heartbeat delivery failed')
    if len(result.stdout) > LIMIT:
        raise ValueError('invalid acknowledgement size')
    reply = json.loads(result.stdout)
    if (reply.get('format') != 'owr-heartbeat-ack-v1' or reply.get('state') not in ('accepted','duplicate')
            or reply.get('sha256') != hashlib.sha256(body).hexdigest()):
        raise ValueError('acknowledgement mismatch')
    return reply


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['receive','send'])
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    try:
        config=json.loads(a.config.read_text())
        if a.action=='receive':
            if os.environ.get('SSH_ORIGINAL_COMMAND') != 'heartbeat':
                raise ValueError('only heartbeat command is permitted')
            import resource
            resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
            resource.setrlimit(resource.RLIMIT_CPU,(2,2))
            signal.alarm(10)
            result=receive(sys.stdin.buffer.read(LIMIT+1),Path(config['directory']),config['monitor_id'])
        else:
            with Path(config['heartbeat_file']).open('rb') as stream:raw=stream.read(LIMIT+1)
            result=send(config,raw)
        print(json.dumps(result))
        return 0
    except Exception as exc:
        print(json.dumps({'accepted':False,'error_type':type(exc).__name__}))
        return 1


if __name__=='__main__':raise SystemExit(main())
