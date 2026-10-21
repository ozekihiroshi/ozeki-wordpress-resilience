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
    from datetime import timedelta
    daily=load('admitted_daily_lab','first-site-daily.py')
    store={};operations=[]
    class Adapter:
        def __init__(self,path):self.path=path;path.mkdir();self.ops=[]
        def save(self):daily.io.write_json(self.path/'operations.json',self.ops)
        def put(self,bucket,key,body):
            store[key]=body;event=dict(method='PUT',key=key,sha256=daily.gate.sha(body),bytes=len(body),state='acknowledged',version_id='lab-fixed-v1');self.ops.append(event);operations.append(event);self.save();return 'lab-fixed-v1'
        def get(self,loc):
            body=store[loc['key']];event=dict(method='GET',key=loc['key'],sha256=daily.gate.sha(body),bytes=len(body),version_id='lab-fixed-v1');self.ops.append(event);operations.append(event);self.save()
            return dict(body=body,version_id='lab-fixed-v1',reader_identity='OwrM1RecoveryReader',mode='GOVERNANCE',last_modified=daily.gate.now().isoformat(),retain_until=(daily.gate.now()+timedelta(days=36)).isoformat())
    stamp=daily.gate.now()
    original=paths['health'].read_bytes();bad=dict(health);bad['state']='transfer_failed';paths['health'].write_text(json.dumps(bad))
    blocked=daily.Coordinator(root/'blocked-daily')
    row=blocked.tick_admitted(stamp,admission=paths,backend=counted(),adapter_factory=Adapter,preflight=lambda:None)
    check(row['state']=='unknown' and not calls and not operations,'invalid admission started capture or PUT')
    check(blocked.tick_admitted(stamp,admission=paths,backend=counted(),adapter_factory=Adapter,preflight=lambda:None)['state']=='unknown' and not calls and not operations,'blocked run retried')
    results.append(dict(name='daily_initial_failure_no_capture_no_put_no_retry',passed=True))
    paths['health'].write_bytes(original)
    b=counted();original_preflight=b.preflight
    def changed(config):original_preflight(config);paths['health'].write_text(json.dumps(bad))
    b.preflight=changed
    late=daily.Coordinator(root/'late-daily')
    row=late.tick_admitted(stamp,admission=paths,backend=b,adapter_factory=Adapter,preflight=lambda:None)
    check(row['state']=='unknown' and not calls and not operations,'late admission failure started capture or PUT')
    results.append(dict(name='daily_late_failure_no_fence_no_put',passed=True))
    paths['health'].write_bytes(original)
    accepted=daily.Coordinator(root/'accepted-daily')
    row=accepted.tick_admitted(stamp,admission=paths,backend=counted(),adapter_factory=Adapter,preflight=lambda:None)
    check(row['state']=='awaiting_approval','daily capture/publication failed; retained ledger')
    status=accepted.status(stamp)['runs'][0]
    check(status['storage_complete'] and status['approval_state']=='pending' and not status['restore_allowed'],'publication confused with signature approval')
    check(sum(x['method']=='PUT' for x in operations)==2 and calls.count('fence')==1 and calls.count('stream')==2,'unexpected transfers')
    results.append(dict(name='real_capture_daily_mock_storage_pending_approval',passed=True,puts=2))
    snapshot=list(operations);previous=list(calls)
    check(accepted.tick_admitted(stamp,admission=paths,backend=counted(),adapter_factory=Adapter,preflight=lambda:None)==row and operations==snapshot and calls==previous,'duplicate slot repeated capture or storage')
    results.append(dict(name='daily_duplicate_no_capture_no_put',passed=True))
    check(php("echo file_exists('/tmp/owr-gate.fence')?'bad':'ok';")==b'ok','source not released')
