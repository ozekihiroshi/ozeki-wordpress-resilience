"""Signed two-asset first-site recovery gate (no queue). Transport is injected; no AWS/restore side effects on import."""
import datetime as dt,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FORMAT='owr-protected-first-site-set-v1'
NAMES={'database':'database.sql','files':'wordpress-files.tar.gz'}
def check(ok,message):
    if not ok:raise ValueError(message)
def now():return dt.datetime.now(dt.timezone.utc)
def date(value):
    t=dt.datetime.fromisoformat(value.replace('Z','+00:00'));check(t.tzinfo is not None,'timezone required');return t
def sha(data):return hashlib.sha256(data).hexdigest()
def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def fetch_envelope(trust,get,destination):
    """Bootstrap from independently held locators; never search for latest signature."""
    pin=json.loads((trust/'pin.json').read_bytes())
    check(pin['status']=='active','revoked trust')
    check(not trust.resolve().is_relative_to(destination.resolve()),'trust inside download')
    names={'document':'recovery-set.json','signature':'recovery-set.sig'}
    check(set(pin['envelope'])==set(names),'incomplete envelope')
    verified={}
    for role,name in names.items():
        e=pin['envelope'][role];loc=e['locator']
        check(loc['bucket']==pin['bucket'] and loc['region']==pin['region'] and loc['key']==f"sites/{pin['site_id']}/sets/{pin['set_id']}/{name}",'envelope locator mismatch')
        check(isinstance(loc['version_id'],str) and loc['version_id'] not in ('','null'),'unpinned envelope')
        r=get(dict(loc))
        check(r['version_id']==loc['version_id'],'envelope version mismatch')
        check(r['reader_identity']==pin['reader_identity'] and len(r['body'])==loc['size_bytes'] and sha(r['body'])==loc['sha256'],'envelope bytes/reader mismatch')
        check(r['mode']=='GOVERNANCE' and date(r['last_modified'])<=now() and date(r['last_modified'])==date(e['retention']['last_modified']),'envelope observation mismatch')
        check(date(r['retain_until'])>=date(e['retention']['retain_until'])>now() and (date(r['retain_until'])-date(r['last_modified'])).total_seconds()>=35*86400-1,'envelope retention mismatch')
        verified[name]=r['body']
    check(sha(verified['recovery-set.json'])==pin['approved_document_sha256'],'unapproved envelope')
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name,body in verified.items():
        with (destination/name).open('xb') as f:f.write(body)
    return destination/'recovery-set.json',destination/'recovery-set.sig'
def observe(role,body,locator,response,reader):
    """Normalize an exact-version read receipt, shared by publication and restoration."""
    check(role in NAMES,'unknown asset')
    check(response['version_id']==locator['version_id'] and response['reader_identity']==reader,'wrong version or reader')
    check(len(body)==locator['size_bytes'] and sha(body)==locator['sha256'],'asset bytes mismatch')
    check(response['mode']=='GOVERNANCE','retention mode')
    modified=date(response['last_modified']);until=date(response['retain_until'])
    check(modified<=now() and (until-modified).total_seconds()>=35*86400-1 and until>now(),'retention missing/short/expired')
    return {'role':role,'locator':locator,'retention':{k:response[k] for k in ['mode','last_modified','retain_until']},'verification':{'reader_identity':reader,'checked_at':now().isoformat(),'size_and_sha256_match':True}}
def build(assets,paired,site,set_id,bucket,region,writer,reader,put,get):
    """put returns a VersionId; get always receives a locator with explicit VersionId."""
    check(writer!=reader,'writer and reader must differ')
    for ident in [site,set_id]:check(re.fullmatch('[A-Za-z0-9_-]{1,80}',ident) is not None,'unsafe target')
    validate_capture(paired,assets)
    entries=[]
    for role,name in NAMES.items():
        body=assets[role];key=f'sites/{site}/sets/{set_id}/{name}'
        version=put(bucket,key,body)
        check(isinstance(version,str) and version not in ('','null'),'unpinned PUT')
        loc={'bucket':bucket,'region':region,'key':key,'version_id':version,'size_bytes':len(body),'sha256':sha(body),'writer_identity':writer}
        response=get(loc);entries.append(observe(role,response['body'],loc,response,reader))
    issued=now();deadline=min(date(e['retention']['retain_until']) for e in entries)
    return {'format':FORMAT,'algorithm':'rsa-sha256','site_id':site,'set_id':set_id,'sequence':1,'scope':'storage_integrity_candidate_only','production_recovery_approved':False,'malware_cleanliness':'unverified','issued_at':issued.isoformat(),'expires_at':min(issued+dt.timedelta(days=7),deadline).isoformat(),'minimum_retention_until':deadline.isoformat(),'paired':paired,'assets':entries}
