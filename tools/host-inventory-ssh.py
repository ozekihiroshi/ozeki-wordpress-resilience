"""Pinned, fixed-command SSH host inventory; stdout-only preflight result."""
import argparse, importlib.util, json, os, re, secrets, signal, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True

def load(name):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

t=load('notification-transfer')
original=t.command

def command(c):
    args=original(c)
    args[args.index('HostKeyAlias=owr-notification-'+c['site_id'])]='HostKeyAlias=owr-inventory-'+c['site_id']
    args[-1]='host-inventory'
    return args

t.command=command

def endpoint(c, packet):
    if not isinstance(packet,dict) or set(packet)!={'site_id','config_sha256','nonce'}:
        raise ValueError('request')
    if packet['site_id']!=c['site_id'] or packet['config_sha256']!=c['config_sha256'] or not isinstance(packet['nonce'],str) or not re.fullmatch('[a-f0-9]{32}',packet['nonce']):
        raise ValueError('binding')
    env={'PATH':'/usr/bin:/bin','LANG':'C','OWR_INV_SITE':c['site_id'],'OWR_INV_CONFIG_SHA256':c['config_sha256'],'OWR_INV_NONCE':packet['nonce']}
    for k in ('DB_HOST','DB_NAME','DB_PREFIX','DB_USER','DB_PASSWORD','ROOT'):
        if not isinstance(c['probe'][k],str):raise ValueError('config')
        env['OWR_INV_'+k]=c['probe'][k]
    p=subprocess.run([c['php'],'-d','auto_prepend_file=','-d','auto_append_file=',str(Path(__file__).with_name('host-inventory.php'))],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=15)
    report=t.decode(p.stdout,65536)
    if p.returncode not in (0,2):raise ValueError('probe')
    return report

def inspect(c,profile,inventory,workspace,transport=None):
    pre=load('deployment-preflight');checker=load('host-inventory-check')
    result=pre.assess(profile,inventory,workspace)
    nonce=secrets.token_hex(16)
    packet=dict(site_id=profile['site_id'],config_sha256=pre.capture.digest(profile),nonce=nonce)
    try:
        if c['site_id']!=profile['site_id']:raise ValueError('site')
        report=(transport or t.ssh)(c,packet)
    except (OSError,ValueError,RuntimeError,TimeoutError,subprocess.SubprocessError,KeyError):
        result['state']='unsupported' if result['state']=='unsupported' else 'needs_configuration'
        result['host_observation']={'state':'unavailable'}
        result['issues'].append(dict(code='host_ssh_unavailable_or_invalid',category='unclassified',action='接続・ホスト鍵・権限・応答を確認してください。原因未確定のため環境障害と断定しません。'))
        return result
    result=checker.integrate(result,profile,report,nonce)
    result['transport']={'kind':'ssh_pinned_fixed_command','host_identity_checked':True,'remote_attestation':False}
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['endpoint','inspect']);p.add_argument('--admin-report',action='store_true');p.add_argument('--config',required=True)
    for name in ('profile','inventory','workspace'):p.add_argument('--'+name)
    a=p.parse_args()
    try:
        c=t.read_file(a.config,16384)
        if a.action=='endpoint':
            signal.alarm(18)
            if os.environ.get('SSH_ORIGINAL_COMMAND')!='host-inventory':raise ValueError('command')
            result=endpoint(c,t.decode(sys.stdin.buffer.read(1025),1024));code=0
        else:
            pre=load('deployment-preflight')
            result=inspect(c,pre.read_json(a.profile),pre.read_json(a.inventory),a.workspace)
            code=0 if result['state']=='eligible_for_dedicated_trial' else 2
            if a.admin_report:
                from datetime import datetime,timezone
                profile=pre.read_json(a.profile)
                result=dict(format='owr-preflight-admin-v1',site_id=profile['site_id'],config_sha256=pre.capture.digest(profile),attempted_at=datetime.now(timezone.utc).isoformat(),result=result)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False));return code
    except Exception:
        print('{"format":"owr-host-ssh-error-v1","status":"failed"}');return 2
if __name__=='__main__':raise SystemExit(main())
