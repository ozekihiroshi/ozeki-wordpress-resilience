#!/usr/bin/env python3
"""Loopback-only SMTP sink; writes test mail locally and never relays mail."""
import argparse
import json
from pathlib import Path
import socketserver
import uuid


class Handler(socketserver.StreamRequestHandler):
    def reply(self, data):
        self.wfile.write(data + b'\r\n')
        self.wfile.flush()

    def handle(self):
        self.connection.settimeout(10)
        self.reply(b'220 owr-test SMTP sink')
        while True:
            line = self.rfile.readline(8193)
            if not line or len(line) > 8192:
                return
            command = line.split(b' ', 1)[0].strip().upper()
            if command in (b'EHLO', b'HELO'):
                self.reply(b'250 owr-test')
            elif command in (b'MAIL', b'RCPT', b'RSET', b'NOOP'):
                self.reply(b'250 OK')
            elif command == b'DATA':
                self.reply(b'354 End with dot')
                body = bytearray()
                while True:
                    line = self.rfile.readline(8193)
                    if not line:
                        return
                    if line == b'.\r\n':
                        break
                    body.extend(line[1:] if line.startswith(b'..') else line)
                    if len(body) > 131072 or len(line) > 8192:
                        return
                if self.server.reject_file and self.server.reject_file.exists():
                    self.reply(b'451 Test delivery temporarily unavailable')
                    continue
                name = self.server.directory / (uuid.uuid4().hex + '.eml')
                import os
                with name.open('xb') as out:
                    out.write(body)
                    out.flush()
                    os.fsync(out.fileno())
                self.reply(b'250 Stored in local test inbox')
            elif command == b'QUIT':
                self.reply(b'221 Bye')
                return
            else:
                self.reply(b'502 Unsupported')


def receiver(directory, reject_file=None, port=0):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    server = socketserver.TCPServer(('127.0.0.1', port), Handler)
    server.directory, server.reject_file = directory, reject_file
    return server


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--ready-file', type=Path, required=True)
    p.add_argument('--reject-file', type=Path)
    p.add_argument('--port', type=int, default=0)
    a = p.parse_args()
    if not 0 <= a.port <= 65535: p.error('port out of range')
    with receiver(a.directory, a.reject_file, a.port) as server:
        a.ready_file.write_text(json.dumps({'host':'127.0.0.1','port':server.server_address[1]}))
        server.serve_forever()


if __name__ == '__main__':
    main()
