"""OpenSSH ForceCommand client: no shell evaluation or caller-supplied paths."""
import json,os,re,socket,sys

def request(job):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(25);s.connect('/run/owr-dispatch/service.sock')
        s.sendall(json.dumps(job).encode()+b'\n')
        return json.loads(s.makefile('rb').readline(4096))

if __name__=='__main__':
    command=os.environ.get('SSH_ORIGINAL_COMMAND','')
    match=re.fullmatch(r'(write|deploy|slow) ([a-zA-Z0-9_-]{1,48})',command)
    if not match:
        print(json.dumps({'state':'command_denied'}));sys.exit(2)
    result=request({'kind':match[1],'id':match[2]})
    print(json.dumps(result));sys.exit(0 if result['state']=='done' else 3)
