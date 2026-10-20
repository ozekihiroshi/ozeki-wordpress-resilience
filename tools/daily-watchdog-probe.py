#!/usr/bin/env python3
"""Read-only daily report freshness endpoint for the independent watchdog."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import sys

def load():
    spec = importlib.util.spec_from_file_location('daily_transfer', Path(__file__).with_name('daily-status-transfer.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def endpoint(config, packet):
    if (set(packet) != {'format', 'nonce'} or packet['format'] != 'owr-watchdog-probe-v1'
            or not isinstance(packet['nonce'], str) or not re.fullmatch('[a-f0-9]{32}', packet['nonce'])):
        raise ValueError('invalid probe')
    daily = load()
    daily.t.ident(config['monitor_id'])
    value = None
    status = 'missing'
    try:
        report = daily.report(daily.t.read_file(config['report_file'], 65536), config['site_id'])
        # Report time, never probe time: reachable SSH cannot conceal a stalled publisher/relay.
        value = dict(format='owr-monitor-heartbeat-v1', monitor_id=config['monitor_id'],
                     completed_at=report['observed_at'], undelivered=0, open_incidents=0)
        status = 'present'
    except FileNotFoundError:
        pass
    except Exception:
        status = 'invalid'
    return dict(format='owr-watchdog-probe-result-v1', nonce=packet['nonce'],
                monitor_id=config['monitor_id'], status=status, heartbeat=value)

def main():
    import json
    import resource
    import signal
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (128*1024*1024, 128*1024*1024))
    signal.alarm(10)
    if os.environ.get('SSH_ORIGINAL_COMMAND') != 'watchdog-probe':
        raise ValueError('forced command only')
    daily = load()
    config = daily.t.read_file(args.config, 4096)
    print(json.dumps(endpoint(config, daily.t.decode(sys.stdin.buffer.read(1025), 1024))))

if __name__ == '__main__':
    main()
