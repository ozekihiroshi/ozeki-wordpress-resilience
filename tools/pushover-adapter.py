"""Pushover provider for the isolated notification lab; no provider secrets in errors."""
import json
import os
import re
import ssl
import stat
import urllib.error
import urllib.parse
import urllib.request


class DeliveryError(Exception):
    def __init__(self, outcome):
        self.outcome = outcome
        super().__init__(outcome)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Adapter:
    capabilities = {'acknowledgement': True, 'cancel': True, 'emergency_retry': True}

    def __init__(self, config):
        if set(config) - {'transport', 'credentials_file', 'retry', 'expire', 'timeout_seconds'}:
            raise ValueError('unknown Pushover option')
        self.retry, self.expire = config.get('retry', 60), config.get('expire', 1800)
        self.timeout = config.get('timeout_seconds', 10)
        if type(self.retry) is not int or not 30 <= self.retry <= 10800:
            raise ValueError('invalid retry')
        if type(self.expire) is not int or not self.retry <= self.expire <= 10800:
            raise ValueError('invalid expire')
        if type(self.timeout) is not int or not 1 <= self.timeout <= 30:
            raise ValueError('invalid timeout')
        # Linux/WSL only: open without following symlinks and validate the opened file.
        fd = os.open(config['credentials_file'], os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise ValueError('credentials require owner-only regular file')
            credentials = json.loads(stream.read(4097))
        if set(credentials) != {'token', 'user'} or any(
                not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9]{30}', v)
                for v in credentials.values()):
            raise ValueError('invalid credentials format')
        self.credentials = credentials
        # Never inherit proxy configuration or forward secrets through redirects.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def request(self, path, fields=None):
        fields = dict(fields or {}, token=self.credentials['token'])
        encoded = urllib.parse.urlencode(fields)
        url = 'https://api.pushover.net/1/' + path
        req = urllib.request.Request(url, data=encoded.encode())
        # Only receipt queries are GET; tokens must never be logged by callers.
        if path.startswith('receipts/') and path.endswith('.json') and '/cancel' not in path:
            req = urllib.request.Request(url + '?' + encoded)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                raw = response.read(65537)
                if len(raw) > 65536:
                    raise DeliveryError('unknown')
                body = json.loads(raw)
            if not isinstance(body, dict) or body.get('status') not in (0, 1):
                raise DeliveryError('unknown')
            if body['status'] != 1:
                raise DeliveryError('rejected')
            return body
        except urllib.error.HTTPError as exc:
            # An explicit quota rejection can be retried later; a lost/5xx response
            # may follow acceptance, so do not automatically duplicate emergencies.
            raise DeliveryError('retry' if exc.code == 429 else
                                'unknown' if exc.code >= 500 else 'rejected') from None
        except (OSError, ValueError, urllib.error.URLError):
            raise DeliveryError('unknown') from None

    def send(self, event):
        urgent = event['transition'] == 'opened'
        body = self.request('messages.json', dict(user=self.credentials['user'],
            title='OWR lab: ' + event['kind'],
            message='\n'.join(str(event[k]) for k in ('site', 'transition', 'kind', 'observed_at', 'event_id')),
            priority=2 if urgent else 0,
            **({'retry': self.retry, 'expire': self.expire} if urgent else {})))
        receipt = body.get('receipt')
        if urgent and (not isinstance(receipt, str) or not re.fullmatch(r'[A-Za-z0-9]{30}', receipt)):
            raise DeliveryError('unknown')
        return {'receipt': receipt}

    def poll(self, receipt):
        self.validate_receipt(receipt)
        body = self.request('receipts/' + receipt + '.json')
        if any(type(body.get(k)) is not int or body[k] not in (0, 1) for k in ('acknowledged', 'expired')):
            raise DeliveryError('unknown')
        return {'acknowledged': body['acknowledged'], 'expired': body['expired']}

    def cancel(self, receipt):
        self.validate_receipt(receipt)
        self.request('receipts/' + receipt + '/cancel.json')

    @staticmethod
    def validate_receipt(receipt):
        if not isinstance(receipt, str) or not re.fullmatch(r'[A-Za-z0-9]{30}', receipt):
            raise ValueError('invalid receipt')
