"""Read C-owned authenticated observer state; uncertainty never means A loss."""
import hashlib,hmac,json,pathlib,time
KEY=pathlib.Path('/etc/kpi-a-lease-observer.key')
STATE=pathlib.Path('/var/lib/kpi-a-link-observer/state.json')
MAX_AGE=5
VALID={'reachable','unreachable','missing','observer_failure'}
def encode(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sign(value,key):return value|{'authentication_hmac_sha256':hmac.new(key,encode(value),hashlib.sha256).hexdigest()}
def read_state(path=STATE,keypath=KEY,monotonic=time.monotonic,boot_hash=None):
 try:
  path=pathlib.Path(path);keypath=pathlib.Path(keypath)
  if not path.exists():return {'state':'missing','certain':False,'reason':'observer_state_missing'}
  raw=path.read_bytes()
  if len(raw)>8192:raise ValueError('oversized observer state')
  x=json.loads(raw);tag=x.pop('authentication_hmac_sha256');key=keypath.read_bytes()
  if len(key)!=32 or not hmac.compare_digest(tag,hmac.new(key,encode(x),hashlib.sha256).hexdigest()):raise ValueError('observer authentication rejected')
  if boot_hash is None:boot_hash=hashlib.sha256(pathlib.Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest()
  if x['schema']!='kpi-independent-SSH-observer/v1' or x['state'] not in VALID or x['boot_identity_sha256']!=boot_hash:raise ValueError('invalid observer identity')
  age=monotonic()-x['observed_monotonic']
  if not 0<=age<=MAX_AGE:return {'state':'stale','certain':False,'reason':'observer_heartbeat_stale','evidence_digest':hashlib.sha256(raw).hexdigest()}
  if x['state']=='unreachable' and not x['positive_baseline_in_this_generation']:raise ValueError('absence without independent positive baseline')
  if x['state']=='reachable' and not 0<=monotonic()-x['last_ack_monotonic']<=6:raise ValueError('reachable lease stale')
  return {'state':x['state'],'certain':x['state'] in {'reachable','unreachable'},'reason':x['reason'],'observer_generation':x['observer_generation'],'observed_at':x['observed_at'],'age_seconds':age,'journal_seq':x['journal_seq'],'journal_digest':x['journal_digest'],'evidence_digest':hashlib.sha256(raw).hexdigest(),'authentication':'C-owned HMAC and kernel-authenticated forced SSH peer; C receipts additionally use pinned forced-command SSH'}
 except Exception as e:return {'state':'observer_failure','certain':False,'reason':type(e).__name__}
