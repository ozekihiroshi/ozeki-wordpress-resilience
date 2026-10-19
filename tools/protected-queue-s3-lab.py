"""Explicit real-AWS experiment; only generated isolated-lab assets may be passed here."""
import importlib.util,json,secrets,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
gate=load('real_queue_gate','protected-queue-set.py');transport=load('real_queue_s3','queue-s3-adapter.py')
def exercise(assets,paired,mark):
    if paired['site_id']!='isolated-queue-lab':raise ValueError('real transfer restricted to generated lab site')
    if sum(map(len,assets.values()))>128*1024*1024:raise ValueError('lab transfer budget exceeded')
    preflight=transport.preflight()
    set_id='AWS-'+secrets.token_hex(8);site=paired['site_id']
    root=Path.home()/'.local/share/owr-queue-s3-lab'/set_id;root.mkdir(mode=0o700,parents=True,exist_ok=False)
    trust=root/'operator-trust';trust.mkdir(mode=0o700)
    adapter=transport.S3Adapter(root/'transfer-receipts');prefix=f'sites/{site}/sets/{set_id}/'
    report={'passed':False,'set_id':set_id,'bucket':transport.BUCKET,'prefix':prefix,'preflight':preflight,'production_data':False,'production_key_used':False,'stages':[]}
    def save():(root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    def passed(name):report['stages'].append(name);save();mark(name)
    def denied(actor,method,**kw):
        try:
            with adapter.request(actor,method,prefix+'permission-probe.txt',**kw) as response:
                report.setdefault('unexpected_mutation_receipts',[]).append({'actor':actor,'method':method,'version_id':response.headers.get('x-amz-version-id')});save()
        except RuntimeError as exc:
            if str(exc)==f'S3 {method} HTTP 403 AccessDenied':
                report.setdefault('permission_checks',[]).append({'actor':actor,'method':method,'error_code':'AccessDenied','http_status':403});save();return
            raise
        raise RuntimeError(actor+' '+method+' unexpectedly allowed; stop and inspect test object')
    try:
        save();passed('real_aws_bucket_configuration_and_separate_sts_roles_verified')
        denied('reader','PUT',body=b'OWR generated lab permission probe\n')
        body=b'OWR generated lab permission probe\n';version=adapter.put(transport.BUCKET,prefix+'permission-probe.txt',body)
        probe={'bucket':transport.BUCKET,'region':transport.REGION,'key':prefix+'permission-probe.txt','version_id':version,'size_bytes':len(body),'sha256':gate.sha(body),'writer_identity':'my-ssm-role'}
        gate.observe('queue',body,probe,adapter.get(probe),'OwrM1RecoveryReader')
        denied('reader','DELETE',version=version);denied('writer','DELETE',version=version)
        gate.observe('queue',body,probe,adapter.get(probe),'OwrM1RecoveryReader')
        passed('real_reader_write_delete_and_writer_delete_denied_probe_intact')
        manifest=gate.build(assets,paired,site,set_id,transport.BUCKET,transport.REGION,'my-ssm-role','OwrM1RecoveryReader',adapter.put,adapter.get)
        passed('real_three_assets_put_with_retention_and_read_by_fixed_version')
        document=root/'recovery-set.json';sig=root/'recovery-set.sig';document.write_bytes(gate.encode(manifest))
        with tempfile.TemporaryDirectory(prefix='signer-',dir=root) as tmp:
            key=Path(tmp)/'private.pem'
            subprocess.run(['openssl','genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(key)],check=True,capture_output=True);key.chmod(0o600)
            subprocess.run(['openssl','pkey','-in',str(key),'-pubout','-out',str(trust/'public.pem')],check=True,capture_output=True)
            subprocess.run(['openssl','dgst','-sha256','-sign',str(key),'-out',str(sig),str(document)],check=True,capture_output=True)
        pin={'status':'active','site_id':site,'set_id':set_id,'minimum_sequence':1,'bucket':transport.BUCKET,'region':transport.REGION,'writer_identity':'my-ssm-role','reader_identity':'OwrM1RecoveryReader','public_key_sha256':gate.sha((trust/'public.pem').read_bytes()),'approved_document_sha256':gate.sha(document.read_bytes()),'envelope':{}}
        (trust/'pin.json').write_bytes(gate.encode(pin))
        gate.authorize(trust,document,sig,site,set_id)
        for role,path in [('document',document),('signature',sig)]:
            data=path.read_bytes();loc={'bucket':transport.BUCKET,'region':transport.REGION,'key':prefix+path.name,'version_id':adapter.put(transport.BUCKET,prefix+path.name,data),'size_bytes':len(data),'sha256':gate.sha(data),'writer_identity':'my-ssm-role'}
            response=adapter.get(loc)
            observed=gate.observe('queue',data,loc,response,'OwrM1RecoveryReader')
            pin['envelope'][role]={'locator':loc,'retention':observed['retention']}
        (trust/'pin.json').write_bytes(gate.encode(pin))
        document,sig=gate.fetch_envelope(trust,adapter.get,root/'downloaded-envelope')
        passed('real_signed_envelope_stored_and_retrieved_from_independent_pin')
        invalid=root/'invalid.sig';invalid.write_bytes(b'invalid');before=len(adapter.operations)
        try:gate.fetch_verified(trust,document,invalid,site,set_id,paired['handler_sha256'],adapter.get)
        except ValueError:pass
        else:raise RuntimeError('invalid signature accepted')
        if len(adapter.operations)!=before:raise RuntimeError('asset fetched before rejecting signature')
        invalid.unlink();passed('real_downloaded_envelope_bad_signature_stops_before_asset_fetch')
        fetched,result=gate.fetch_verified(trust,document,sig,site,set_id,paired['handler_sha256'],adapter.get)
        if fetched!=assets:raise RuntimeError('real S3 roundtrip bytes mismatch')
        passed('real_fixed_versions_signature_retention_and_paired_checkpoint_verified')
        evidence={'verification':result,'transport':'AWS S3; EC2-role-scoped presigned HTTPS','signature':'RSA-SHA256 on host; disposable lab private key destroyed; trust retained independently','set_id':set_id,'bucket':transport.BUCKET,'prefix':prefix,'trust_directory':str(trust),'signed_document_sha256':gate.sha(document.read_bytes()),'private_key_retained':False,'s3_data_request_count':adapter.request_count,'minimum_asset_retention_until':manifest['minimum_retention_until'],'delete_denial_scope':'explicit role policy deny; not an independent Object Lock deletion enforcement test','production_key_used':False}
        report.update(passed=True,evidence=evidence,restore_not_yet_completed=True);save()
        return fetched,evidence
    except Exception as exc:
        report.update(error_type=type(exc).__name__,error=str(exc) if isinstance(exc,(RuntimeError,ValueError)) else 'Details suppressed');save();raise

def record_restore_success(evidence):
    root=(Path.home()/'.local/share/owr-queue-s3-lab'/evidence['set_id']).resolve()
    if Path(evidence['trust_directory']).resolve()!=root/'operator-trust':raise ValueError('evidence path mismatch')
    path=root/'result.json';report=json.loads(path.read_text())
    if report['set_id']!=evidence['set_id'] or not report['passed']:raise ValueError('storage stage incomplete')
    report.update(restore_not_yet_completed=False,isolated_restore_passed=True,production_recovery_approved=False)
    path.write_text(json.dumps(report,indent=2)+'\n')

def resume(set_id,mark):
    """Continue a retained, independently signed lab set; never repeat uncertain PUTs."""
    import re
    if not re.fullmatch('AWS-[a-f0-9]{16}',set_id):raise ValueError('invalid resume set')
    root=Path.home()/'.local/share/owr-queue-s3-lab'/set_id;trust=root/'operator-trust'
    report=json.loads((root/'result.json').read_text());original=json.loads(json.dumps(report))
    (root/('result-before-resume-'+secrets.token_hex(4)+'.json')).write_text(json.dumps(original,indent=2)+'\n')
    preflight=transport.preflight();document=root/'recovery-set.json';sig=root/'recovery-set.sig'
    site='isolated-queue-lab';manifest,pin=gate.authorize(trust,document,sig,site,set_id)
    expected=['real_aws_bucket_configuration_and_separate_sts_roles_verified','real_reader_write_delete_and_writer_delete_denied_probe_intact','real_three_assets_put_with_retention_and_read_by_fixed_version']
    if report['stages'][:3]!=expected or len(report.get('permission_checks',[]))!=3:raise ValueError('required initial stages not recorded')
    for name in expected:mark(name,reused_from_prior_run=True)
    prior=[]
    for p in root.glob('*/operations.json'):prior.extend(json.loads(p.read_text()))
    adapter=transport.S3Adapter(root/('resume-receipts-'+secrets.token_hex(4)))
    report['resume_preflight']=preflight;report['prior_failure']=original.get('error');report.pop('error',None);report.pop('error_type',None)
    def save():(root/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    def passed(name):
        if name not in report['stages']:report['stages'].append(name)
        save();mark(name)
    try:
        prefix=f'sites/{site}/sets/{set_id}/'
        pin['envelope']={}
        for role,path in [('document',document),('signature',sig)]:
            data=path.read_bytes();key=prefix+path.name
            puts=[p for p in prior if p['method']=='PUT' and p['key']==key]
            if puts:
                if len(puts)!=1 or puts[0]['state']!='acknowledged' or puts[0]['sha256']!=gate.sha(data) or puts[0]['bytes']!=len(data):raise ValueError('uncertain or mismatching prior PUT; manual receipt review required')
                version=puts[0]['version_id']
            else:version=adapter.put(transport.BUCKET,key,data)
            loc={'bucket':transport.BUCKET,'region':transport.REGION,'key':key,'version_id':version,'size_bytes':len(data),'sha256':gate.sha(data),'writer_identity':'my-ssm-role'}
            response=adapter.get(loc);observed=gate.observe('queue',data,loc,response,'OwrM1RecoveryReader')
            pin['envelope'][role]={'locator':loc,'retention':observed['retention']}
        (trust/'pin.json').write_bytes(gate.encode(pin))
        document,sig=gate.fetch_envelope(trust,adapter.get,root/('resumed-envelope-'+secrets.token_hex(4)))
        passed('real_signed_envelope_stored_and_retrieved_from_independent_pin')
        invalid=root/'invalid.sig';invalid.write_bytes(b'invalid');before=adapter.request_count
        try:gate.fetch_verified(trust,document,invalid,site,set_id,manifest['paired']['handler_sha256'],adapter.get)
        except ValueError:pass
        else:raise RuntimeError('invalid signature accepted')
        if adapter.request_count!=before:raise RuntimeError('fetch before signature rejection')
        invalid.unlink();passed('real_downloaded_envelope_bad_signature_stops_before_asset_fetch')
        handler=gate.sha((ROOT/'lab/consistency/external-job.php').read_bytes())
        assets,result=gate.fetch_verified(trust,document,sig,site,set_id,handler,adapter.get)
        passed('real_fixed_versions_signature_retention_and_paired_checkpoint_verified')
        evidence={'verification':result,'transport':'AWS S3; EC2-role-scoped presigned HTTPS','signature':'RSA-SHA256 on host; original lab signature reused without private key','set_id':set_id,'bucket':transport.BUCKET,'prefix':prefix,'trust_directory':str(trust),'signed_document_sha256':gate.sha(document.read_bytes()),'private_key_retained':False,'s3_data_request_count':len(prior)+len(report['permission_checks'])+adapter.request_count,'minimum_asset_retention_until':manifest['minimum_retention_until'],'delete_denial_scope':'explicit role policy deny; not an independent Object Lock deletion enforcement test','production_key_used':False,'resumed_after_clock_observation_failure':True}
        report.update(passed=True,evidence=evidence,restore_not_yet_completed=True);save()
        return assets,evidence,manifest['paired']
    except Exception as exc:
        report.update(passed=False,error_type=type(exc).__name__,error=str(exc) if isinstance(exc,(RuntimeError,ValueError)) else 'Details suppressed');save();raise
