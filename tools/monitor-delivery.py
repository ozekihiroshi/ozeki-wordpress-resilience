"""SMTP notification adapter; test mode is strictly loopback, real mode requires TLS."""
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime
import ipaddress
import json
import os
from pathlib import Path
import smtplib
import ssl
import stat


def send(config, payload):
    transport = config['transport']
    if transport not in ('smtp_test', 'smtp_starttls', 'smtp_tls'):
        raise ValueError('unsupported notification transport')
    host, port = config['host'], config['port']
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid SMTP port')
    timeout = config.get('timeout_seconds', 10)
    if not 0 < timeout <= 30:
        raise ValueError('invalid SMTP timeout')
    for key in ('from', 'to'):
        address = config[key]
        if not isinstance(address, str) or any(c in address for c in '\r\n,;<> ') or address.count('@') != 1:
            raise ValueError('one mailbox required')
    if transport == 'smtp_test':
        if not ipaddress.ip_address(host).is_loopback or config.get('credentials_file'):
            raise ValueError('test SMTP must be unauthenticated loopback')
    credentials = None
    if config.get('credentials_file'):
        path = Path(config['credentials_file'])
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('SMTP credentials require owner-only regular file')
        credentials = json.loads(path.read_text())
    message = EmailMessage()
    message['From'], message['To'] = config['from'], config['to']
    message['Subject'] = f"[OWR] {payload['transition']}: {payload['kind']}"
    message['Message-ID'] = f"<{payload['event_id']}@owr.invalid>"
    message['Date'] = format_datetime(datetime.fromisoformat(payload['observed_at']))
    message.set_content(json.dumps(payload, ensure_ascii=False, indent=2))
    context = ssl.create_default_context()
    client = smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) if transport == 'smtp_tls' else smtplib.SMTP(host, port, timeout=timeout)
    with client:
        client.ehlo()
        if transport == 'smtp_starttls':
            client.starttls(context=context)
            client.ehlo()
        if credentials:
            client.login(credentials['username'], credentials['password'])
        refused = client.send_message(message)
        if refused:
            raise RuntimeError('SMTP recipient rejected')
