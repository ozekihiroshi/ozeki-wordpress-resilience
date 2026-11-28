"""Isolated reconstruction through existing WordPress/Markdown Documents HTTP forms.

No plugin internals, direct database writes, nonce fabrication, or rendered-cache repair.
The caller provides a plan selected by SiteSnapshot.markdownRegistrationPlan().
"""
import argparse
import base64
import getpass
import hashlib
import html
import http.cookiejar
import json
import re
import datetime
import urllib.parse
import urllib.request
from pathlib import Path
from html.parser import HTMLParser


class Unsupported(ValueError):
    pass


def image_references(raw, source_url, replacements):
    """Bounded inline-image grammar. Preserve code examples and all other bytes.

    Unsupported image forms stop this document rather than guessing an edit.
    replacements maps exact archived original URLs to destination media URLs.
    """
    text = raw.decode('utf-8')
    output, used, fenced = [], set(), None
    image = re.compile(r'!\[([^\]\r\n]*)\]\((<?)([^\s()<>]+)(>?)(\s+"[^"\r\n]*")?\)')
    def prose(part):
        if re.search(r'<img\b', part, re.I):
            raise Unsupported('HTML image needs an explicit reference mapping')
        remainder = image.sub('', part)
        if '![' in remainder:
            raise Unsupported('Reference-style or complex image syntax is not yet mapped')
        def replace(m):
            url = m[3]
            if bool(m[2]) != bool(m[4]):
                raise Unsupported('Ambiguous image destination')
            parsed = urllib.parse.urlsplit(url)
            if not parsed.scheme and not url.startswith('/'):
                raise Unsupported('Relative image URL needs the original document base URL')
            if not parsed.scheme or parsed.netloc == urllib.parse.urlsplit(source_url).netloc:
                absolute = urllib.parse.urljoin(source_url.rstrip('/')+'/', url)
                if absolute not in replacements:
                    raise Unsupported('Missing public image original or unresolved image URL: '+url)
                used.add(absolute)
                return m[0][:m.start(3)-m.start()]+replacements[absolute]+m[0][m.end(3)-m.start():]
            return m[0]
        return image.sub(replace, part)
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*?)(?:\r?\n)?$', line)
        if fenced:
            output.append(line)
            if marker and marker[1][0] == fenced[0] and len(marker[1]) >= fenced[1] and not marker[2].strip():
                fenced = None
            continue
        if marker:
            fenced = (marker[1][0], len(marker[1])); output.append(line); continue
        # Keep inline code spans byte-identical. Unclosed spans are not guessed.
        cursor, parts = 0, []
        for span in re.finditer(r'(`+)(.*?)(?<!`)\1(?!`)', line):
            parts.append(prose(line[cursor:span.start()])); parts.append(span[0]); cursor = span.end()
        tail = line[cursor:]
        if '`' in tail:
            raise Unsupported('Unclosed or multiline inline code needs review')
        parts.append(prose(tail)); output.append(''.join(parts))
    if fenced:
        raise Unsupported('Unclosed fenced code needs review')
    return ''.join(output).encode('utf-8'), used


class Fields(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True); self.values = {}; self.feed(markup)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'input' and a.get('name'):
            self.values[a['name']] = a.get('value', '')


class SameSiteRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin):
        self.origin = origin
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        p = urllib.parse.urlsplit(newurl)
        if (p.scheme, p.netloc) != self.origin:
            raise Unsupported('Cross-origin redirect refused')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NormalMarkdownClient:
    def __init__(self, url, username, password, isolated=False):
        if not isolated:
            raise Unsupported('This development entry requires an isolated destination')
        self.url = url.rstrip('/')
        p = urllib.parse.urlsplit(self.url)
        if p.scheme not in ('http', 'https') or p.username or p.password or p.query or p.fragment:
            raise Unsupported('Invalid destination URL')
        self.origin = (p.scheme, p.netloc)
        self.op = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), SameSiteRedirect(self.origin))
        self.request('/wp-login.php')
        self.request('/wp-login.php', {'log': username, 'pwd': password, 'wp-submit': 'Log In', 'testcookie': '1', 'redirect_to': self.url+'/wp-admin/'})
        self.nonce = self.request('/wp-admin/admin-ajax.php?action=rest-nonce')[0].decode().strip()
        self.me = self.rest('users/me?context=edit')

    def request(self, path, data=None, headers=None):
        url = path if path.startswith(('http://', 'https://')) else self.url+path
        p = urllib.parse.urlsplit(url)
        if (p.scheme, p.netloc) != self.origin:
            raise Unsupported('Cross-origin request refused')
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode('utf-8')
        with self.op.open(urllib.request.Request(url, data=data, headers=headers or {}), timeout=30) as r:
            return r.read(), r.headers

    def rest(self, path, data=None):
        route = '/wp/v2/'+path
        separator = '&' if '?' in path else ''
        route = route.replace('?', '&', 1) if separator else route
        body, _ = self.request('/?rest_route='+urllib.parse.quote(route, safe='/&='), None if data is None else json.dumps(data).encode(), {'X-WP-Nonce': self.nonce, 'Content-Type': 'application/json'})
        return json.loads(body)

    def import_document(self, raw, filename):
        if not re.fullmatch(r'[^/\\\r\n"\x00]+\.(?:md|markdown)', filename, re.I):
            raise Unsupported('An explicit safe .md/.markdown import filename is required')
        markup = self.request('/wp-admin/edit.php?post_type=ozmd_document&page=ozmd-import')[0].decode()
        nonce = Fields(markup).values['_wpnonce']
        boundary = '----OwrNormalImport'+hashlib.sha256(raw).hexdigest()
        body = ('--'+boundary+'\r\nContent-Disposition: form-data; name="action"\r\n\r\nozmd_import_document\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="_wpnonce"\r\n\r\n'+nonce+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="ozmd_file"; filename="'+filename+'"\r\nContent-Type: text/markdown\r\n\r\n').encode()+raw+('\r\n--'+boundary+'--\r\n').encode()
        markup = self.request('/wp-admin/admin-post.php', body, {'Content-Type': 'multipart/form-data; boundary='+boundary})[0].decode()
        notices = re.findall(r'<div class="notice notice-success[^>]*>(.*?)</div>', markup, re.S)
        links = [html.unescape(link) for notice in notices for link in re.findall(r'href="([^"]+)"', notice) if 'post.php?' in link]
        if len(links) != 1:
            raise Unsupported('Normal import did not identify exactly one new draft; do not retry blindly')
        return int(urllib.parse.parse_qs(urllib.parse.urlsplit(links[0]).query)['post'][0])

    def export(self, doc_id):
        markup = self.request('/wp-admin/post.php?post='+str(doc_id)+'&action=edit')[0].decode()
        links = [html.unescape(u) for u in re.findall(r'href="([^"]+)"', markup) if 'action=ozmd_export_document' in u]
        if len(links) != 1:
            raise Unsupported('Normal export link unavailable')
        return self.request(links[0])

    def save(self, doc_id, raw, item):
        markup = self.request('/wp-admin/post.php?post='+str(doc_id)+'&action=edit')[0].decode()
        fields = Fields(markup).values
        date = datetime.datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S')
        self.request('/wp-admin/post.php', {'action': 'editpost', 'post_ID': doc_id, 'post_type': 'ozmd_document', '_wpnonce': fields['_wpnonce'], 'ozmd_source_nonce': fields['ozmd_source_nonce'], 'ozmd_source': raw.decode(), 'post_title': item['title'], 'post_name': item['slug'], 'post_status': item['status'], 'post_password': item['password'], 'post_author_override': item['author_destination'], 'edit_date': 'true', 'aa': date.year, 'mm': date.month, 'jj': date.day, 'hh': date.hour, 'mn': date.minute, 'ss': date.second, 'original_post_status': fields.get('original_post_status', 'draft'), 'user_ID': str(self.me['id'])})
        exported, headers = self.export(doc_id)
        if exported != raw:
            raise Unsupported('Normal save/export differs; no internal repair attempted')
        saved_fields = Fields(self.request('/wp-admin/post.php?post='+str(doc_id)+'&action=edit')[0].decode()).values
        if saved_fields.get('post_title') != item['title'] or saved_fields.get('original_post_status') != item['status']:
            raise Unsupported('Normal editor title/publication state differs; no repair attempted')
        return headers.get('Content-Disposition', '')

    def rebuild(self, plan, journal_path, author_map):
        if plan['schema'] != 'owr-normal-markdown-registration-1' or plan['source_url'].rstrip('/') == self.url:
            raise Unsupported('Wrong plan or source destination collision')
        site = json.loads(self.request('/?rest_route=/')[0])
        if (site.get('timezone_string', '') != plan['timezone']['name'] or
                float(site.get('gmt_offset', 0)) != float(plan['timezone']['offset'])):
            raise Unsupported('Prepare the same site timezone before restoring publication dates')
        journal = Path(journal_path)
        state = {'state': 'planning', 'through': plan['through'], 'plan_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(), 'documents': {}, 'images': {}, 'pages': {}, 'held': dict(plan['held']) if plan['held'] else {}, 'excluded': plan['excluded']}
        with journal.open('x', encoding='utf-8') as f:
            json.dump(state, f)
        def record():
            journal.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        try:
            originals = {url: image for image in plan['images'] for url in image['urls']}
            eligible, required = [], set()
            for item in plan['documents']:
                try:
                    item = dict(item)
                    item['author_destination'] = author_map.get(str(item['author_origin']))
                    if not item['author_destination']:
                        raise Unsupported('Explicit destination author mapping required')
                    raw = base64.b64decode(item['source_base64'], validate=True)
                    if hashlib.sha256(raw).hexdigest() != item['source_sha256']:
                        raise Unsupported('Source digest mismatch')
                    _, used = image_references(raw, plan['source_url'], {u: u for u in originals})
                    eligible.append(item); required.update(used)
                except (Unsupported, UnicodeError) as e:
                    state['held'][str(item['origin_id'])] = str(e)
            state['state'] = 'registering'; record(); replacements = {}
            for image in plan['images']:
                if not required.intersection(image['urls']):
                    continue
                raw = base64.b64decode(image['body_base64'], validate=True)
                if hashlib.sha256(raw).hexdigest() != image['sha256']:
                    raise Unsupported('Image digest mismatch')
                if not re.fullmatch(r'[A-Za-z0-9_.-]+', image['filename']):
                    raise Unsupported('Media filename needs explicit confirmation')
                response = json.loads(self.request('/?rest_route=/wp/v2/media', raw, {'X-WP-Nonce': self.nonce, 'Content-Type': image['mime'], 'Content-Disposition': 'attachment; filename="'+image['filename']+'"'})[0])
                new = response['id']; state['images'][str(image['origin_id'])] = new; record()
                self.rest('media/'+str(new), {'title': image['title'], 'alt_text': image['alt']})
                replacements.update({url: response['source_url'] for url in image['urls']})
            for item in eligible:
                raw = base64.b64decode(item['source_base64']); applied, _ = image_references(raw, plan['source_url'], replacements)
                new = self.import_document(applied, item['filename']); state['documents'][str(item['origin_id'])] = new; record()
                # Export the imported draft before publishing. Source and application copies stay distinct.
                if self.export(new)[0] != applied:
                    raise Unsupported('Normal import/export differs')
                self.save(new, applied, item)
            pattern = re.compile(r'\[ozeki_markdown_document\s+id=["\']?([1-9][0-9]*)["\']?\s*/?\]')
            for page in plan['pages']:
                if not author_map.get(str(page['author_origin'])):
                    state['held'][str(page['origin_id'])] = 'Explicit destination author mapping required'; record(); continue
                refs = pattern.findall(page['content'])
                if any(ref not in state['documents'] for ref in refs):
                    state['held'][str(page['origin_id'])] = 'Referenced document was not registered'; record(); continue
                body = pattern.sub(lambda m: '[ozeki_markdown_document id="'+str(state['documents'][m[1]])+'"]', page['content'])
                if plan['source_url'] in body:
                    state['held'][str(page['origin_id'])] = 'Page has additional source-site links requiring the core registration map'; record(); continue
                endpoint = 'pages' if page['type'] == 'page' else 'posts'
                response = self.rest(endpoint, {'title': page['title'], 'slug': page['slug'], 'content': body, 'status': page['status'], 'password': page['password'], 'excerpt': page['excerpt'], 'date': page['date'].replace(' ', 'T'), 'date_gmt': page['date_gmt'].replace(' ', 'T'), 'author': author_map[str(page['author_origin'])], 'comment_status': page['comment_status'], 'ping_status': page['ping_status']})
                state['pages'][str(page['origin_id'])] = response['id']; record()
                actual = self.rest(endpoint+'/'+str(response['id'])+'?context=edit')
                if actual['content']['raw'] != body:
                    raise Unsupported('Normal page save differs')
            state['state'] = 'completed'; state['image_urls'] = replacements; record(); return state
        except Exception as e:
            state['state'] = 'failed'; state['error'] = str(e); record(); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True); parser.add_argument('--url', required=True)
    parser.add_argument('--username', required=True); parser.add_argument('--journal', required=True)
    parser.add_argument('--author-map', required=True, help='JSON file: source user IDs to prepared destination user IDs')
    parser.add_argument('--isolated', action='store_true')
    args = parser.parse_args()
    client = NormalMarkdownClient(args.url, args.username, getpass.getpass('WordPress password: '), args.isolated)
    result = client.rebuild(json.loads(Path(args.plan).read_text(encoding='utf-8-sig')), args.journal, json.loads(Path(args.author_map).read_text(encoding='utf-8-sig')))
    print(json.dumps(result, ensure_ascii=False, indent=2))
