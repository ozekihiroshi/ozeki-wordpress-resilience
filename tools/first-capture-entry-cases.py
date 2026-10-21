"""Actual generated WordPress/MariaDB acceptance for the new capture entry."""
import copy, importlib.util, json, os, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def exercise(db,web,php,sql,hold,ready,release,run,check,results,output):
    a=load('capture_api','first-site-capture.py');module=load('docker_backend','first-site-docker-lab.py')
    c=json.loads((ROOT/'examples/first-site/generated-lab.json').read_text())
    # Real standard attachment fields. No synthetic content-hash postmeta required.
    attachment=php("require '/var/www/html/wp-load.php'; $p=WP_CONTENT_DIR.'/uploads/one.png'; file_put_contents($p,base64_decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZfoAAAAASUVORK5CYII=')); $id=wp_insert_attachment(['post_title'=>'Capture image','post_status'=>'inherit','post_mime_type'=>'image/png'],$p); update_attached_file($id,$p); wp_update_attachment_metadata($id,['width'=>1,'height'=>1,'file'=>'one.png','sizes'=>[]]); wp_insert_post(['post_title'=>'First site normal post','post_status'=>'publish','post_content'=>'Image attachment']); echo $id;")
    check(int(attachment)>0,'normal attachment creation failed')
    run('docker','exec',web,'sh','-c',"printf 'auto_prepend_file=/lab/route-prepend.php\n' > /usr/local/etc/php/conf.d/owr-route-gate.ini")
    run('docker','exec',web,'apachectl','-k','graceful')
    run('docker','exec',web,'sh','-c',"printf '<?php echo ini_get(\"auto_prepend_file\");' > /var/www/html/gate-probe.php")
    deadline=time.monotonic()+20
    while php("echo file_get_contents('http://127.0.0.1/gate-probe.php');")!=b'/lab/route-prepend.php':
        check(time.monotonic()<deadline,'new Apache config not active');time.sleep(.2)
    output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    root=output.parent/(output.stem+'-private');root.mkdir(mode=0o700)
    from datetime import datetime,timezone
    entry=load('admitted_capture','first-capture-entry.py');a=entry.api
    c['storage']['destination_ref']='dedicated-storage-ref'
    c['trust'].update(operator='lab-operator',public_pin_ref='dedicated-test-pin')
    workspace=root/'capture';workspace.mkdir(mode=0o700)
    now=datetime.now(timezone.utc).isoformat();d=a.digest
    inv={k:copy.deepcopy(c[k]) for k in ('site_id','wordpress','database','files','writers','queue','dependencies','runtime')}
    inv.update(format='owr-deployment-inventory-v1',config_sha256=d(c),observed_at=now,incomplete_runs=0,uncertain_puts=0)
    assessment=entry.gate.pre.assess(c,inv,workspace)
    assessment.update(state='needs_configuration',host_observation={'state':'validated_report','unverified':entry.gate.SCOPES[:-1]},issues=[{'category':'configuration','code':'host_unverified_scope_remaining'}])
    # Synthetic admission evidence: this test exercises execution, not SSH collection.
    now=datetime.now(timezone.utc).isoformat()
    report=dict(format='owr-preflight-admin-v1',site_id=c['site_id'],config_sha256=d(c),attempted_at=now,result=assessment)
    health=dict(format='owr-preflight-transfer-v1',site_id=c['site_id'],config_sha256=d(c),attempted_at=now,state='ok',report_at=now)
    review=dict(format='owr-first-capture-review-v1',site_id=c['site_id'],config_sha256=d(c),report_sha256=d(report),health_sha256=d(health),inventory_sha256=d(inv),workspace=str(workspace),reviewed_at=now,reviewed_by=c['operations']['owner'],scope='dedicated_trial_only',confirmations={k:dict(confirmed=True,evidence_ref='generated-record/'+k) for k in entry.gate.SCOPES})
    paths={}
    for name,value in [('profile',c),('inventory',inv),('report',report),('health',health),('review',review)]:
        p=root/(name+'.json');p.write_text(json.dumps(value));p.chmod(0o600);paths[name]=p
    paths['workspace']=workspace
    def backend():return module.DockerBackend(a,c,db,web,php,sql,hold,ready,release,run)
    calls=[]
    def counted():
        b=backend()
        for name in ('fence','stream'):
            original=getattr(b,name)
            def call(*args,_name=name,_fn=original):calls.append(_name);return _fn(*args)
            setattr(b,name,call)
        return b
    original=paths['health'].read_bytes()
    bad=dict(health);bad['state']='transfer_failed';paths['health'].write_text(json.dumps(bad))
    try:entry.capture_from_files(**paths,backend=counted());raise RuntimeError('invalid admission accepted')
    except a.Rejected as exc:check('admission_blocked' in str(exc),'unexpected rejection')
    check(calls==[] and not any(p.is_dir() for p in workspace.iterdir()),'blocked capture had side effects')
    results.append(dict(name='initial_failure_no_capture',passed=True))
    paths['health'].write_bytes(original)
    b=counted();original_preflight=b.preflight
    def changed_preflight(config):
        original_preflight(config);paths['health'].write_text(json.dumps(bad))
    b.preflight=changed_preflight
    work,result=entry.capture_from_files(**paths,backend=b)
    check(not result['capture_started'] and not result['assets'] and calls==[],'late failure started capture')
    check(list(work.iterdir())==[work/'result.json'],'late failure created assets')
    results.append(dict(name='live_preflight_then_changed_health_no_fence',passed=True))
    paths['health'].write_bytes(original)
    work,result=entry.capture_from_files(**paths,backend=counted())
    check(result['eligible_for_consistency_acceptance'] and result['capture_started'] and result['release_confirmed'],'admitted real capture failed: '+json.dumps(result))
    check(set(result['assets'])=={'database','files'} and calls.count('fence')==1 and calls.count('stream')==2,'unexpected asset capture')
    results.append(dict(name='admitted_real_db_files_capture_and_release',passed=True,asset_bytes={k:v['bytes'] for k,v in result['assets'].items()}))
    check(php("echo file_exists('/tmp/owr-gate.fence')?'bad':'ok';")==b'ok','fence remained')
    check(sql('SELECT COUNT(*) FROM wp_posts;').strip()!=b'0','DB unavailable after release')
    results.append(dict(name='source_available_after_release',passed=True))
