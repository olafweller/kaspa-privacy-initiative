"""B boundary wait: retry read-only status transport failures within one deadline.
Arm is a single mutation. Lost arm response is terminal, never retried.
"""
import hashlib,json,pathlib,subprocess,time,os

def wait_and_arm(C,run_id,deadline,directory,atomic,clock=time.monotonic,sleep=time.sleep):
 directory=pathlib.Path(directory)
 while True:
  if clock()>=deadline:raise TimeoutError('boundary acceptance deadline')
  try:s=C('status')
  except (subprocess.TimeoutExpired,TimeoutError,ConnectionError):
   atomic(directory/'boundary-transport-status.json',{'at':time.time(),'status':'read-only-status-disconnected','retry':'bounded same acceptance deadline'})
   if clock()>=deadline:raise TimeoutError('boundary acceptance deadline')
   sleep(min(2,max(0,deadline-clock())));continue
  # A reply crossing the deadline never authorizes arm, even if otherwise valid.
  if clock()>=deadline:raise TimeoutError('late boundary status')
  if s.get('run_id')!=run_id or s.get('faulted') is not False:raise ValueError('wrong/faulted status')
  events=s['events']
  if len(events) not in (1,2) or [x['kind'] for x in events]!=['PREPARED','C_ACCEPTED_DURABLE'][:len(events)]:raise ValueError('unexpected/previously-consumed boundary')
  if len(events)==2 and s['sandbox_inspected']:
   receipt=s['receipt']
   if not isinstance(receipt,dict) or receipt.get('run_id')!=run_id or receipt.get('acceptance_digest')!=events[1]['digest'] or receipt.get('at')!=events[1]['at']:raise ValueError('receipt/status mismatch')
   if not -2<=time.time()-receipt['at']<=120:raise ValueError('stale receipt')
   # Durable exclusive intent precedes one arm call. Restart cannot issue a second call.
   claim=directory/'arm-attempt.json';claim.parent.mkdir(parents=True,exist_ok=True)
   durable(claim,{'at':time.time(),'run_id':run_id,'receipt_sha256':hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'one_attempt':True})
   if clock()>=deadline:raise TimeoutError('boundary deadline before arm')
   result=C('arm',{'receipt':receipt})
   if result.get('armed') is not True or not isinstance(result.get('arm_digest'),str):raise ValueError('invalid arm response')
   if clock()>=deadline:raise TimeoutError('late arm response; no retry, no recovery')
   return result
  sleep(min(2,max(0,deadline-clock())))

def durable(path,data):
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(json.dumps(data,sort_keys=True,separators=(',',':')).encode());f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
