from pathlib import Path
import json,subprocess,hashlib,sys
root=Path('/code');work=Path('/lab');inputs=work/'inputs';inputs.mkdir()
p=json.loads((root/'examples/first-site/generated-lab.json').read_text());top=dict(format='owr-deployment-topology-v1',site_id=p['site_id'],hosts={k:dict(host=k+'.example.invalid',port=22,user='inspector' if k=='inventory' else 'owr-status') for k in ('inventory','scanner','wordpress','observer')})
(inputs/'profile.json').write_text(json.dumps(p));(inputs/'topology.json').write_text(json.dumps(top))
def hashes():return {str(f.relative_to(work)):hashlib.sha256(f.read_bytes()).hexdigest() for f in work.rglob('*') if f.is_file()}
args=['python3','-B','/code/tools/external-deployment-plan.py'];base=['--profile',str(inputs/'profile.json'),'--topology',str(inputs/'topology.json')]
checks=[]
def run(action,extra=[],code=0):
 r=subprocess.run(args+[action]+base+extra,capture_output=True);assert r.returncode==code,(r.stdout,r.stderr);return r
before=hashes();v=json.loads(run('plan').stdout);assert hashes()==before;checks.append('plan does not write input or create output files')
assert not v['production_ready'] and not v['apply_supported'];checks.append('unverified prerequisites stay blocked')
assert len(v['host_key_pins'])==6;checks.append('six independent SSH credential references and pinned aliases')
bundle=work/'bundle';generated=json.loads(run('generate',['--output',str(bundle)]).stdout);assert v==generated;checks.append('generation matches deterministic read-only plan')
for f in v['files']:assert hashlib.sha256((bundle/f['file']).read_bytes()).hexdigest()==f['sha256']
checks.append('all generated files match manifest hashes')
before=hashes();run('generate',['--output',str(bundle)],2);assert before==hashes();checks.append('existing bundle refused without modifying files')
run('plan',['--output',str(work/'must-not-exist')],2);assert not (work/'must-not-exist').exists();checks.append('plan rejects write destination')
for n in ('scanner/publisher.json','wordpress/receiver.json','wordpress/source-pull.json','wordpress/receiver-pull.json'):assert (bundle/n).is_file()
checks.append('publisher receiver observer pulls and WordPress fragment generated')
assert (bundle/'wordpress/wp-config.fragment.php').read_text().count('define(')==5;checks.append('WordPress binding fragment complete')
(work/'result.json').write_text(json.dumps(dict(passed=True,checks=checks,scope='Dedicated Docker network none, root filesystem read-only; generated inputs; no SSH, DB, systemd, S3, signing or existing observation access'),indent=2))
print(json.dumps(dict(passed=True,checks=len(checks))))
