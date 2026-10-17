#!/usr/bin/env python3
"""Verify the synthetic source baseline; never a recovery-success report."""
import hashlib
import http.cookiejar
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent.parent
baseline = json.loads((root / 'evidence/m1/phase1/source-baseline.json').read_text())
config = dict(line.strip().split('=', 1) for line in (root / '.local/runtime.env').read_text().splitlines() if '=' in line)
base = 'http://localhost:18081'
checks = []
jar = http.cookiejar.CookieJar()
client = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(jar))

def request(path, form=None):
    url = urllib.parse.urljoin(base, path)
    if urllib.parse.urlsplit(url).netloc != 'localhost:18081':
        raise ValueError('Fixture URL required')
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    try:
        with client.open(urllib.request.Request(url, data=data), timeout=20) as response:
            return response.status, response.read(), response.geturl()
    except urllib.error.HTTPError as error:
        return error.code, error.read(), error.geturl()

def check(condition, name):
    checks.append({'name': name, 'passed': bool(condition)})

try:
    ids = baseline['ids']
    for key, marker in [('home', 'OWR-HOME'), ('services', 'OWR-SERVICES'), ('contact', 'OWR-CONTACT'), ('post', 'OWR-NEWS')]:
        path = '/' if key == 'home' else '/?p=' + str(ids[key])
        status, body, _ = request(path)
        check(status == 200 and marker.encode() in body, 'http_' + key)
        if key == 'contact':
            contact_html = body.decode()
        if key == 'home':
            check('日本語と絵文字 🌱'.encode() in body, 'http_japanese_emoji')
            check(('?page_id=' + str(ids['services'])).encode() in body, 'internal_services_link')
            check(('?page_id=' + str(ids['contact'])).encode() in body, 'internal_contact_link')
    for name, asset in baseline['media'].items():
        status, body, _ = request('/wp-content/uploads/' + urllib.parse.quote(asset['relative']))
        check(status == 200 and hashlib.sha256(body).hexdigest() == asset['sha256'], 'http_media_' + name)
    match = re.search(r'name="_wpnonce" value="([^"]+)"', contact_html)
    check(match is not None, 'form_nonce_present')
    status, body, _ = request('/wp-admin/admin-post.php', {'action': 'owr_fixture_contact', '_wpnonce': 'invalid', 'message': 'OWR-SYNTHETIC-INQUIRY'})
    check(status == 403 and b'OWR_FORM_REJECTED' in body, 'form_rejects_bad_nonce')
    if match:
        status, body, _ = request('/wp-admin/admin-post.php', {'action': 'owr_fixture_contact', '_wpnonce': match.group(1), 'message': 'OWR-SYNTHETIC-INQUIRY'})
        check(status == 200 and body == b'OWR_FORM_ACCEPTED', 'form_accepts_synthetic_message')
    request('/wp-login.php')
    status, body, url = request('/wp-login.php', {'log': 'owradmin', 'pwd': config['OWR_ADMIN_PASSWORD'], 'wp-submit': 'Log In', 'redirect_to': base + '/wp-admin/', 'testcookie': '1'})
    check(status == 200 and '/wp-admin/' in url and any(c.name.startswith('wordpress_logged_in_') for c in jar), 'admin_login_http')
    status, body, _ = request('/wp-admin/profile.php')
    check(status == 200 and b'owradmin' in body and b'user_login' in body, 'admin_profile_http')
except Exception as error:
    # Do not serialize requests/cookies/passwords.
    checks.append({'name': 'http_execution_' + type(error).__name__, 'passed': False})
report = {'schema_version': 1, 'kind': 'phase1_source_http', 'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': checks, 'passed': bool(checks) and all(c['passed'] for c in checks)}
(root / 'evidence/m1/phase1/http-checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
(root / ('evidence/m1/phase1/http-checks-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'passed': report['passed'], 'checks': len(checks), 'failed': [c['name'] for c in checks if not c['passed']]}))
raise SystemExit(0 if report['passed'] else 1)
