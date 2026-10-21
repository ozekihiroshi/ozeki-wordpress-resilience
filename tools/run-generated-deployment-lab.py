#!/usr/bin/env python3
"""Deploy generated drafts to disposable hosts, using existing production entry points."""
import ipaddress
import argparse,hashlib,importlib.util,json,os,secrets,shlex,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ui=load('run-preflight-observer-relay-lab');run=ui.run

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
 prefix='owr-plan-install-'+secrets.token_hex(5);net=prefix+'-net';hosts={r:prefix+'-'+r for r in ('inventory','scanner','wordpress','observer')};db=prefix+'-db';created=[];checks=[];events=[]
 def record(label):checks.append(label);print('PASS '+label,flush=True)
 def ex(role,*args,check=True,input=None):return run('docker','exec',*(['-i'] if input is not None else []),hosts.get(role,role),*args,check=check,input=input)
 def put(role,path,value,owner='root:root',mode='640'):
  temp=a.output/'upload';temp.write_text(value if isinstance(value,str) else json.dumps(value));temp.chmod(0o600);run('docker','cp',str(temp),hosts.get(role,role)+':'+path);ex(role,'sh','-c',shlex.join(['chown',owner,path])+' && '+shlex.join(['chmod',mode,path]));temp.unlink()
 def read(role,path):return ex(role,'cat',path).stdout
 def doc(role,path):return json.loads(read(role,path))
 def invoke(role,argv,user,check=True):return ex(role,'runuser','-u',user,'--',*argv,check=check)
 def wait(fn,label):
  until=time.monotonic()+65
  while time.monotonic()<until:
   try:
    if fn():record(label);return
   except (RuntimeError,ValueError,KeyError):pass
   time.sleep(2)
  raise AssertionError(label)
 site='generated-first-site';cfg='/etc/owr/'+site;private='/var/lib/owr-preflight/'+site;public='/var/lib/owr-preflight-web/'+site;op='/var/lib/owr-observer-relay/'+site;webpath='/var/lib/owr-status-web/'+site
 status=a.output/'status';status.mkdir(mode=0o755);preweb=status/'preflight';preweb.mkdir(mode=0o755);obsweb=status/'observer';obsweb.mkdir(mode=0o755)
 imageenv=dict(x.split('=',1) for x in (ROOT/'lab/m1/images.env').read_text().splitlines() if '=' in x)
 try:
  ids=run('docker','network','ls','-q').stdout.decode().split()
  used=[ipaddress.ip_network(c['Subnet']) for n in json.loads(run('docker','network','inspect',*ids).stdout) for c in (n['IPAM'].get('Config') or []) if c.get('Subnet')]
  for route in json.loads(run('ip','-j','route').stdout):
   if route.get('dst') and route['dst']!='default':used.append(ipaddress.ip_network(route['dst'],strict=False))
  subnet=next(ipaddress.ip_network('10.253.'+str(i)+'.0/28') for i in range(256) if not any(ipaddress.ip_network('10.253.'+str(i)+'.0/28').overlaps(n) for n in used))
  run('docker','network','create','--internal','--subnet',str(subnet),net)
  secret=secrets.token_hex(24);env=a.output/'db-env';env.write_text('MARIADB_ROOT_PASSWORD='+secret+'\nMARIADB_DATABASE=lab\n');env.chmod(0o600)
  run('docker','run','-d','--name',db,'--network',net,'--memory','512m','--env-file',str(env),imageenv['OWR_DB_IMAGE']);created.append(db)
  wait(lambda:run('docker','exec',db,'healthcheck.sh','--connect','--innodb_initialized',check=False).returncode==0,'dedicated MariaDB ready')
  def sql(v):return run('docker','exec','-i',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb -uroot lab',input=v.encode())
  sql("CREATE TABLE wp_options(option_name varchar(64),option_value text) ENGINE=InnoDB; CREATE TABLE wp_posts(ID bigint) ENGINE=InnoDB; CREATE TABLE wp_postmeta(post_id bigint) ENGINE=InnoDB; INSERT INTO wp_options VALUES('upload_path',''),('upload_url_path',''); CREATE USER 'inspector'@'%' IDENTIFIED BY '"+secret+"'; GRANT SELECT ON lab.* TO 'inspector'@'%';")
  fixture=a.output/'site';(fixture/'wp-content/uploads').mkdir(parents=True);(fixture/'wp-content/uploads/generated.txt').write_text('generated install test');(fixture/'wp-config.php').write_text('<?php throw new Exception("DO_NOT_EXECUTE");')
  for role,host in hosts.items():
   mounts=['-v',str(ROOT)+':/opt/owr:ro']
   if role=='inventory':mounts+=['-v',str(fixture)+':/var/www/html:ro']
   if role=='wordpress':mounts+=['-v',str(preweb)+':'+public,'-v',str(obsweb)+':'+webpath]
   run('docker','run','-d','--name',host,'--network',net,'--memory','384m',*mounts,'--entrypoint','sleep','owr-external-lab:local','infinity');created.append(host)
   for user in ('owr-preflight','owr-observer','owr-relay','ingress'):
    ex(role,'useradd','-m','-g','33','-s','/bin/sh',user)
   ex(role,'usermod','-p','*','ingress');ex(role,'mkdir','-p',cfg,'/run/sshd');ex(role,'chmod','750',cfg);ex(role,'chgrp','33',cfg)
  profile=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());top=dict(format='owr-deployment-topology-v1',site_id=site,hosts={r:dict(host=h,port=2222,user='ingress') for r,h in hosts.items()})
  for n,v in [('profile',profile),('topology',top)]: (a.output/(n+'.json')).write_text(json.dumps(v))
  tool=['python3','-B',str(ROOT/'tools/external-deployment-plan.py')];inputs=['--profile',str(a.output/'profile.json'),'--topology',str(a.output/'topology.json')]
  plan=json.loads(run(*tool,'plan',*inputs).stdout);bundle=a.output/'bundle';run(*tool,'generate',*inputs,'--output',str(bundle))
  assert not plan['production_ready'];record('actual plan and generate CLI used; readiness remains false')
  # Reviewed plan directories and configuration paths are applied only inside named disposable hosts.
  for d in plan['directories']:
   ex(d['role'],'sh','-c',shlex.join(['mkdir','-p',d['path']])+' && '+shlex.join(['chown',d['owner']+':33',d['path']])+' && '+shlex.join(['chmod',d['mode'],d['path']]))
   if d['path']==cfg:ex(d['role'],'chgrp','33',cfg)
  mutations=[]
  for entry in plan['files']:
   if entry['target']=='manual_merge_into_wp_config':continue
   value=json.loads((bundle/entry['file']).read_text())
   if entry['file']=='inventory/endpoint.draft.json':
    value['php']='/usr/local/bin/php';value['probe'].update(DB_HOST=db,DB_USER='inspector',DB_PASSWORD=secret);mutations.append('inventory endpoint: local PHP binary, generated SELECT credentials and database host')
   # group33 is a deliberate dedicated-lab mapping, not a production ACL recommendation.
   put(entry['role'],entry['target'],value,mode=entry['mode']);ex(entry['role'],'chgrp','33',entry['target'])
  pre=load('deployment-preflight');inventory={k:profile[k] for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')};inventory.update(format='owr-deployment-inventory-v1',config_sha256=pre.capture.digest(profile),observed_at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),incomplete_runs=0,uncertain_puts=0)
  # Fixture declarations come from this controlled lab setup; host facts are measured separately over SSH.
  put('scanner',cfg+'/profile.json',profile);put('scanner',cfg+'/inventory.json',inventory);ex('scanner','chgrp','33',cfg+'/profile.json',cfg+'/inventory.json')
  keydir=a.output/'keys';keydir.mkdir(mode=0o700)
  for role in hosts:
   key=keydir/(role+'-host');run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key));put(role,cfg+'/hostkey',key.read_text(),mode='600')
  auth={r:[] for r in hosts}
  for idx,pin in enumerate(plan['host_key_pins']):
   key=keydir/('client-'+str(idx));run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(key))
   local,remote=pin['role'],pin['remote_role'];owner='owr-observer' if local=='observer' else ('owr-relay' if 'observer-relay' in pin['identity_file'] else 'owr-preflight')
   put(local,pin['identity_file'],key.read_text(),owner+':33','600');put(local,pin['known_hosts'],pin['alias']+' '+(keydir/(remote+'-host.pub')).read_text(),owner+':33','600')
   endpoints=[e for e in plan['ssh_endpoints'] if e['role']==remote]
   if remote=='observer':side='source' if 'source-report' in pin['identity_file'] else 'receiver';endpoint=next(e for e in endpoints if side+'-endpoint' in ' '.join(e['argv']))
   else:endpoint=next(e for e in endpoints if e['requested_command']==('watchdog-probe' if local=='observer' else ('host-inventory' if remote=='inventory' else 'preflight-status')))
   auth[remote].append('restrict,command="'+shlex.join(endpoint['argv'])+'" '+key.with_suffix('.pub').read_text().strip())
  for role in hosts:
   put(role,cfg+'/authorized_keys','\n'.join(auth[role])+'\n',mode='644');put(role,cfg+'/sshd','\n'.join(['Port 2222','HostKey '+cfg+'/hostkey','PidFile /run/sshd/pid','AuthorizedKeysFile '+cfg+'/authorized_keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','AllowUsers ingress','DisableForwarding yes','PermitTTY no'])+'\n',mode='644');ex(role,'/usr/sbin/sshd','-f',cfg+'/sshd')
  record('six separate SSH keys pinned from local host-key origins; forced commands installed')
  commands=plan['commands']
  def command(role,needle):return next(c['argv'] for c in commands if c['role']==role and needle in ' '.join(c['argv']))
  pub=command('scanner','preflight-relay.py');recv=command('wordpress','preflight-transfer.py')
  def one(role,argv,user):return invoke(role,argv[:-1]+['0'] if '--interval' in argv else argv,user,False)
  def dump():return run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --skip-comments --skip-dump-date lab').stdout
  before=dump();filebefore={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()}
  result=one('scanner',pub,'owr-preflight');assert result.returncode==0,result.stdout.decode()+result.stderr.decode()
  assert one('wordpress',recv,'owr-preflight').returncode==0
  assert before==dump() and filebefore=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()}
  assert doc('wordpress',public+'/report.json')['result']['host_observation']['state']=='validated_report';record('generated publisher and receiver perform real SSH inventory; DB and files unchanged')
  run('docker','exec','-d','-u','owr-observer',hosts['observer'],'python3','-B','/opt/owr/tools/smtp-test-receiver.py','--directory',op+'/mail','--ready-file',op+'/smtp-ready.json')
  wait(lambda:ex('observer','test','-f',op+'/smtp-ready.json',check=False).returncode==0,'dedicated local SMTP receiver ready')
  smtp=doc('observer',op+'/smtp-ready.json')
  for side in ('source','receiver'):
   path=cfg+'/'+side+'-observer.json';value=doc('observer',path);value['alerts']=dict(source_outbox=op+'/'+side+'-alerts.sqlite',state=op+'/'+side+'-delivery',channels=[dict(id='local-mail',provider=dict(transport='smtp_test',host=smtp['host'],port=smtp['port'],**{'from':'watchdog@example.invalid','to':'operator@example.invalid'}))]);put('observer',path,value);ex('observer','chgrp','33',path)
  mutations.append('observer alerts completed with existing smtp_test dispatcher and dedicated loopback receiver; no external delivery')
  def observers():
   for side in ('source','receiver'):
    q=invoke('observer',command('observer',side+'-observer'),'owr-observer',False);assert q.returncode==0,q.stdout.decode()+q.stderr.decode()
    assert one('wordpress',command('wordpress',side+'-pull'),'owr-relay').returncode==0
  observers();record('generated observer and both status pulls work over actual SSH')
  for path in (public+'/report.json',webpath+'/source.json'):
   assert ex('wordpress','runuser','-u','www-data','--','test','-r',path,check=False).returncode==0
   assert ex('wordpress','runuser','-u','www-data','--','test','-w',path,check=False).returncode!=0
  for pin in plan['host_key_pins']:
   assert ex(pin['role'],'runuser','-u','www-data','--','test','-r',pin['identity_file'],check=False).returncode!=0
  record('WordPress reads reports but cannot write them or read SSH keys')
  # Real periodic publisher/receiver, using reviewed generated argv; shortened interval only in lab.
  for role,argv in [('scanner',pub),('wordpress',recv)]:
   argv=argv[:-1]+['2'];run('docker','exec','-d','-u','owr-preflight',hosts[role],'sh','-c','exec '+shlex.join(argv)+' > '+private+'/periodic.log 2>&1')
  first=doc('wordpress',public+'/report.json')['attempted_at'];wait(lambda:doc('wordpress',public+'/report.json')['attempted_at']!=first,'actual periodic publication advances')
  assert one('scanner',pub,'owr-preflight').returncode!=0;record('duplicate generated publisher rejected')
  fragment=''.join(line for line in (bundle/'wordpress/wp-config.fragment.php').read_text().splitlines() if line and not line.startswith(('<?php','//')))
  # Reuse real WordPress and browser fixture. Generated bindings and paths used unchanged.
  with ui.ui_session(status,dict(php=fragment,mounts=[str(preweb)+':'+public+':ro',str(obsweb)+':'+webpath+':ro'])) as (wp,browser):
   def screen(mode):
    q=run('docker','exec',browser,'python3','/lab/preflight-relay-browser.py',mode,timeout=120,check=False)
    (a.output/(mode+'-browser.stdout')).write_bytes(q.stdout);(a.output/(mode+'-browser.stderr')).write_bytes(q.stderr)
    if q.returncode:raise RuntimeError('browser '+mode+' failed: '+q.stderr.decode()[-2500:])
    events.append(json.loads(q.stdout));(a.output/'browser-events.json').write_text(json.dumps(events,indent=2));run('docker','cp',browser+':/tmp/preflight-'+mode+'.png',str(a.output/(mode+'.png')))

   diagnostics=run('docker','exec',wp,'php','-r',"require '/var/www/html/wp-load.php'; echo json_encode(['report_defined'=>defined('OWR_PREFLIGHT_REPORT'),'report_readable'=>defined('OWR_PREFLIGHT_REPORT') && is_readable(OWR_PREFLIGHT_REPORT),'health_readable'=>defined('OWR_PREFLIGHT_TRANSFER_FILE') && is_readable(OWR_PREFLIGHT_TRANSFER_FILE)]);");(a.output/'wordpress-bindings.json').write_bytes(diagnostics.stdout)
   screen('ok');record('actual WordPress preflight screen uses generated bindings; permissions and read-only checks pass')
   ex('inventory','pkill','-x','sshd');wait(lambda:doc('wordpress',public+'/health.json')['state']=='acquisition_failed','inventory SSH outage displayed as acquisition failure');screen('acquisition_failed')
   ex('inventory','/usr/sbin/sshd','-f',cfg+'/sshd');wait(lambda:doc('wordpress',public+'/health.json')['state']=='ok','inventory SSH restart recovers');screen('recovered')
   observers()
   q=run('docker','exec',browser,'python3','/lab/preflight-observer-relay-browser.py','generated',json.dumps({s:dict(report='current',transfer='ok') for s in ('source','receiver')}),timeout=120);events.append(json.loads(q.stdout));run('docker','cp',browser+':/tmp/relay-generated.png',str(a.output/'watchdog.png'));record('actual watchdog screen uses generated monitor IDs and paths')
  (a.output/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,browser=events,reviewed_adjustments=mutations+['dedicated lab group33 mapping for read-only reports/config traversal','periodic interval60 to2seconds only in lab','generated fixture inventory declarations; measured SSH facts remain independently checked'],scope='disposable internal Docker network; real SELECT-only MariaDB, pinned SSH, existing workers and WordPress browser; no systemd/OS reboot/S3/signing/72h mutation; observer CLI uses local SMTP test receiver, no external notification',environment_incidents=[],product_defects=[]),indent=2))
 except Exception as e:
  (a.output/'failure.json').write_text(json.dumps(dict(error_type=type(e).__name__,detail=str(e)),indent=2));raise
 finally:
  if hosts['wordpress'] in created:ex('wordpress','chown','-R',str(os.getuid())+':'+str(os.getgid()),public,webpath,check=False)
  for name in reversed(created):run('docker','rm','-f','-v',name,check=False)
  run('docker','network','rm',net,check=False)
 print('ALL_PASS',flush=True)
if __name__=='__main__':main()
