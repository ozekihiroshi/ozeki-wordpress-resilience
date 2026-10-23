"""Generated-data preparation queue; existing generation-kit CLI only. Never signs."""
import argparse,fcntl,hashlib,json,os,re,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def atomic(p,v):
 p=Path(p);t=p.with_suffix('.tmp');t.write_text(json.dumps(v,ensure_ascii=False));os.replace(t,p)
def report(c,profile):
 items=[read(p) for p in sorted(Path(c['state']).glob('*/status.json'))]
 atomic(c['report'],{'schema':'owr-reconstruction-console-v1','updated_at':int(time.time()),'profile_sha256':sha(profile),'items':items})
def execute(receipt,profile,work,log):
 with log.open('ab') as out:
  p=subprocess.run([sys.executable,str(ROOT/'tools/rbr-generation-kit.py'),'--generation',str(receipt),'--profile',str(profile),'--work',str(work),'--execute-generated-lab'],stdout=out,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('CLI failed')
 return read(work/'result.json')
def cycle(c,runner=execute):
 profile=Path(c['profile']).read_bytes();ph=sha(profile)
 if read(c['profile']).get('schema')!='owr-rbr-request-profile-v1':raise ValueError('Request-Q profile required')
 report(c,profile)
 for path in sorted(Path(c['inbox']).glob('*.json')):
  try:
   fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('regular file required')
    raw=os.read(fd,32769)
   finally:os.close(fd)
   if len(raw)>32768:raise ValueError('request size')
   q=json.loads(raw)
   if set(q)!={'job_id','attempt','profile_sha256','receipt'} or q['profile_sha256']!=ph or type(q['attempt'])!=int or not 0<=q['attempt']<=99 or not isinstance(q['receipt'],str):raise ValueError('request fields')
   job=sha(q['receipt'].encode()+ph.encode());attempt=q['attempt']
   if q['job_id']!=job or path.name!=f'{job}-{attempt}.json':raise ValueError('identity')
   receipt=json.loads(q['receipt'])
   if set(receipt)!={'state','sequence','generation','expected_ref'} or receipt['state']!='applied' or type(receipt['sequence'])!=int or receipt['sequence']<1:raise ValueError('receipt')
   directory=Path(c['state'])/job;directory.mkdir(exist_ok=True);status=directory/'status.json'
   previous=read(status) if status.exists() else None
   if previous and attempt<=previous['attempt']:continue
   if previous and (attempt!=previous['attempt']+1 or previous['state'] not in ['failed','interrupted']):continue
   if not previous and attempt!=0:continue
   receiptpath=directory/'receipt.json';profilepath=directory/'profile.json'
   if receiptpath.exists() and (receiptpath.read_text()!=q['receipt'] or profilepath.read_bytes()!=profile):raise ValueError('frozen input changed')
   receiptpath.write_text(q['receipt']);profilepath.write_bytes(profile)
   current={'job_id':job,'attempt':attempt,'profile_sha256':ph,'generation_sha256':receipt['generation']['sha256'],'expected_sha256':receipt['expected_ref']['sha256'],'state':'running','reason':'固定版取得・保持確認・計画検査・S3キット保存を実行中'}
   atomic(status,current);report(c,profile)
   try:
    result=runner(receiptpath,profilepath,directory/'work',directory/'private.log')
    if result['state']!='stored_awaiting_independent_approval' or result['generation_ref']!=receipt['generation'] or result.get('public_activation') is not False:raise ValueError('result binding')
    current.update(state=result['state'],reason='独立署名承認は別操作です',root_receipt=result['root_receipt'])
   except Exception:
    operations=directory/'work/transport/operations.json'
    uncertain=False
    if operations.exists():
     try:uncertain=any(o['method']=='PUT' and o['state']!='acknowledged' for o in read(operations))
     except Exception:uncertain=True
    reason='CLI処理が失敗しました。担当者が非公開ログを確認してから再開してください'
    log=directory/'private.log';diagnostic=log.read_text(errors='replace')[-16384:] if log.exists() else ''
    for markers,message in [(['retention','protection','Expired'],'保持期限・保護条件を満たしません。期限と設定を確認してください'),(['Resume input changed','Fixed bytes mismatch','digest'],'入力または固定版の整合性を確認できません。担当者の照合が必要です'),(['authorization failed','preflight','Connection','Timeout'],'接続・権限・事前検査に失敗しました。担当者が接続設定を確認してください'),(['Planner','planner','plan.php'],'再構築計画の検査に失敗しました。規則・実行環境を確認してください')]:
     if any(marker in diagnostic for marker in markers):reason=message;break
    current.update(state='blocked' if uncertain else 'failed',reason='S3書込み結果の照合が必要です。再送しません' if uncertain else reason)
   atomic(status,current);report(c,profile)
  except (ValueError,TypeError,KeyError,OSError):
   # Untrusted malformed requests never become commands or expose private diagnostics.
   continue
 report(c,profile)
def main():
 p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--once',action='store_true');p.add_argument('--allow-disposable-lab',action='store_true');a=p.parse_args()
 if not a.allow_disposable_lab:p.error('Dedicated generated-data opt-in required')
 c=read(a.config)
 if c.get('schema')!='owr-kit-preparation-config-v1':raise ValueError('config')
 inbox=Path(c['inbox']).resolve();state=Path(c['state']);state.mkdir(parents=True,exist_ok=True)
 for path in [a.config,Path(c['profile']),state,Path(c['report'])]:
  if path.is_symlink() or path.resolve().is_relative_to(inbox):raise ValueError('Trusted inputs must be outside inbox')
 lock=(state/'worker.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 for s in state.glob('*/status.json'):
  v=read(s)
  if v['state']=='running':v.update(state='interrupted',reason='前回処理の終了を確認できません。再開時も既存CLIが記録を再検査します');atomic(s,v)
 while True:
  cycle(c)
  if a.once:break
  time.sleep(15)
if __name__=='__main__':main()
