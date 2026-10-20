"""Bounded external spool: drain producer output even while control probes run."""
import os,select,subprocess,tempfile,threading,time

def stream(command,deadline,limit,directory,rejected):
    with tempfile.TemporaryFile(dir=directory) as spool,tempfile.TemporaryFile(dir=directory) as stderr:
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=stderr)
        condition=threading.Condition();stop=threading.Event()
        state={'written':0,'done':False,'error':None}
        def drain():
            try:
                while not stop.is_set():
                    left=deadline-time.monotonic()
                    if left<=0:raise rejected('capture_window_lost')
                    if not select.select([p.stdout],[],[],min(left,.1))[0]:continue
                    chunk=os.read(p.stdout.fileno(),65536)
                    if not chunk:break
                    offset=state['written']
                    if offset+len(chunk)>limit:raise rejected('capture_size_limit')
                    written=0
                    while written<len(chunk):
                        n=os.pwrite(spool.fileno(),chunk[written:],offset+written)
                        if n<=0:raise OSError('spool write failed')
                        written+=n
                    with condition:state['written']+=written;condition.notify_all()
                if not stop.is_set() and p.wait(timeout=max(.01,deadline-time.monotonic()))!=0:raise rejected('stream_process_failed')
            except Exception as e:
                with condition:state['error']=e
                if p.poll() is None:p.kill()
            finally:
                with condition:state['done']=True;condition.notify_all()
        worker=threading.Thread(target=drain,daemon=True);worker.start();offset=0
        try:
            while True:
                with condition:
                    if state['error'] is not None:raise state['error']
                    available=state['written']-offset
                    if not available:
                        if state['done']:break
                        condition.wait(.1);continue
                if time.monotonic()>=deadline:raise rejected('capture_window_lost')
                chunk=os.pread(spool.fileno(),min(65536,available),offset)
                if not chunk:raise OSError('spool read failed')
                offset+=len(chunk)
                yield chunk
        finally:
            stop.set()
            if p.poll() is None:p.kill()
            p.wait(timeout=5);worker.join(timeout=5)
            p.stdout.close()
            if worker.is_alive():raise RuntimeError('producer drain stop unconfirmed')
