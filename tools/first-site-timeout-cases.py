"""Diagnostic-only instrumentation; no deadline changes or external requests."""
import importlib.util,json,time,traceback,hashlib,os,functools,threading,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
 output.parent.mkdir(parents=True,exist_ok=True);log=output.with_suffix('.events.jsonl')
 def emit(event,**data):
  env={}
  for name in ['cpu','memory','io']:
   path=Path('/proc/pressure')/name
   if path.exists():env[name]=path.read_text().strip()
  with log.open('a') as f:f.write(json.dumps({'event':event,'wall':time.time(),'mono':time.monotonic(),'load':os.getloadavg(),'pressure':env,**data})+'\n')
 def wrap(name,fn):
  @functools.wraps(fn)
  def call(*args,**kwargs):
   start=time.monotonic();emit('start',operation=name)
   done=threading.Event()
   def watch():
    if done.wait(3):return
    try:
     p=subprocess.run(['docker','top',web,'-eo','pid,ppid,stat,wchan:32,comm'],capture_output=True,text=True,timeout=5)
     emit('slow_process_snapshot',operation=name,exit=p.returncode,processes=p.stdout)
    except subprocess.TimeoutExpired:emit('slow_process_snapshot',operation=name,error='docker_top_timeout')
   watcher=threading.Thread(target=watch,daemon=True) if name=='php' else None
   if watcher:watcher.start()
   try:return fn(*args,**kwargs)
   except Exception as e:
    emit('error',operation=name,error=type(e).__name__,timeout=getattr(e,'timeout',None),frames=[{'file':Path(x.filename).name,'line':x.lineno,'function':x.name} for x in traceback.extract_tb(e.__traceback__)])
    raise
   finally:
    done.set()
    if watcher:watcher.join(timeout=6)
    emit('end',operation=name,seconds=time.monotonic()-start)
  return call
 original=load('diag_original','first-site-lab-cases.py');loader=original.load
 def instrument(name,file):
  module=loader(name,file)
  if file=='first-site-docker-lab.py':
   parent=module.DockerBackend
   class Measured(parent):
    def __init__(self,*args,**kwargs):
     super().__init__(*args,**kwargs)
     for method in ['preflight','fence','held','release','inventory','schema','references']:
      setattr(self,method,wrap(method,getattr(self,method)))
    def stream(self,asset,deadline):
     start=time.monotonic();emit('start',operation='stream.'+asset,remaining=deadline-start)
     size=0
     try:
      for b in super().stream(asset,deadline):size+=len(b);yield b
     except Exception as e:
      emit('error',operation='stream.'+asset,error=type(e).__name__,timeout=getattr(e,'timeout',None),frames=[{'file':Path(x.filename).name,'line':x.lineno,'function':x.name} for x in traceback.extract_tb(e.__traceback__)])
      raise
     finally:emit('end',operation='stream.'+asset,seconds=time.monotonic()-start,bytes=size)
   module.DockerBackend=Measured
  return module
 original.load=instrument
 callbacks=[wrap('php',php),wrap('sql',sql),wrap('hold',hold),wrap('ready',ready),wrap('release_callback',release),wrap('run',run)]
 emit('begin',mode=os.environ['OWR_TIMEOUT_MODE'])
 try:
  if os.environ['OWR_TIMEOUT_MODE']=='sequence':original.exercise(db,web,*callbacks,check,results,output)
  else:
   # Identical source/setup, but missing attachment is first capture, then repeated.
   source=(ROOT/'tools/first-site-lab-cases.py').read_text()
   source=source[:source.index('    b=backend();original_fence=b.fence')]+'''    run('docker','exec',web,'rm','/var/www/html/wp-content/uploads/one.png')
    for index in range(int(os.environ.get('OWR_TIMEOUT_REPEATS','3'))):
        _,v=a.capture(c,a.digest(c),backend(),root)
        results.append({'case':'missing_attachment_single_'+str(index+1),'state':v['state'],'reason':v.get('reason'),'release_confirmed':v['release_confirmed']})
        check(v['state']=='inconsistent' and v.get('reason')=='attachment_reference_missing' and v['release_confirmed'],'missing attachment expected result not reached')
'''
   ns={'__file__':str(ROOT/'tools/first-site-lab-cases.py')};exec(compile(source,'single-missing-diagnostic','exec'),ns);ns['load']=instrument
   ns['exercise'](db,web,*callbacks,check,results,output)
 finally:emit('complete',results=results)
