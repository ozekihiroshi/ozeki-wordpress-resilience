"""Validate packaged deployment drafts and reuse the actual WordPress ZIP acceptance."""
import argparse,hashlib,json,subprocess,sys,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
def main():
 p=argparse.ArgumentParser();p.add_argument('--operator-review',action='store_true');p.add_argument('--distribution',type=Path,required=True);p.add_argument('--old-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 m=json.loads((a.distribution/'manifest.json').read_text());art={}
 for entry in m['artifacts']:
  path=a.distribution/entry['file'];assert sha(path)==entry['sha256'];art['kit' if entry['file'].startswith('owr-development-kit') else 'plugin']=path
 kit=a.output/'code';kit.mkdir()
 with zipfile.ZipFile(art['kit']) as z:
  for name in z.namelist():
   assert name.startswith('owr-development-kit/') and (kit/name).resolve().is_relative_to(kit.resolve())
  z.extractall(kit)
 root=kit/'owr-development-kit';entry=next(e for e in m['artifacts'] if e['file']==art['kit'].name)
 assert tree(root)==entry['files']
 config=a.output/'configuration';config.mkdir();bundle=config/'reviewed-draft'
 cmd=[sys.executable,'-B',str(root/'tools/external-deployment-plan.py')]
 topology=next((root/'examples/deployment').glob('*.json'))
 inputs=['--profile',str(root/'examples/first-site/generated-lab.json'),'--topology',str(topology)]
 def run(args):return subprocess.run(args,capture_output=True,text=True)
 before=tree(config);q=run(cmd+['plan']+inputs);assert q.returncode==0,q.stderr;assert tree(config)==before
 plan=json.loads(q.stdout);assert not plan['production_ready'] and not plan['apply_supported']
 q=run(cmd+['generate']+inputs+['--output',str(bundle)]);assert q.returncode==0,q.stderr
 # Operator-owned additions must not be replaced by a second generation.
 (bundle/'operator-note.txt').write_text('Dedicated generated fixture; preserve reviewed settings\n')
 snapshot=tree(config);q=run(cmd+['generate']+inputs+['--output',str(bundle)]);assert q.returncode==2;assert tree(config)==snapshot
 nextcode=a.output/'next-code';nextcode.mkdir()
 with zipfile.ZipFile(art['kit']) as z:z.extractall(nextcode)
 assert tree(config)==snapshot
 checks=['kit ZIP bytes and every extracted file match manifest','packaged plan is read-only and not production-ready','packaged generate creates new draft','existing reviewed draft overwrite refused without changes','separate code extraction preserves external configuration']
 (a.output/'kit-result.json').write_text(json.dumps(dict(passed=True,checks=checks,kit_sha256=sha(art['kit']),configuration_hashes=snapshot),indent=2))
 print('PASS packaged kit: '+str(len(checks))+' checks',flush=True)
 q=subprocess.run([sys.executable,'-B',str(root/'tools/run-preflight-zip-lab.py'),'--zip',str(art['plugin'].resolve()),'--old-zip',str(a.old_zip.resolve()),'--output',str(a.output/'wordpress')]+(['--operator-review'] if a.operator_review else []))
 assert q.returncode==0,'WordPress ZIP acceptance failed; keep diagnostics'
 result=json.loads((a.output/'wordpress/result.json').read_text());assert result['passed'];assert tree(config)==snapshot
 (a.output/'result.json').write_text(json.dumps(dict(passed=True,kit_checks=checks,wordpress=result,kit_sha256=sha(art['kit']),plugin_sha256=sha(art['plugin']),production_ready=False,scope='Synthetic dedicated fixtures; packaged code and actual WordPress updater; no service rollout, S3, signing, production or observation changes'),indent=2))
 print('ALL_PASS',flush=True)
if __name__=='__main__':main()
