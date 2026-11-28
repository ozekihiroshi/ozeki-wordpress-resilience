"""Prepared isolated worker for the job selected in WordPress administration.

Run on the destination host with WP-CLI and the supported plugins already set up.
No SSH, Docker, installation, database patch, supplied ID map, or source recipe.
The web process never launches a shell. Credentials are prompted, not archived.
"""
import argparse, getpass, importlib.util, json, os, subprocess, tempfile
from pathlib import Path

def load(name):
    p=Path(__file__).with_name('reconstruct-'+name+'.py')
    s=importlib.util.spec_from_file_location('worker_'+name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
    a=argparse.ArgumentParser();a.add_argument('--wordpress',required=True);a.add_argument('--wp-cli',required=True);a.add_argument('--user',required=True);a.add_argument('--allow-root',action='store_true');a.add_argument('--local-runner',help='Administrator-owned JSON argv prefix for a prepared isolated container; never read from a kit');a.add_argument('--private-work-parent');a=a.parse_args()
    base=Path(__file__).resolve().parent
    os.umask(0o077)
    work=Path(tempfile.mkdtemp(prefix='owr-construction-worker-',dir=a.private_work_parent));os.chmod(work,0o700)
    if work.resolve().is_relative_to(Path(a.wordpress).resolve()):
        work.rmdir()
        raise RuntimeError('Worker evidence must be outside the WordPress document root')
    prefix=json.loads(Path(a.local_runner).read_text()) if a.local_runner else []
    if not isinstance(prefix,list) or any(not isinstance(x,str) for x in prefix):raise ValueError('Invalid local runner')
    command=prefix+['php',str(Path(a.wp_cli).resolve()),'--path='+str(Path(a.wordpress).resolve()),'--user='+a.user]
    if a.allow_root:command.append('--allow-root')
    def wp(script,*args):
        r=subprocess.run(command+['eval-file',str(base/script),*map(str,args)],capture_output=True,text=True,timeout=180)
        if r.returncode:
            (work/'bridge-error.txt').write_text(r.stderr)
            raise RuntimeError('Worker bridge failed; inspect private evidence: '+str(work))
        return json.loads(r.stdout)
    password=getpass.getpass('Prepared destination administrator password: ')
    # Claim is permanent even if a later request has an unknown outcome.
    job=wp('construction-job.php','claim')
    modules={k:load(k) for k in ['markdown','tablepress','contact-form','members','acf']}
    classes={'markdown':'NormalMarkdownClient','tablepress':'NormalTablePressClient','contact-form':'NormalContactFormClient','members':'NormalMemberClient','acf':'NormalAcfClient'}
    try:
        clients={k:getattr(m,classes[k])(job['url'],a.user,password,True) for k,m in modules.items()};password=None
        if any(c.me['id']!=job['actor'] for c in clients.values()):raise RuntimeError('HTTP operator differs from queued operator')
        kit=work/'kit.json';kit.write_text(json.dumps(job['kit'],ensure_ascii=False));os.chmod(kit,0o600)
        def api(value):
            # Journal paths are destination-local, never taken from stored input.
            if value.get('operation')=='receipt':value={**value,'journal':str(work/'receipts.json')}
            p=work/'request.json';p.write_text(json.dumps(value,ensure_ascii=False));os.chmod(p,0o600)
            return wp('construction-api.php',p)
        coordinator=load('kit').Reconstruction(clients,api,work/'registration.json')
        result=coordinator.run(job['plan'],lambda:wp('construction-job.php','authors',kit))
        output=work/'result.json';output.write_text(json.dumps(result,ensure_ascii=False));os.chmod(output,0o600)
        print(json.dumps(wp('construction-job.php','finish',output)))
        if result['state']!='registered_pending_remaining_scope_review':raise RuntimeError('Registration held; do not retry the job automatically')
    finally:
        # Keep private evidence for uncertain operations; no automatic destructive cleanup.
        print('Private worker evidence: '+str(work))

if __name__=='__main__':main()
