#!/usr/bin/env python3
"""Explicit initial provisioning and read-only status export for the WP admin pilot."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3

ROOT=Path(__file__).resolve().parent
def load(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
dispatch=load('notification-dispatch-lab')
def digest(config):return hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):raise ValueError('invalid identifier')
    return value

def compile_settings(settings,profiles,source,state,include_existing=False,migration=False):
    if settings.get('format')!='owr-notification-settings-v1':raise ValueError('invalid settings format')
    if type(settings.get('revision')) is not int or settings['revision']<1:raise ValueError('invalid revision')
    for key in ('site_id','revision_token'):identifier(settings[key])
    if (Path(state)/'dispatch.sqlite').exists() and not migration:raise ValueError('existing state requires explicit migration')
    if Path(source).exists() and not include_existing:
        with sqlite3.connect(Path(source).resolve().as_uri()+'?mode=ro',uri=True) as original:
            if original.execute('SELECT count(*) FROM outbox').fetchone()[0]:
                raise ValueError('existing events require explicit replay authorization')
    channels=[];seen=set()
    if not isinstance(settings['channels'],list) or len(settings['channels'])>20:raise ValueError('invalid channels')
    for item in settings['channels']:
        name=identifier(item['id'])
        if name in seen:raise ValueError('duplicate channel')
        seen.add(name)
        if type(item['enabled']) is not bool:raise ValueError('invalid enabled flag')
        if not item['enabled']:continue
        profile=profiles[identifier(item['profile'])].copy()
        if item['provider'] not in ('pushover','smtp_tls','smtp_starttls') or profile['transport']!=item['provider']:
            raise ValueError('profile transport mismatch')
        if item['provider']=='pushover':
            for key in ('retry','expire'):
                if type(item[key]) is not int:raise ValueError('invalid interval')
            if not 30<=item['retry']<=item['expire']<=10800:raise ValueError('invalid interval')
            profile.update(retry=item['retry'],expire=item['expire'])
        else:
            target=item['recipient']
            if not isinstance(target,str) or len(target)>254 or not re.fullmatch(r'[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]+',target):raise ValueError('invalid mailbox')
            profile['to']=target
        channels.append(dict(id=name,kinds=item['kinds'],provider=profile))
    config=dict(source_outbox=str(Path(source).resolve()),state=str(Path(state).resolve()),channels=channels)
    if channels:dispatch.validate_config(config)
    elif not migration:raise ValueError('no enabled channels')
    binding={key:settings[key] for key in ('site_id','revision','revision_token')}
    binding.update(format='owr-notification-admin-binding-v1',config_hash=digest(config))
    return config,binding

def status(config,binding,simulated=False):
    import fcntl
    with (Path(config['state'])/'dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        return status_locked(config,binding,simulated)

def status_locked(config,binding,simulated=False):
    if binding.get('format')!='owr-notification-admin-binding-v1' or binding.get('config_hash')!=digest(config):
        raise ValueError('configuration binding mismatch')
    directory=Path(config['state'])
    health=json.loads((directory/'delivery-health.json').read_text())
    if health['format']!='owr-delivery-health-v1':raise ValueError('invalid health report')
    with sqlite3.connect((directory/'dispatch.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        saved=db.execute('SELECT binding FROM settings').fetchone()
        if not saved or digest(json.loads(saved[0]))!=binding['config_hash']:raise ValueError('dispatcher binding mismatch')
        rows=db.execute('SELECT channel,status,count(*) FROM deliveries GROUP BY channel,status').fetchall()
        receipts=db.execute('SELECT channel,receipt_state,count(*) FROM deliveries WHERE receipt_state IS NOT NULL GROUP BY channel,receipt_state').fetchall()
    if config.get('managed') and health.get('config_hash')!=digest(config):raise ValueError('new revision has not completed a dispatch cycle')
    channels=[]
    items={item.get('logical_id',item['id']):item for item in config['channels']}
    for logical,item in items.items():
        routes={c['id'] for c in config['channels'] if c.get('logical_id',c['id'])==logical}
        def totals(values):
            result={}
            for channel,state,count in values:
                if channel in routes:result[state]=result.get(state,0)+count
            return result
        channels.append(dict(id=logical,counts=totals(rows),receipts=totals(receipts),
            problems=sorted({p['kind'] for p in health['problems'] if p['channel'] in routes})))
    test_results=[]
    with sqlite3.connect(directory/'dispatch.sqlite') as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='test_requests'").fetchone():
            test_results=[dict(request_id=r[0],channel_id=r[1],status=r[2],revision_token=r[3]) for r in db.execute('SELECT id,channel,status,revision_token FROM test_requests ORDER BY created DESC LIMIT 20')]
    return dict(tests=test_results,format='owr-notification-admin-status-v1',**{k:binding[k] for k in ('site_id','revision','revision_token')},
                completed_at=health['completed_at'],simulated=simulated,channels=channels)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    c=sub.add_parser('compile');c.add_argument('--settings',type=Path,required=True);c.add_argument('--profiles',type=Path,required=True)
    c.add_argument('--source-outbox',required=True);c.add_argument('--state',required=True);c.add_argument('--output',type=Path,required=True)
    c.add_argument('--migration',action='store_true',help='Compile a candidate for explicit live apply; does not alter state')
    c.add_argument('--include-existing',action='store_true',help='Explicitly include existing source events; may send historical alerts')
    s=sub.add_parser('status');s.add_argument('--compiled',type=Path,required=True);s.add_argument('--output',type=Path,required=True);s.add_argument('--simulated',action='store_true')
    args=p.parse_args()
    try:
        if args.action=='compile':
            config,binding=compile_settings(json.loads(args.settings.read_text()),json.loads(args.profiles.read_text()),args.source_outbox,args.state,args.include_existing,args.migration)
            args.output.mkdir(mode=0o700)
            for name,data in [('config.json',config),('binding.json',binding)]:dispatch.health.atomic_json(args.output/name,data)
            print('Initial configuration compiled; no notifications sent.')
        else:
            result=status(json.loads((args.compiled/'config.json').read_text()),json.loads((args.compiled/'binding.json').read_text()),args.simulated)
            dispatch.health.atomic_json(args.output,result);print('Sanitized status exported.')
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__}));return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
