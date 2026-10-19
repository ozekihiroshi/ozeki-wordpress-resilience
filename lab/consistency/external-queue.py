"""Isolated single-consumer queue; control endpoints are lab-only and unauthenticated."""
import argparse,json,re,sqlite3,time,urllib.request
from http.server import BaseHTTPRequestHandler,HTTPServer
from external_client import request
DB='/queue/jobs.sqlite'
class Broker(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,obj,status=200):
        data=json.dumps(obj).encode();self.send_response(status);self.end_headers();self.wfile.write(data)
    def do_GET(self):
        with sqlite3.connect(DB) as db:
            frozen=db.execute('SELECT checkpoint FROM control').fetchone()[0]
            if self.path=='/control':return self.respond({'checkpoint':frozen})
            if self.path=='/jobs':
                rows=[] if frozen else db.execute("SELECT id,kind FROM jobs WHERE state='pending' ORDER BY rowid").fetchall()
                return self.respond([{'id':r[0],'kind':r[1]} for r in rows])
            if self.path=='/status':return self.respond([dict(zip(['id','kind','state'],r)) for r in db.execute('SELECT id,kind,state FROM jobs ORDER BY rowid')])
        self.respond({'error':'unknown'},404)
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=4096:raise ValueError()
            data=json.loads(self.rfile.read(size))
            with sqlite3.connect(DB) as db:
                token=db.execute('SELECT checkpoint FROM control').fetchone()[0]
                if self.path in ['/freeze','/resume']:
                    wanted=data.get('checkpoint','')
                    if not re.fullmatch(r'[a-f0-9]{32}',wanted):raise ValueError()
                    if (self.path=='/freeze' and token) or (self.path=='/resume' and token!=wanted):return self.respond({'error':'checkpoint_conflict'},409)
                    db.execute('UPDATE control SET checkpoint=?',(wanted if self.path=='/freeze' else '',))
                else:
                    if token:return self.respond({'error':'frozen'},409)
                    ident=data.get('id','')
                    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,48}',ident):raise ValueError()
                    if self.path=='/enqueue':
                        kind=data.get('kind')
                        if kind not in ['write','deploy','slow']:raise ValueError()
                        old=db.execute('SELECT kind FROM jobs WHERE id=?',(ident,)).fetchone()
                        if old and old[0]!=kind:return self.respond({'error':'identity_conflict'},409)
                        db.execute('INSERT OR IGNORE INTO jobs(id,kind) VALUES(?,?)',(ident,kind))
                    elif self.path in ['/ack','/quarantine']:db.execute("UPDATE jobs SET state=? WHERE id=? AND state='pending'",('done' if self.path=='/ack' else 'quarantined',ident))
                    else:return self.respond({'error':'unknown'},404)
            self.respond({'ok':True})
        except (ValueError,TypeError,AttributeError):self.respond({'error':'invalid'},400)
def api(path,data=None):
    payload=None if data is None else json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765'+path,data=payload,headers={'Content-Type':'application/json'}),timeout=30) as response:return json.load(response)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['broker','worker']);args=parser.parse_args()
    if args.mode=='broker':
        with sqlite3.connect(DB) as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'pending')")
            db.execute('CREATE TABLE IF NOT EXISTS control(id INTEGER PRIMARY KEY CHECK(id=1),checkpoint TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO control VALUES(1,'')")
        HTTPServer(('127.0.0.1',8765),Broker).serve_forever()
    else:
        while True:
            try:
                jobs=api('/jobs')
                if jobs:
                    result=request(jobs[0])
                    if result['state']=='done':api('/ack',{'id':jobs[0]['id']})
                    elif result['state']!='fenced':api('/quarantine',{'id':jobs[0]['id']})
            except (OSError,ValueError):pass
            time.sleep(.1)
