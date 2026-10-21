#!/usr/bin/env python3
"""Deploy generated drafts to disposable hosts, using existing production entry points."""
import ipaddress
import argparse,hashlib,importlib.util,json,os,secrets,shlex,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ui=load('run-preflight-observer-relay-lab');run=ui.run

def main(review_mode=False):
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(mode=0o700,parents=True,exist_ok=False)
 prefix='owr-plan-systemd-'+secrets.token_hex(5);net=prefix+'-net';hosts={r:prefix+'-'+r for r in ('inventory','scanner','wordpress','observer')};db=prefix+'-db';created=[];checks=[];events=[];vms={};hostboot=Path('/proc/sys/kernel/random/boot_id').read_text()
 def record(label):checks.append(label);print('PASS '+label,flush=True)
 def ex(role,*args,check=True,input=None):
  if role in vms:
   vm,ssh=vms[role];return run('docker','exec',*(['-i'] if input is not None else []),vm,*ssh,'sudo '+shlex.join(args),check=check,input=input,timeout=100)
  return run('docker','exec',*(['-i'] if input is not None else []),hosts.get(role,role),*args,check=check,input=input)
 def bootvm(role):
  share=status if role=='wordpress' else a.output/(role+'-share');share.mkdir(exist_ok=True)
  envvm=os.environ.copy();envvm.update(OWR_VM_LAB_OUTPUT=str(a.output/('vm-'+role)),OWR_VM_OBSERVER=hosts[role],OWR_VM_REPORTS=str(share),OWR_VM_FIXED_ENDPOINT='1')
  q=subprocess.run(['python3',str(ROOT/'lab/observer-relay-vm/start.py')],env=envvm,capture_output=True,timeout=400)
  if q.returncode:raise RuntimeError('VM boot '+role+': '+q.stderr.decode()[-1500:])
  vms[role]=((a.output/('vm-'+role)/'container-name').read_text(),json.loads((a.output/('vm-'+role)/'ssh-command.json').read_text()))
  ex(role,'mkdir','-p','/opt/owr');ex(role,'tar','-xf','/tmp/payload.tar','-C','/opt/owr','--strip-components=1');ex(role,'chown','-R','root:root','/opt/owr');ex(role,'chmod','-R','go-w','/opt/owr');record(role+' dedicated Ubuntu VM booted')
 def put(role,path,value,owner='root:root',mode='640'):
  if role in vms:
   raw=value if isinstance(value,str) else json.dumps(value);code='import pathlib,sys;p=pathlib.Path('+repr(path)+');p.write_bytes(sys.stdin.buffer.read())';ex(role,'python3','-c',code,input=raw.encode());ex(role,'sh','-c',shlex.join(['chown',owner,path])+' && '+shlex.join(['chmod',mode,path]));return
  temp=a.output/'upload';temp.write_text(value if isinstance(value,str) else json.dumps(value));temp.chmod(0o600);run('docker','cp',str(temp),hosts.get(role,role)+':'+path);ex(role,'sh','-c',shlex.join(['chown',owner,path])+' && '+shlex.join(['chmod',mode,path]));temp.unlink()
 def read(role,path):return ex(role,'cat',path).stdout
 def doc(role,path):return json.loads(read(role,path))
 def invoke(role,argv,user,check=True):return ex(role,'runuser','-u',user,'--',*argv,check=check)
 def wait(fn,label):
  until=time.monotonic()+240
  while time.monotonic()<until:
   try:
    if fn():record(label);return
   except (RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired):pass
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
   if role!='inventory':bootvm(role)
   for user in ('owr-preflight','owr-observer','owr-relay','ingress'):
    ex(role,'useradd','-m','-g','33','-s','/bin/sh',user)
   ex(role,'usermod','-p','*','ingress');ex(role,'mkdir','-p',cfg,'/run/sshd');ex(role,'chmod','750',cfg);ex(role,'chgrp','33',cfg)
  profile=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text());top=dict(format='owr-deployment-topology-v1',site_id=site,hosts={r:dict(host=json.loads(run('docker','inspect',h).stdout)[0]['NetworkSettings']['Networks'][net]['IPAddress'],port=2222 if r=='inventory' else 2224,user='ingress') for r,h in hosts.items()})
  if review_mode:
   profile['storage']['destination_ref']='generated-storage';profile['trust'].update(operator='lab-operator',public_pin_ref='generated-pin')
  for n,v in [('profile',profile),('topology',top)]: (a.output/(n+'.json')).write_text(json.dumps(v))
  tool=['python3','-B',str(ROOT/'tools/external-deployment-plan.py')];inputs=['--profile',str(a.output/'profile.json'),'--topology',str(a.output/'topology.json')]
  plan=json.loads(run(*tool,'plan',*inputs).stdout);bundle=a.output/'bundle';run(*tool,'generate',*inputs,'--output',str(bundle))
  assert not plan['production_ready'];record('actual plan and generate CLI used; readiness remains false')
  # Reviewed plan directories and configuration paths are applied only inside named disposable hosts.
  for d in plan['directories']:
   ex(d['role'],'sh','-c',shlex.join(['mkdir','-p',d['path']])+' && '+shlex.join(['chown',d['owner']+':33',d['path']])+' && '+shlex.join(['chmod',d['mode'],d['path']]))
   if d['path']==cfg:ex(d['role'],'chgrp','33',cfg)
  # The display VM shares its report directories via 9p; all private state stays in guest disks.
  ex('wordpress','mkdir','-p','/mnt/owr-shared')
  fstab=read('wordpress','/etc/fstab').decode()+'\nreports /mnt/owr-shared 9p trans=virtio,version=9p2000.L 0 0\n/mnt/owr-shared/preflight '+public+' none bind 0 0\n/mnt/owr-shared/observer '+webpath+' none bind 0 0\n'
  put('wordpress','/etc/fstab',fstab,mode='644');ex('wordpress','mount','-a');ex('wordpress','chown','owr-preflight:33',public);ex('wordpress','chmod','2750',public);ex('wordpress','chown','owr-relay:33',webpath);ex('wordpress','chmod','2750',webpath)
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
   put(role,cfg+'/authorized_keys','\n'.join(auth[role])+'\n',mode='644');put(role,cfg+'/sshd','\n'.join(['Port 2222','HostKey '+cfg+'/hostkey','PidFile /run/sshd/pid','AuthorizedKeysFile '+cfg+'/authorized_keys','PasswordAuthentication no','KbdInteractiveAuthentication no','UsePAM no','AllowUsers ingress','DisableForwarding yes','PermitTTY no'])+'\n',mode='644');
   if role in vms:
    put(role,'/etc/systemd/system/owr-fixed-endpoint.service','[Unit]\nAfter=network.target\n[Service]\nType=simple\nRuntimeDirectory=sshd\nRuntimeDirectoryMode=0755\nRuntimeDirectoryPreserve=yes\nExecStart=/usr/sbin/sshd -D -f '+cfg+'/sshd\nRestart=on-failure\n[Install]\nWantedBy=multi-user.target\n',mode='644');ex(role,'systemctl','daemon-reload');ex(role,'systemctl','enable','--now','owr-fixed-endpoint')
   else:ex(role,'/usr/sbin/sshd','-f',cfg+'/sshd')
  record('six separate SSH keys pinned from local host-key origins; forced commands installed')
  commands=plan['commands']
  def command(role,needle):return next(c['argv'] for c in commands if c['role']==role and needle in ' '.join(c['argv']))
  pub=command('scanner','preflight-relay.py');recv=command('wordpress','preflight-transfer.py')
  def one(role,argv,user):return invoke(role,argv[:-1]+['0'] if '--interval' in argv else argv,user,False)
  def refresh_inventory():
   inventory['observed_at']=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
   put('scanner',cfg+'/inventory.json',inventory,owner='root:33')
  if review_mode:
   pubpath=pub[pub.index('--config')+1];pc=doc('scanner',pubpath);pc['review_file']=cfg+'/operator-review.json';put('scanner',pubpath,pc,owner='root:33')
   refresh_inventory()
  def dump():return run('docker','exec',db,'sh','-c','MYSQL_PWD="$MARIADB_ROOT_PASSWORD" mariadb-dump -uroot --skip-comments --skip-dump-date lab').stdout
  before=dump();filebefore={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()}
  result=one('scanner',pub,'owr-preflight');assert result.returncode==0,result.stdout.decode()+result.stderr.decode()
  assert one('wordpress',recv,'owr-preflight').returncode==0
  assert before==dump() and filebefore=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.rglob('*') if p.is_file()}
  assert doc('wordpress',public+'/report.json')['result']['host_observation']['state']=='validated_report';record('generated publisher and receiver perform real SSH inventory; DB and files unchanged')
  if review_mode:
   # Explicit lab operator issuance; periodic publisher cannot write this root-owned file.
   code="import importlib.util,json,pathlib; s=importlib.util.spec_from_file_location('issuer','/opt/owr/tools/recurring-capture-review.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);c=json.load(open("+repr(pubpath)+"));read=lambda k:json.load(open(c[k]));p=read('profile_file');v=m.issue(p,read('inventory_file'),c['workspace'],read('report_file'),read('health_file'),{k:dict(confirmed=True,evidence_ref='generated-manual-check/'+k) for k in m.gate.SCOPES},p['operations']['owner']);print(json.dumps(v))"
   review=json.loads(invoke('scanner',['python3','-B','-c',code],'owr-preflight').stdout);put('scanner',pc['review_file'],review,owner='root:33');review_bytes=read('scanner',pc['review_file'])
   assert one('scanner',pub,'owr-preflight').returncode==0
   assert one('wordpress',recv,'owr-preflight').returncode==0
   summary=doc('wordpress',public+'/report.json')['result']['operator_review'];assert summary['state']=='valid' and summary['automatic_checks_passed'],summary
   assert ex('scanner','runuser','-u','owr-preflight','--','test','-w',pc['review_file'],check=False).returncode!=0
   record('operator review issued explicitly; valid summary transferred over SSH; worker cannot edit confirmation')
  put('observer','/etc/systemd/system/owr-lab-mail.service','[Unit]\nAfter=network.target\n[Service]\nUser=owr-observer\nGroup=www-data\nExecStart=/usr/bin/python3 -B /opt/owr/tools/smtp-test-receiver.py --directory '+op+'/mail --ready-file '+op+'/smtp-ready.json --port 1025\nRestart=on-failure\n[Install]\nWantedBy=multi-user.target\n',mode='644');ex('observer','systemctl','daemon-reload');ex('observer','systemctl','enable','--now','owr-lab-mail')
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
  units={'scanner':['owr-generated-publisher'],'wordpress':['owr-generated-receiver','owr-generated-source-pull','owr-generated-receiver-pull'],'observer':['owr-generated-source-observer.timer','owr-generated-receiver-observer.timer']}
  def install(role,name,template,argv,paths,oneshot=False):
   text=template
   text='\n'.join('ExecStart='+shlex.join(argv) if x.startswith('ExecStart=') else 'ReadWritePaths='+' '.join(paths) if x.startswith('ReadWritePaths=') else 'Group=www-data' if x.startswith('Group=') else x for x in text.splitlines())+'\n'
   text=text.replace('[Service]','RequiresMountsFor='+' '.join(paths)+'\n[Service]')
   put(role,'/etc/systemd/system/'+name+'.service',text,mode='644')
   (a.output/(name+'.service')).write_text(text)
   if oneshot:
    timer='[Unit]\nDescription=Generated observer schedule\n[Timer]\nOnBootSec=10\nOnUnitActiveSec=60\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n';put(role,'/etc/systemd/system/'+name+'.timer',timer,mode='644')
  install('scanner','owr-generated-publisher',(ROOT/'examples/preflight-relay/owr-preflight.service').read_text(),pub,[private,public])
  install('wordpress','owr-generated-receiver',(ROOT/'examples/preflight-relay/owr-preflight-transfer.service').read_text(),recv,[private,public])
  for side in ('source','receiver'):
   install('wordpress','owr-generated-'+side+'-pull',(ROOT/'examples/observer-status-relay/owr-observer-status@.service').read_text(),command('wordpress',side+'-pull'),[op,webpath])
   install('observer','owr-generated-'+side+'-observer',(ROOT/'examples/watchdog-observer/owr-watchdog-observer.service').read_text(),command('observer',side+'-observer'),[op,webpath],True)
  for role,names in units.items():ex(role,'systemctl','daemon-reload');ex(role,'systemctl','enable','--now',*names)
  first=doc('wordpress',public+'/report.json')['attempted_at'];wait(lambda:doc('wordpress',public+'/report.json')['attempted_at']!=first,'generated systemd services advance reports at60seconds')
  def healthy():return doc('wordpress',public+'/health.json')['state']=='ok' and all(doc('wordpress',webpath+'/'+side+'-transfer.json')['state']=='ok' for side in ('source','receiver'))
  wait(healthy,'all generated report routes healthy')
  assert one('scanner',pub,'owr-preflight').returncode!=0;record('duplicate generated systemd publisher rejected')
  def verify(label):
   evidence={}
   for role,names in units.items():
    for name in names:
     service=name.replace('.timer','.service') if name.endswith('.timer') else name+'.service'
     raw=ex(role,'systemctl','show',service,'--property=User,Group,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp').stdout.decode();props=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
     for key,val in dict(Group='www-data',NoNewPrivileges='yes',ProtectSystem='strict',ProtectHome='yes',PrivateTmp='yes').items():assert props[key]==val,(service,key,props)
     assert ex(role,'systemctl','is-enabled',name,check=False).returncode==0;evidence[role+'/'+name]=props
   (a.output/(label+'-units.json')).write_text(json.dumps(evidence,indent=2));record(label+' hardened units and enablement verified')
  verify('initial')
  fragment=''.join(line for line in (bundle/'wordpress/wp-config.fragment.php').read_text().splitlines() if line and not line.startswith(('<?php','//')))
  # Reuse real WordPress and browser fixture. Generated bindings and paths used unchanged.
  with ui.ui_session(status,dict(php=fragment,diagnostics=str(a.output/'browser-diagnostics'),mounts=[str(preweb)+':'+public+':ro',str(obsweb)+':'+webpath+':ro'])) as (wp,browser):
   def screen(mode):
    q=run('docker','exec',browser,'python3','/lab/preflight-relay-browser.py',mode,timeout=120,check=False)
    (a.output/(mode+'-browser.stdout')).write_bytes(q.stdout);(a.output/(mode+'-browser.stderr')).write_bytes(q.stderr)
    if q.returncode:raise RuntimeError('browser '+mode+' failed: '+q.stderr.decode()[-2500:])
    events.append(json.loads(q.stdout));(a.output/'browser-events.json').write_text(json.dumps(events,indent=2));run('docker','cp',browser+':/tmp/preflight-'+mode+'.png',str(a.output/(mode+'.png')))

   def review_screen(label,mode):
    if not review_mode:return
    q=run('docker','exec',browser,'python3','/lab/operator-review-browser.py',mode,timeout=120,check=False)
    (a.output/('review-'+label+'.log')).write_bytes(q.stdout+q.stderr)
    if q.returncode:raise RuntimeError('operator review browser failed:'+label)
    events.append(dict(label=label,operator_review=json.loads(q.stdout)))
    run('docker','cp',browser+':/tmp/operator-review-'+mode+'.png',str(a.output/('review-'+label+'.png')))
    assert read('scanner',pc['review_file'])==review_bytes,'automatic renewal or mutation'
    record('operator review '+label+' UI and immutable confirmation verified')
   diagnostics=run('docker','exec',wp,'php','-r',"require '/var/www/html/wp-load.php'; echo json_encode(['report_defined'=>defined('OWR_PREFLIGHT_REPORT'),'report_readable'=>defined('OWR_PREFLIGHT_REPORT') && is_readable(OWR_PREFLIGHT_REPORT),'health_readable'=>defined('OWR_PREFLIGHT_TRANSFER_FILE') && is_readable(OWR_PREFLIGHT_TRANSFER_FILE)]);");(a.output/'wordpress-bindings.json').write_bytes(diagnostics.stdout)
   review_screen('initial','valid')
   screen('ok');record('actual WordPress preflight screen uses generated bindings; permissions and read-only checks pass')
   # Stop every generated periodic service/timer; preserve reports and private state.
   for role,names in units.items():
    stop=names+[n.replace('.timer','.service') for n in names if n.endswith('.timer')];ex(role,'systemctl','stop',*stop)
   frozen={path:read('wordpress',path) for path in [public+'/report.json',public+'/health.json',webpath+'/source.json',webpath+'/receiver.json',webpath+'/source-transfer.json',webpath+'/receiver-transfer.json']}
   started=time.monotonic()
   while time.monotonic()-started<310:
    time.sleep(10);assert all(read('wordpress',p)==v for p,v in frozen.items());print('STOPPED_SECONDS '+str(round(time.monotonic()-started)),flush=True)
   review_screen('stopped','stale')
   screen('stopped');record('all periodic units stopped310seconds; reports byte-preserved and UI stopped')
   if review_mode:refresh_inventory() # Controlled fixture re-observation, never renewal of confirmation.
   for role,names in units.items():ex(role,'systemctl','start',*names)
   old=json.loads(frozen[public+'/report.json'])['attempted_at'];wait(lambda:healthy() and doc('wordpress',public+'/report.json')['attempted_at']!=old,'explicit restart restores generated report chain');screen('recovered')
   review_screen('recovered','valid')
   boots={role:read(role,'/proc/sys/kernel/random/boot_id').decode().strip() for role in vms}
   if review_mode:refresh_inventory()
   before_reboot=doc('wordpress',public+'/report.json')['attempted_at']
   for role in vms:ex(role,'systemctl','reboot',check=False)
   for role in vms:wait(lambda role=role:read(role,'/proc/sys/kernel/random/boot_id').decode().strip()!=boots[role],role+' actual OS reboot changes BootID')
   wait(lambda:healthy() and doc('wordpress',public+'/report.json')['attempted_at']!=before_reboot,'enabled units automatically recover after OS reboot')
   verify('reboot');screen('restarted')
   review_screen('reboot','valid')
   assert Path('/proc/sys/kernel/random/boot_id').read_text()==hostboot
   (a.output/'boot.json').write_text(json.dumps(dict(before=boots,after={r:read(r,'/proc/sys/kernel/random/boot_id').decode().strip() for r in vms},host_unchanged=True),indent=2));record('72hour observation host BootID unchanged')
   q=run('docker','exec',browser,'python3','/lab/preflight-observer-relay-browser.py','generated',json.dumps({s:dict(report='current',transfer='ok') for s in ('source','receiver')}),timeout=120);events.append(json.loads(q.stdout));run('docker','cp',browser+':/tmp/relay-generated.png',str(a.output/'watchdog.png'));record('actual watchdog screen uses generated monitor IDs and paths')
  (a.output/'result.json').write_text(json.dumps(dict(passed=True,operator_review_mode=review_mode,automatic_review_renewal=False,checks=checks,browser=events,reviewed_adjustments=mutations+['dedicated lab group33 mapping for read-only reports/config traversal','generated service interval60seconds unchanged; observer timers60seconds','generated fixture inventory declarations; measured SSH facts remain independently checked'],scope='disposable internal Docker network; real SELECT-only MariaDB, pinned SSH, existing workers and WordPress browser; three real Ubuntu VMs with systemd and OS reboot; no S3/signing/72h mutation; observer CLI uses local SMTP test receiver, no external notification',environment_incidents=[],product_defects=[]),indent=2))
 except Exception as e:
  (a.output/'failure.json').write_text(json.dumps(dict(error_type=type(e).__name__,detail=str(e)),indent=2));raise
 finally:
  if hosts['wordpress'] in created:ex('wordpress','chown','-R',str(os.getuid())+':'+str(os.getgid()),public,webpath,check=False)
  for role in ('scanner','wordpress','observer'):
   vmfile=a.output/('vm-'+role)/'container-name'
   if vmfile.exists():
    name=vmfile.read_text();assert name.startswith('owr-production-vm-') and name.replace('-','').isalnum();run('docker','rm','-f','-v',name,check=False)
  for name in reversed(created):run('docker','rm','-f','-v',name,check=False)
  run('docker','network','rm',net,check=False)
 print('ALL_PASS',flush=True)
if __name__=='__main__':main()
