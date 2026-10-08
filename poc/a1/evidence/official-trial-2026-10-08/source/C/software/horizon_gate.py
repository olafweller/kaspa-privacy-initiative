"""Read-only pre-funding gate. No caller can promote capture readiness."""
import pathlib,json,hashlib,time,os
from capture import canonical

def check(x,m):
 if not x:raise ValueError(m)
def sha(x):return hashlib.sha256(x).hexdigest()
def value(db,key):
 r=db.execute('select value from metadata where key=?',(key,)).fetchone();check(r is not None,'missing capture '+key);return json.loads(r[0])
def require_ready(db,namespace,now=time.time,monotonic=time.monotonic,inspect_worker=True,require_watch=False):
 state=value(db,'horizon_state');check(state['schema']=='kpi-capture-horizon/v1' and state['namespace']==namespace and state['phase']=='READY','attempt capture horizon not READY')
 check(value(db,'last_error') is None,'capture error blocks funding');last=value(db,'last_commit');check(last==state['current'] and last['cursor']==value(db,'cursor'),'capture cursor/state discontinuity');check(-2<=now()-last['at']<=15,'capture commit stale')
 projection=[r[0] for r in db.execute('select hash from active_chain order by position')];check(sha(canonical(projection))==state['projection_sha256'],'capture projection changed');cp=value(db,'sealed_checkpoint');sealed=value(db,'sealed_checkpoint_sha256');check(cp['namespace']==namespace and sha(canonical(cp))==sealed and cp['cursor'] in set(projection),'sealed checkpoint invalid/removed');baseline=value(db,'baseline_receipt_sha256');check(sha(canonical(value(db,'baseline_receipt')))==baseline and cp['baseline_receipt_sha256']==baseline,'baseline receipt changed')
 proof=value(db,'initialization_complete_page');complete_sha=value(db,'initialization_complete_page_sha256');check(sha(canonical(proof))==complete_sha and proof['request']['minConfirmationCount']==0 and proof['request']['dataVerbosityLevel']=='Full' and proof['core_sha256']==state['core_sha256'] and proof['seq']<=last['seq'],'complete live page proof invalid');row=db.execute('select cursor,digest,response_sha,request from pages where seq=?',(proof['seq'],)).fetchone();check(row and row[0]==proof['cursor'] and row[1]==proof['digest'] and row[2]==proof['response_sha256'] and json.loads(row[3])==proof['request'],'complete live page no longer retained')
 worker=value(db,'horizon_worker');check(worker['source_sha256']==state['horizon_source_sha256'],'capture worker source changed');check(worker['namespace']==namespace and 0<=monotonic()-worker['monotonic']<=10,'capture worker stale');check(worker['boot_sha256']==sha(pathlib.Path('/proc/sys/kernel/random/boot_id').read_bytes()),'capture worker belongs to another boot')
 if inspect_worker:
  p=pathlib.Path('/proc')/str(worker['pid']);check(p.exists() and namespace.encode() in (p/'cmdline').read_bytes() and b'horizon_capture.py' in (p/'cmdline').read_bytes(),'capture worker unavailable/wrong namespace');check((p/'stat').read_text().split(') ',1)[1].split()[0]!='Z','capture worker dead')
 if require_watch:
  watch=value(db,'watch_binding');check(watch['namespace']==namespace,'watch namespace mismatch');row=db.execute('select at,addresses_sha,response_sha,response from utxo_observations order by seq desc limit 1').fetchone();check(row is not None and -2<=now()-row[0]<=15 and row[1]==sha(canonical(watch['addresses'])),'new reserve watch not durably fresh');raw=__import__('zlib').decompress(row[3]);check(len(raw)<=16*1024**2 and sha(raw)==row[2] and len(json.loads(raw)['entries'])<=8,'reserve observation corrupt/unbounded')
 return {'state':'READY','namespace':namespace,'sealed_checkpoint':cp,'sealed_checkpoint_sha256':sealed,'baseline_receipt_sha256':baseline,'initialization_complete_page_sha256':complete_sha,'current':last,'funding_authorization':False,'scope':'capture qualification only; separate fresh live authorization/fee-policy/freeze required'}
