"""Lab-only shared-lock executor. Every allowed job's entire process group is bounded."""
import fcntl,json,os,re,signal,socketserver,subprocess,time
from pathlib import Path
SOCKET='/run/owr-dispatch/service.sock'

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(30)
        try:
            job=json.loads(self.rfile.readline(4096))
            if set(job)!={'kind','id'} or job['kind'] not in ['write','deploy','slow'] or not re.fullmatch('[a-zA-Z0-9_-]{1,48}',job['id']):
                raise ValueError('invalid job')
            result=self.execute(job)
        except (ValueError,TypeError,KeyError):result={'state':'command_denied'}
        self.wfile.write(json.dumps(result).encode()+b'\n')

    def execute(self,job):
        if Path('/tmp/owr-gate.fence').exists():return {'state':'fenced'}
        with open('/tmp/owr-gate.lock','rb') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError:return {'state':'fenced'}
            if Path('/tmp/owr-gate.fence').exists():return {'state':'fenced'}
            with open('/tmp/owr-route-generation','r+') as counter:
                fcntl.flock(counter,fcntl.LOCK_EX)
                n=int(counter.read());counter.seek(0);counter.truncate();counter.write(str(n+1));counter.flush()
            process=subprocess.Popen(['/usr/local/bin/php','-d','auto_prepend_file=','/lab/external-job.php',job['id'],job['kind']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            try:
                out,err=process.communicate(timeout=15)
                if process.returncode:return {'state':'failed'}
                return json.loads(out)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.communicate()
                return {'state':'failed'}

class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads=False

if __name__=='__main__':
    if os.path.exists(SOCKET):raise SystemExit('Refusing stale socket')
    with Server(SOCKET,Handler) as server:
        os.chmod(SOCKET,0o660)
        server.serve_forever()