def authorize(trust,document,signature,site,set_id):
    """Trust path is operator-selected, never taken from the downloaded document."""
    pin=json.loads((trust/'pin.json').read_bytes())
    check(pin['status']=='active' and pin['site_id']==site and pin['set_id']==set_id,'revoked/wrong trust')
    check(sha((trust/'public.pem').read_bytes())==pin['public_key_sha256'],'public key changed')
    check(document.stat().st_size<65536 and sha(document.read_bytes())==pin['approved_document_sha256'],'document not independently pinned')
    result=subprocess.run(['openssl','dgst','-sha256','-verify',str(trust/'public.pem'),'-signature',str(signature),str(document)],capture_output=True,timeout=10)
    check(result.returncode==0,'invalid signature')
    m=json.loads(document.read_bytes());t=now()
    check(m['format']==FORMAT and m['algorithm']=='rsa-sha256','format')
    check(m['site_id']==site and m['set_id']==set_id,'target mismatch')
    check(m['scope']=='storage_integrity_candidate_only' and m['production_recovery_approved'] is False and m['malware_cleanliness']=='unverified','unsupported approval claim')
    check(type(m['sequence']) is int and m['sequence']>=pin['minimum_sequence'],'stale sequence')
    check(date(m['issued_at'])<=t<date(m['expires_at']),'expired/future approval')
    check(len(m['assets'])==2 and {e['role'] for e in m['assets']}==set(NAMES),'missing/duplicate asset')
    deadlines=[]
    for e in m['assets']:
        loc=e['locator'];ret=e['retention'];obs=e['verification'];role=e['role']
        check(loc['bucket']==pin['bucket'] and loc['region']==pin['region'] and loc['key']==f'sites/{site}/sets/{set_id}/{NAMES[role]}','locator mismatch')
        check(isinstance(loc['version_id'],str) and loc['version_id'] not in ('','null'),'unpinned version')
        check(type(loc['size_bytes']) is int and loc['size_bytes']>0 and re.fullmatch('[a-f0-9]{64}',loc['sha256']) is not None,'invalid asset declaration')
        check(pin['writer_identity']!=pin['reader_identity'] and loc['writer_identity']==pin['writer_identity'] and obs['reader_identity']==pin['reader_identity'],'identity separation missing')
        check(obs['size_and_sha256_match'] is True and date(ret['last_modified'])<=date(obs['checked_at'])<=date(m['issued_at']),'observation mismatch')
        check(ret['mode']=='GOVERNANCE' and (date(ret['retain_until'])-date(ret['last_modified'])).total_seconds()>=35*86400-1,'short retention')
        check(date(ret['retain_until'])>=date(m['expires_at']),'retention shorter than approval')
        deadlines.append(date(ret['retain_until']))
    check(date(m['minimum_retention_until'])==min(deadlines),'retention summary mismatch')
    return m,pin
def fetch_verified(trust,document,signature,site,set_id,config_hash,get):
    m,pin=authorize(trust,document,signature,site,set_id)
    check(m['paired']['config_sha256']==config_hash,'configuration pin mismatch')
    assets={}
    for entry in m['assets']:
        loc=entry['locator'];response=get(dict(loc));body=response['body']
        fresh=observe(entry['role'],body,loc,response,pin['reader_identity'])
        check(date(fresh['retention']['last_modified'])==date(entry['retention']['last_modified']),'stored version changed')
        check(date(fresh['retention']['retain_until'])>=date(entry['retention']['retain_until']),'retention shortened')
        check(date(fresh['retention']['retain_until'])>=date(m['expires_at']),'fresh retention too short')
        assets[entry['role']]=body
    check(m['paired']['config_sha256']==config_hash,'configuration pin mismatch')
    validate_capture(m['paired'],assets)
    # No restore callback is invoked until BOTH assets and capture binding pass.
    return assets,{'passed':True,'assets_verified':2,'attempt_id':m['paired']['attempt_id'],'scope':m['scope'],'production_recovery_approved':False,'malware_cleanliness':'unverified'}


def validate_capture(c,assets):
    check(c['format']=='owr-first-site-capture-v1','capture format')
    check(c['state']=='consistent' and c['eligible_for_consistency_acceptance'] is True and c['release_confirmed'] is True,'capture not accepted/released')
    check(c['production_recovery_approved'] is False,'unsupported production claim')
    check(c['queue']['state']=='absent' and bool(c['queue']['evidence']),'queue absence required')
    check(re.fullmatch('[a-f0-9]{32}',c['attempt_id']) is not None,'attempt id')
    check(re.fullmatch('[a-f0-9]{64}',c['config_sha256']) is not None,'config hash')
    check(set(assets)==set(c['assets'])==set(NAMES),'exactly two assets required')
    for role,body in assets.items():
        a=c['assets'][role]
        check(a['attempt_id']==c['attempt_id'] and a['bytes']==len(body)>0 and a['sha256']==sha(body),'capture bytes/generation mismatch')
