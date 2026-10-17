#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parent.parent
cmd=['docker','compose','--env-file',str(root/'.local/runtime.env'),'-f',str(root/'lab/m1/compose.yml')]
def output(args): return subprocess.check_output(args,timeout=25).decode()
config=json.loads(output(cmd+['--profile','recovery','config','--format','json']))
checks=[]
def check(ok,name): checks.append({'name':name,'passed':bool(ok)})
source=config['services']['source']; recovery=config['services']['recovery']
check(source['environment']['WORDPRESS_DB_PASSWORD']!=recovery['environment']['WORDPRESS_DB_PASSWORD'],'separate_db_credentials')
source_volumes={v['source'] for v in source['volumes'] if v['type']=='volume'}
recovery_volumes={v['source'] for v in recovery['volumes'] if v['type']=='volume'}
check(not source_volumes & recovery_volumes,'separate_site_private_volumes')
check(set(source['networks']).isdisjoint(recovery['networks']),'separate_networks')
for service in ['source','source-db']:
    container_id=output(cmd+['ps','-q',service]).strip()
    info=json.loads(output(['docker','inspect',container_id]))[0]
    check(info['State']['Status']=='running','running_'+service)
    check(info['State'].get('Health',{}).get('Status')=='healthy','healthy_'+service)
    check(info['Image']==config['services'][service]['image'],'pinned_image_'+service)
    for name in info['NetworkSettings']['Networks']:
        network=json.loads(output(['docker','network','inspect',name]))[0]
        check(network['Internal'],'internal_network_'+service)
    if service=='source':
        check(not info['HostConfig']['PortBindings'],'source_has_no_published_ports')
        plugin=[m for m in info['Mounts'] if m['Destination'].endswith('/plugins/ozeki-database-backup-for-s3')]
        check(len(plugin)==1 and not plugin[0]['RW'],'readonly_plugin_dependency')
    else:
        check(not info['HostConfig']['PortBindings'],'db_has_no_published_ports')
proxy_id=output(cmd+['ps','-q','preview']).strip()
proxy=json.loads(output(['docker','inspect',proxy_id]))[0]
bindings=proxy['NetworkSettings']['Ports'].get('80/tcp') or []
check(bool(bindings) and all(b['HostIp']=='127.0.0.1' and b['HostPort']=='18081' for b in bindings),'active_loopback_only_http')
check(proxy['Image']==config['services']['preview']['image'],'pinned_proxy_image')
check(proxy['State'].get('Health',{}).get('Status')=='healthy','healthy_preview')
check(not output(cmd+['--profile','recovery','ps','-q','recovery','recovery-db']).strip(),'recovery_not_started')
report={'kind':'phase1_isolation','checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'passed':all(c['passed'] for c in checks)}
(root/'evidence/m1/phase1/isolation-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'checks':len(checks),'passed':report['passed'],'failed':[c['name'] for c in checks if not c['passed']]}))
raise SystemExit(0 if report['passed'] else 1)
