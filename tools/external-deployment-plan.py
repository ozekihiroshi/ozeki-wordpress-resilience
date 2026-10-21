#!/usr/bin/env python3
"""Offline configuration bundle and read-only deployment plan; never applies changes."""
import argparse, hashlib, importlib.util, json, os, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('deployment-preflight.py'))
pre = importlib.util.module_from_spec(spec); spec.loader.exec_module(pre)
ROLES = ('inventory', 'scanner', 'wordpress', 'observer')

def encode(v):
    return (json.dumps(v, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def compile_plan(profile, topology):
    pre.capture.validate(profile)
    site = profile['site_id']
    if not re.fullmatch('[a-z][a-z0-9-]{0,31}', site): raise ValueError('site id length')
    if set(topology) != {'format','site_id','hosts'} or topology['format'] != 'owr-deployment-topology-v1' or topology['site_id'] != site: raise ValueError('topology binding')
    hosts = topology['hosts']
    if set(hosts) != set(ROLES): raise ValueError('roles')
    for c in hosts.values():
        if set(c) != {'host','port','user'}: raise ValueError('connection fields')
        if any(not isinstance(c[k],str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,252}',c[k]) for k in ('host','user')): raise ValueError('connection value')
        if type(c['port']) is not int or not 1 <= c['port'] <= 65535: raise ValueError('port')
    # Logical host labels must separate these responsibilities; this is not attestation.
    if len({hosts[k]['host'].lower() for k in ('scanner','wordpress','observer')}) != 3: raise ValueError('separate host labels required')
    if hosts['observer']['host'].lower() == hosts['inventory']['host'].lower(): raise ValueError('observer must be separate')
    digest=pre.capture.digest(profile); cfg='/etc/owr/'+site
    private='/var/lib/owr-preflight/'+site; public='/var/lib/owr-preflight-web/'+site
    op='/var/lib/owr-observer-relay/'+site; web='/var/lib/owr-status-web/'+site
    files={}; entries=[]; commands=[]; pins=[]
    def add(role,name,value,target,owner='root',group='owr-preflight',mode='0640',template=False):
        rel=role+'/'+name; raw=value.encode() if isinstance(value,str) else encode(value)
        files[rel]=raw;entries.append(dict(file=rel,role=role,target=target,owner=owner,group=group,mode=mode,template_only=template,sha256=sha(raw)))
    def connection(role,remote,keyroot,key,alias):
        c=dict(site_id=site,**hosts[remote],identity_file=keyroot+'/'+key+'.key',known_hosts=keyroot+'/'+key+'.known_hosts')
        pins.append(dict(role=role,remote_role=remote,alias=alias,known_hosts=c['known_hosts'],identity_file=c['identity_file'],verification='operator_must_verify_out_of_band'))
        return c
    # Credentials are intentionally absent. This draft cannot run before local completion.
    endpoint=dict(site_id=site,config_sha256=digest,php='/usr/bin/php',probe=dict(DB_HOST='127.0.0.1',DB_NAME=profile['database']['name'],DB_PREFIX=profile['database']['prefix'],DB_USER=None,DB_PASSWORD=None,ROOT=profile['files']['root']))
    add('inventory','endpoint.draft.json',endpoint,cfg+'/endpoint.json',group=hosts['inventory']['user'],template=True)
    inv=connection('scanner','inventory',private,'inventory','owr-inventory-'+site)
    add('scanner','inventory-ssh.json',inv,cfg+'/inventory-ssh.json')
    publisher=dict(site_id=site,config_sha256=digest,profile_file=cfg+'/profile.json',inventory_file=cfg+'/inventory.json',connection_file=cfg+'/inventory-ssh.json',workspace=private+'/work',lock_file=private+'/publisher.lock',report_file=public+'/report.json',health_file=public+'/health.json')
    add('scanner','publisher.json',publisher,cfg+'/publisher.json')
    binding=dict(site_id=site,config_sha256=digest,report_file=public+'/report.json',health_file=public+'/health.json')
    add('scanner','report-endpoint.json',binding,cfg+'/report-endpoint.json',group=hosts['scanner']['user'])
    receiver=connection('wordpress','scanner',private,'report','owr-preflight-'+site)
    receiver.update(binding,lock_file=private+'/receiver.lock')
    add('wordpress','receiver.json',receiver,cfg+'/receiver.json')
    wp={}
    for short,role in [('source','scanner'),('receiver','wordpress')]:
        monitor='pf-'+short+'-'+site
        add(role,'watchdog-probe.json',dict(binding,monitor_id=monitor),cfg+'/watchdog-probe.json',group=hosts[role]['user'])
        ssh=connection('observer',role,op,short+'-probe','owr-notification-'+monitor);ssh['site_id']=monitor
        observer=dict(monitor_id=monitor,state=op+'/'+short+'-state',stale_after_seconds=300,admin_site_id=site,public_status_file=web+'/'+short+'.json',ssh=ssh)
        add('observer',short+'-observer.json',observer,cfg+'/'+short+'-observer.json',group='owr-observer',template=True)
        add('observer',short+'-endpoint.json',dict(site_id=site,public_status_file=web+'/'+short+'.json'),cfg+'/'+short+'-endpoint.json',group=hosts['observer']['user'])
        pull=connection('wordpress','observer',op,short+'-report','owr-notification-'+site)
        pull.update(monitor_id=monitor,status_file=web+'/'+short+'.json',transfer_health=web+'/'+short+'-transfer.json',lock_file=op+'/'+short+'-pull.lock',loop_lock=op+'/'+short+'-loop.lock')
        add('wordpress',short+'-pull.json',pull,cfg+'/'+short+'-pull.json',group='owr-relay')
        wp[short]=dict(path=pull['status_file'],monitor_id=monitor,transfer_file=pull['transfer_health'])
        commands.append(dict(role='observer',kind='manual_one_shot_after_prerequisites',argv=['/usr/bin/python3','-B','/opt/owr/tools/watchdog-observer.py','observe','--config',cfg+'/'+short+'-observer.json']))
        commands.append(dict(role='wordpress',kind='periodic_after_prerequisites',argv=['/usr/bin/python3','-B','/opt/owr/tools/observer-status-relay.py','--config',cfg+'/'+short+'-pull.json','--interval','60']))
    # PHP syntax built from restricted paths and IDs, not arbitrary operator text.
    def php(v):
        if isinstance(v,dict):return '['+','.join(php(k)+'=>'+php(x) for k,x in v.items())+']'
        return "'"+v.replace('\\','\\\\').replace("'","\\'")+"'"
    constants=dict(OWR_PREFLIGHT_SITE_ID=site,OWR_PREFLIGHT_CONFIG_SHA256=digest,OWR_PREFLIGHT_REPORT=public+'/report.json',OWR_PREFLIGHT_TRANSFER_FILE=public+'/health.json',OWR_PREFLIGHT_WATCHDOG_REPORTS=wp)
    snippet='<?php\n// Review existing definitions before manually merging into wp-config.php.\n'+''.join('define('+php(k)+','+php(v)+');\n' for k,v in constants.items())
    add('wordpress','wp-config.fragment.php',snippet,'manual_merge_into_wp_config',group='www-data',template=True)
    for role,tool,name in [('scanner','preflight-relay.py','publisher'),('wordpress','preflight-transfer.py','receiver')]:
        commands.append(dict(role=role,kind='periodic_after_prerequisites',argv=['/usr/bin/python3','-B','/opt/owr/tools/'+tool]+(['pull'] if role=='wordpress' else [])+['--config',cfg+'/'+name+'.json','--interval','60']))
    dirs=[]
    for role in ROLES:
        dirs.append(dict(role=role,path=cfg,owner='root',mode='0750',note='Grant only designated service/SSH users traversal and required config reads; inspect ACLs.'))
    for role in ('scanner','wordpress'):
        dirs += [dict(role=role,path=private,owner='owr-preflight',mode='0700'),dict(role=role,path=public,owner='owr-preflight',group='www-data' if role=='wordpress' else hosts[role]['user'],mode='2750')]
    dirs += [dict(role='scanner',path=private+'/work',owner='owr-preflight',mode='0700')]
    for role,user in [('observer','owr-observer'),('wordpress','owr-relay')]:
        dirs += [dict(role=role,path=op,owner=user,mode='0700'),dict(role=role,path=web,owner=user,group=hosts[role]['user'] if role=='observer' else 'www-data',mode='2750')]
    manual=[('configuration','profile_and_independent_inventory','Place reviewed profile and independently collected inventory on scanner; do not clone profile as evidence.'),('configuration','db_select_credentials','Complete inventory endpoint locally; SELECT-only DB user; never put secrets in topology or generated bundle.'),('configuration','host_keys_and_ssh_restrictions','Verify host keys out of band; install separate keys with fixed commands, no shell/forwarding; no keys generated.'),('configuration','notifications_not_configured','Observer drafts omit alerts; no external alert delivery is configured. Complete existing notification configuration before operation.'),('environment','runtime_accounts_acl_services','Check Python/PHP/mysqli/MariaDB, users, groups, ACLs and root-owned code. No host is contacted or service installed.'),('operational','existing_state_and_paths','Review existing files/ledgers/locks; never overwrite them. Generated paths are proposals, not an inventory.'),('operational','service_mapping','Map argv/config paths/users to existing hardened units and a scheduled observer; no unit is enabled by this tool.'),('scope','capture_signing_recovery_not_deployed','Capture, S3, signing, recovery and retention cleanup remain separate operator workflows; this bundle does not configure or start them.')]
    endpoints=[dict(role='inventory',requested_command='host-inventory',argv=['/usr/bin/python3','-B','/opt/owr/tools/host-inventory-ssh.py','endpoint','--config',cfg+'/endpoint.json']),dict(role='scanner',requested_command='preflight-status',argv=['/usr/bin/python3','-B','/opt/owr/tools/preflight-transfer.py','serve','--config',cfg+'/report-endpoint.json'])]
    for role in ('scanner','wordpress'):
        endpoints.append(dict(role=role,requested_command='watchdog-probe',argv=['/usr/bin/python3','-B','/opt/owr/tools/preflight-watchdog-probe.py','--config',cfg+'/watchdog-probe.json']))
    for side in ('source','receiver'):
        endpoints.append(dict(role='observer',requested_command='observer-status',argv=['/usr/bin/python3','-B','/opt/owr/tools/observer-status.py','endpoint','--config',cfg+'/'+side+'-endpoint.json']))
    plan=dict(format='owr-external-deployment-plan-v1',site_id=site,config_sha256=digest,topology_sha256=sha(encode(topology)),production_ready=False,apply_supported=False,state='requires_operator_configuration',scope='preflight_inventory_watchdog_reporting',hosts=hosts,ssh_endpoints=endpoints,files=entries,directories=dirs,host_key_pins=pins,commands=commands,required_actions=[dict(category=c,code=k,detail=v) for c,k,v in manual])
    return plan,files

def generate(plan,files,output):
    output=Path(output)
    if not output.is_absolute():raise ValueError('absolute output required')
    if output.exists() or output.is_symlink():raise ValueError('new output directory required')
    parent=output.parent
    if not parent.is_dir() or any(p.is_symlink() for p in [parent,*parent.parents]):raise ValueError('parent must be existing non-symlink directory')
    output.mkdir(mode=0o700) # Exclusive ownership; no replacement or cleanup of existing content.
    for rel,raw in files.items():
        target=output/rel;target.parent.mkdir(mode=0o700,exist_ok=True)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as f:f.write(raw)
    # Written last: absence marks interrupted/incomplete generation, which is never auto-resumed.
    with (output/'plan.json').open('xb') as f:f.write(encode(plan))
    os.chmod(output/'plan.json',0o600)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['plan','generate']);p.add_argument('--profile',required=True);p.add_argument('--topology',required=True);p.add_argument('--output');a=p.parse_args()
    try:
        if (a.action=='plan' and a.output) or (a.action=='generate' and not a.output):raise ValueError('output only for generation')
        plan,files=compile_plan(pre.read_json(a.profile),pre.read_json(a.topology))
        if a.action=='generate':generate(plan,files,a.output)
        print(encode(plan).decode(),end='');return 0
    except Exception:
        print('{"format":"owr-external-deployment-plan-error-v1","state":"rejected","production_ready":false}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
