"""Review-bound cleanup of token-labelled recovery containers. No filesystem deletion."""
import json
import re
import subprocess


class Docker:
    def command(self,*args):
        p=subprocess.run(['docker',*args],capture_output=True,timeout=60)
        if p.returncode:raise RuntimeError('Docker inspection/cleanup failed')
        return p.stdout
    def inventory(self):
        ids=self.command('ps','-aq').decode().split()
        return json.loads(self.command('inspect',*ids)) if ids else []
    def remove(self,ident):
        self.command('rm','-f','-v',ident)
    def volume_exists(self,name):
        return name in self.command('volume','ls','-q').decode().split()


def plan(worker,request_id,api,docker):
    row=worker.row(request_id)
    api.gate.check(row is not None,'unknown request')
    root=worker.root/'recovery-attempts'/request_id
    manifest=json.loads((root/'ownership.json').read_bytes())
    token=manifest['token'];names=manifest['containers']
    api.gate.check(re.fullmatch('[a-f0-9]{32}',token) is not None and len(names)==2
                   and len(set(names))==2 and all(re.fullmatch('owr-daily-restore-[a-f0-9]{12}-(db|web)',n) for n in names),
                   'invalid ownership manifest')
    inventory=docker.inventory();selected=[]
    for obj in inventory:
        name=obj['Name'].lstrip('/')
        if name in names or obj['Config'].get('Labels',{}).get('owr.recovery-token')==token:
            api.gate.check(name in names and obj['Config'].get('Labels',{}).get('owr.recovery-token')==token
                           and obj['Config']['Labels'].get('owr.daily-restore')=='generated','ownership mismatch')
            api.gate.check(not obj['HostConfig']['Binds'] and not obj['HostConfig']['PortBindings']
                           and not obj['HostConfig'].get('Privileged',False),'unexpected resource privileges')
            mounts=obj.get('Mounts',[])
            api.gate.check(all(m['Type']=='volume' and re.fullmatch('[a-f0-9]{64}',m['Name']) for m in mounts),
                           'only anonymous recovery volumes supported')
            selected.append(dict(id=obj['Id'],name=name,volumes=[m['Name'] for m in mounts],
                                 network=obj['HostConfig']['NetworkMode']))
    ids={o['id'] for o in selected}
    volumes={v for o in selected for v in o['volumes']}
    for obj in inventory:
        if obj['Id'] not in ids:
            api.gate.check(not any(m.get('Name') in volumes for m in obj.get('Mounts',[])),
                           'volume shared with another container')
    for obj in selected:
        api.gate.check(obj['network']=='none' or obj['network'].removeprefix('container:') in ids,
                       'network outside recovery resources')
    files={}
    for name in ('result.json','isolation.json','ownership.json'):
        p=root/name
        files[name]=api.gate.sha(p.read_bytes()) if p.exists() else None
    previous=root/'cleanup-progress.json'
    remaining=[]
    if previous.exists():
        progress=json.loads(previous.read_bytes())
        api.gate.check(progress['token']==token,'cleanup token mismatch')
        remaining=[v for v in progress['volumes'] if docker.volume_exists(v)]
        api.gate.check(set(remaining)<=volumes,'orphan volume requires manual inspection')
    return dict(request_id=request_id,token=token,resources=sorted(selected,key=lambda o:o['name']),
                evidence_hashes=files,row_state=row['state'],outcome=row['outcome'],
                registration=row['registration'],report_hash=row['report_hash'])


def review(worker,request_id,api,docker=None):
    with worker.lock():
        value=plan(worker,request_id,api,docker or Docker())
        return dict(plan=value,plan_sha256=api.gate.sha(api.gate.encode(value)))


def clean(worker,request_id,expected_hash,api,docker=None):
    docker=docker or Docker()
    with worker.lock():
        value=plan(worker,request_id,api,docker)
        api.gate.check(api.gate.sha(api.gate.encode(value))==expected_hash,'review changed; inspect again')
        row=worker.row(request_id)
        # Completed recoveries awaiting delivery must be delivered, not abandoned.
        root=worker.root/'recovery-attempts'/request_id
        report=json.loads((root/'result.json').read_bytes()) if (root/'result.json').exists() else {}
        final_report=(report.get('passed') is True or
                      report.get('passed') is False and 'error_type' in report)
        api.gate.check(not (report.get('passed') is True or row['registration']=='pending'
                           or final_report and row['registration']!='recorded'),
                       'final result requires registration before cleanup release')
        progress=dict(token=value['token'],volumes=[v for o in value['resources'] for v in o['volumes']],
                      reviewed_plan_sha256=expected_hash,removed=[])
        api.io.write_json(root/'cleanup-progress.json',progress)
        # Remove WP (namespace dependent) before DB; re-check immutable identities before each removal.
        for obj in sorted(value['resources'],key=lambda o:o['name'].endswith('-web'),reverse=True):
            current=plan(worker,request_id,api,docker)
            match=[x for x in current['resources'] if x['id']==obj['id']]
            api.gate.check(match==[obj],'resource changed during cleanup')
            docker.remove(obj['id'])
            progress['removed'].append(obj['id'])
            api.io.write_json(root/'cleanup-progress.json',progress)
        api.gate.check(not plan(worker,request_id,api,docker)['resources'],'resources remain')
        api.gate.check(not any(docker.volume_exists(v) for v in progress['volumes']),'volumes remain')
        receipt=dict(request_id=request_id,state='reviewed_closed',outcome=row['outcome'],
                     reviewed_plan_sha256=expected_hash,cleanup_at=api.gate.now().isoformat(),
                     resources_removed=True,original_result_preserved=True)
        api.io.write_json(root/'cleanup-review.json',receipt)
        worker.update(request_id,state='reviewed_closed')
        return receipt
