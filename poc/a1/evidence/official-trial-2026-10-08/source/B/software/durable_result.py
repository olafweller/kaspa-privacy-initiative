"""Infrastructure evidence only. Never accepts a secret or a broadcast request."""
import os,json,pathlib,hashlib,time
ROOT=pathlib.Path('/work/final-qualification/autonomous-results')
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def atomic(path,value):
 path=pathlib.Path(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 tmp=path.with_name(path.name+'.'+os.urandom(8).hex()+'.tmp');fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(encode(value));f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
def seal_tree(directory):
 directory=pathlib.Path(directory);items=[]
 for p in sorted(directory.rglob('*')):
  if p.is_file():
   if p.is_symlink():raise ValueError('evidence symlink forbidden')
   with p.open('rb') as f:os.fsync(f.fileno())
   digest=hashlib.sha256()
   with p.open('rb') as f:
    for block in iter(lambda:f.read(1048576),b''):digest.update(block)
   items.append({'name':str(p.relative_to(directory)),'bytes':p.stat().st_size,'sha256':digest.hexdigest()})
 for p in [directory,*[x for x in directory.rglob('*') if x.is_dir()]]:
  d=os.open(p,os.O_DIRECTORY);os.fsync(d);os.close(d)
 manifest=directory/'archive/history-manifest.json'
 if manifest.exists():
  import re
  m=json.loads(manifest.read_bytes());chunk_items={e['name']:e for e in items if re.fullmatch('archive/page-[0-9]+.json',e['name'])}
  expected={'archive/'+x['name']:{'name':'archive/'+x['name'],'bytes':x['bytes'],'sha256':x['sha256']} for x in m['chunks']}
  if chunk_items!=expected or any(x['bytes']>16777216 for x in expected.values()):raise ValueError('chunk seal/manifest mismatch or oversize')
  items=[e for e in items if e['name'] not in chunk_items]
 return items
SAFE_FAILURES={'timeout','interrupted','guard_or_recovery_rejected','controller_rejected','service_terminated'}
def failure(cfg,stage,reason):
 if reason not in SAFE_FAILURES:reason='controller_rejected'
 result={'schema':'kpi-g5-autonomous-result/v1','run_id':cfg['run_id'],'mode':cfg['mode'],'status':'failure','at':time.time(),'stage':stage,'reason':reason,'broadcast':False,'A_dependency':False}
 path=ROOT/cfg['run_id']/'result.json'
 if not path.exists():atomic(path,result)
 return json.loads(path.read_text())
def send(result):
 from access_check import query
 # One report-delivery attempt, independent of transaction submission; no blind loop.
 receipt=query({'action':'independent','op':'result','run_id':result['run_id'],'result':result})
 if receipt.get('result_sha256')!=hashlib.sha256(encode(result)).hexdigest():raise ValueError('C durable-result receipt mismatch')
 if result['status']=='success' and receipt.get('terminal_sdk_receipt_sha256')!=result['terminal_sdk_receipt_sha256']:raise ValueError('C SDK receipt durability mismatch')
 atomic(ROOT/result['run_id']/'C-durable-result-receipt.json',receipt);return receipt
def finalize_bound(cfg):
 # An unarmed, unauthorised standby has no live experiment to fail. Its
 # invocation still gets immutable lifecycle evidence, including failed startup.
 if cfg['mode'] in {'live','finite-live-native'} and cfg.get('execution_authorized') is not True:return
 p=ROOT/cfg['run_id']/'result.json'
 if not p.exists():
  result=failure(cfg,'systemd-stop','service_terminated')
  try:send(result)
  except Exception:atomic(p.parent/'C-delivery-failed.json',{'at':time.time(),'failure_recorded_on_B':True,'reason':'C-report-channel-unavailable'})
if __name__=='__main__':
 from lifecycle_binding import load_config
 finalize_bound(load_config())

def stop_tree(child):
 """Stop only descendants of the isolated recovery subprocess, including setsid children."""
 import signal
 if child is None:return
 table={}
 for path in pathlib.Path('/proc').glob('[0-9]*/stat'):
  try:
   raw=path.read_text();fields=raw[raw.rfind(')')+2:].split();table[int(path.parent.name)]=(int(fields[1]),fields[19])
  except (OSError,ValueError,IndexError):pass
 selected=[child.pid];i=0
 while i<len(selected):
  selected.extend(p for p,(parent,_) in table.items() if parent==selected[i] and p not in selected);i+=1
 for pid in reversed(selected):
  try:
   path=pathlib.Path('/proc')/str(pid)/'stat';raw=path.read_text();fields=raw[raw.rfind(')')+2:].split()
   if pid in table and fields[19]==table[pid][1]:os.kill(pid,signal.SIGKILL)
  except (ProcessLookupError,OSError):pass
 child.wait(timeout=10)
