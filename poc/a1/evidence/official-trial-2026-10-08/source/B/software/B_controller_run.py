"""Persistent B controller: no A dependency; bounded recovery, durable no-broadcast result."""
import pathlib,json,time,subprocess,tempfile,base64,hashlib,os,signal,socket
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from access_check import query
from boundary_wait import wait_and_arm
from terminal_sdk_gate import validate_receipt,validate_evidence,encode,sha
from durable_result import atomic,seal_tree,failure,send,ROOT,stop_tree
from lifecycle_binding import load_config,record as lifecycle_record
import recovery_errors as errors
cfg=load_config();run=cfg['run_id'];
if cfg['mode'] not in {'live','finite-live-native','fixture','rehearsal'}:raise ValueError('unknown recovery service mode')
if cfg['mode']=='rehearsal' and not (cfg.get('qualification_only') is True and cfg.get('execution_authorized') is False and run.startswith('qual-a3-')):raise ValueError('unfunded rehearsal binding required')
started=time.monotonic();out=ROOT/run/'controller.json';events=[];stage='startup';child=None;restore=None;child_streams=None

def C(op,extra=None):return query({'action':'independent','op':op,'run_id':run}|(extra or {}))
def record(kind,payload):
 events.append({'kind':kind,'at':time.time(),'payload':payload});atomic(out,{'run_id':run,'events':events,'A_needed_to_start_recovery':False})
def timeout(signum,frame):raise TimeoutError('overall deadline')
def qualify_local_loopback():
 # This process is already in the service cgroup, so its IP filter is effective.
 # The endpoint is non-forwarding IPv4 loopback; no node/C RPC is contacted.
 began=time.monotonic();nonce=os.urandom(16)
 def receive_exact(peer):
  data=b''
  while len(data)<16:
   block=peer.recv(16-len(data))
   if not block:raise ValueError('local loopback sentinel truncated acknowledgement')
   data+=block
  return data
 with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
  listener.settimeout(30);listener.bind(('127.0.0.1',0));listener.listen(1)
  with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as client:
   client.settimeout(30);client.connect(listener.getsockname());client.sendall(nonce)
   peer,address=listener.accept()
   with peer:
    peer.settimeout(30)
    if address[0]!='127.0.0.1' or receive_exact(peer)!=nonce:raise ValueError('local loopback sentinel binding')
    peer.sendall(nonce)
   if receive_exact(client)!=nonce:raise ValueError('local loopback sentinel acknowledgement')
 start_ticks=pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
 value={'schema':'kpi-B-cgroup-loopback-ready/v1','run_id':run,'PID':os.getpid(),'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'start_ticks':start_ticks,'config_sha256':os.environ['KPI_LIFECYCLE_CONFIG_SHA256'],'IPv4_loopback_bind_connect_send_ack':True,'inside_service_cgroup':pathlib.Path('/proc/self/cgroup').read_text().strip(),'seconds':time.monotonic()-began,'no_external_RPC':True}
 from boundary_wait import durable
 durable(ROOT/run/'B-LOOPBACK-READY.json',value)
 return value
def idle():
 signal.alarm(0)
 while True:time.sleep(30) # Terminal run cannot be replayed, including after reboot.
if (ROOT/run/'result.json').exists():idle()
os.environ['KPI_RECOVERY_DIAGNOSTIC_DIR']=str(ROOT/run/'errors');errors.initialize(os.environ['KPI_RECOVERY_DIAGNOSTIC_DIR'])
signal.signal(signal.SIGALRM,timeout);signal.alarm(12500)
try:
 if out.exists():raise RuntimeError('interrupted pending controller cannot resume blindly')
 stage='local-loopback-startup';errors.stage(stage);qualify_local_loopback()
 lifecycle_record('controller-start',{'mode':cfg['mode']})
 record('B_CONTROLLER_STARTED_BEFORE_ACCEPTANCE',{'mode':cfg['mode'],'overall_timeout_seconds':12500,'recovery_timeout_seconds':5400})
 if cfg['mode'] in {'live','finite-live-native'} and cfg.get('execution_authorized') is not True:
  signal.alarm(0) # Immutable unauthorised standby: never prepares, arms or recovers.
  stage='unfunded-standby'
  while True:
   s=C('status')
   if s['run_id']!=run or s['mode']!=cfg['mode'] or s['faulted'] is not False or s['events'] or s['terminal_result'] is not None:raise ValueError('unfunded standby unexpectedly acquired experiment state')
   time.sleep(2)
 stage='acceptance-wait'
 result=wait_and_arm(C,run,started+5400,ROOT/run,atomic)
 record('B_ARMED_AFTER_C_RECEIPT',{'arm_digest':result['arm_digest']})
 stage='physical-shutdown-wait'
 while True:
  if time.monotonic()-started>6000:raise TimeoutError('shutdown wait')
  s=C('status')
  if len(s['events'])==5:
   result=C('start');record('B_RELEASED_AFTER_C_INDEPENDENT_LOSS',{'loss_digest':result['boundary_digest'],'S1_pointer_received':result['S1_pointer_supplied']});break
  if len(s['events'])!=4:raise ValueError('unexpected loss stage')
  time.sleep(2)
 stage='fresh-proof-and-Full'
 if cfg['mode']=='fixture':args=['/usr/bin/python3','/software/B_independent_recovery.py']
 else:
  if cfg['mode']!='rehearsal' and cfg.get('execution_authorized') is not True:raise ValueError('future execution not authorized')
  base='/instances/'+cfg['base_instance_id'];sealed=pathlib.Path(base+'/backup/backup-package.json').read_bytes()
  if hashlib.sha256(sealed).hexdigest()!=cfg['backup_ciphertext_sha256']:raise ValueError('backup inventory mismatch')
  package=json.loads(sealed);context={k:package[k] for k in ['schema','run_id','manifest_sha256','artifact_inventory_sha256']}
  if context['run_id']!=cfg['base_instance_id'] or context['manifest_sha256']!=cfg['manifest_sha256'] or context['artifact_inventory_sha256']!=cfg['inventory_sha256']:raise ValueError('backup context mismatch')
  unlock=pathlib.Path(base+'/backup/unlock.key').read_bytes();errors.register_secret(unlock)
  material=AESGCM(unlock).decrypt(base64.b64decode(package['nonce_b64']),base64.b64decode(package['ciphertext_b64']),json.dumps(context,sort_keys=True,separators=(',',':')).encode())
  if len(material)!=64:raise ValueError('backup framing')
  errors.register_secret(material);errors.register_secret(material[:32]);errors.register_secret(material[32:])
  restore=tempfile.TemporaryDirectory(prefix='independent-restore-',dir='/work');backup=pathlib.Path(restore.name);backup.chmod(0o700)
  for name,data in [('claim-secret.bin',material[:32]),('recipient-key.bin',material[32:])]:
   target=backup/name;target.write_bytes(data);target.chmod(0o600)
  args=['/usr/bin/python3','/software/recovery_supervisor.py','--mode','future','--run-id',run,'--public',base+'/public','--backup',str(backup),'--locator',cfg['B_locator_path'],'--checkpoint',cfg['B_checkpoint_path'],'--output',cfg['B_recovery_output'],'--inventory-sha256',cfg['inventory_sha256']]
 child=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);child_streams=errors.attach_child(child)
 deadline=time.monotonic()+5410
 while child.poll() is None:
  if time.monotonic()>deadline:raise TimeoutError('bounded recovery wait')
  time.sleep(1)
 errors.collect_child(child,child_streams);child_streams=None
 if child.returncode:raise ValueError('independent guarded recovery rejected')
 if restore:restore.cleanup();restore=None
 C('guard');s=C('status')
 if cfg['mode']=='fixture':
  summary=json.loads(pathlib.Path('/work/final-qualification/independent-recovery-report.json').read_text());directory=pathlib.Path(summary.pop('evidence_directory'))
 else:directory=pathlib.Path(cfg['B_recovery_output'])
 report=json.loads((directory/'report.json').read_text());full=json.loads((directory/'terminal-full-validation.json').read_text());proving=json.loads((directory/'terminal-proving-receipt.json').read_text());sdk_receipt=json.loads((directory/'terminal-sdk-receipt.json').read_text());manifest=json.loads(pathlib.Path('/instances/'+cfg['base_instance_id']+'/public/manifest.json').read_text());validate_receipt(sdk_receipt,cfg,manifest,full,proving,report['discovery']);evidence=seal_tree(directory);sdk_digest=sha(encode(sdk_receipt));validate_evidence(sdk_receipt,sdk_digest,evidence)
 if not (report['discovery']['state']=='s1' and report['fresh_terminal_proof'] and report['separate_native_Full'] and report['SDK_roundtrip_decoded_native_Full'] and report['broadcast'] is False and report['A_access_required'] is False and full['full_valid'] is True and proving['fresh_proof'] is True):raise ValueError('recovery outcome incomplete')
 record('B_FRESH_TERMINAL_FULL_STOP_NO_BROADCAST',{'elapsed_seconds':time.monotonic()-started})
 result={'schema':'kpi-g5-autonomous-result/v1','run_id':run,'mode':cfg['mode'],'status':'success','at':time.time(),'stage':'terminal-Full-stop','broadcast':False,'A_dependency':False,'recovery_report':report,'native_Full':full,'fresh_proving':proving,'artifact_evidence':evidence,'terminal_sdk_receipt':sdk_receipt,'terminal_sdk_receipt_sha256':sdk_digest,'controller_events':events,'C_event_digests':[x['digest'] for x in s['events']],'manifest_sha256':cfg['manifest_sha256'],'inventory_sha256':cfg['inventory_sha256'],'worker_source_sha256':cfg['worker_source_sha256']}
 atomic(ROOT/run/'result.json',result);send(result);stage='complete'
 if cfg['mode']=='finite-live-native' and cfg.get('terminal_execution_authorized') is True:
  # Preserve G5 broadcast=false result even if the separately authorized payout halts.
  stage='terminal-payout'
  try:
   errors.stage(stage)
   from B_terminal_payout import run as terminal_run
   terminal_run(cfg,directory,ROOT/run)
  except Exception as exc:
   diagnostic_recorded=True;diagnostic_failure=None
   try:errors.capture(exc)
   except Exception as diagnostic_exc:diagnostic_recorded=False;diagnostic_failure=type(diagnostic_exc).__name__
   atomic(ROOT/run/'terminal-phase-halted.json',{'run_id':run,'at':time.time(),'status':'halted-reconcile-only','G5_result_unchanged':True,'failure_stage':stage,'exception_type':type(exc).__name__,'private_diagnostics_recorded':diagnostic_recorded,'diagnostic_recording_exception_type':diagnostic_failure,'diagnostic_directory':os.environ['KPI_RECOVERY_DIAGNOSTIC_DIR']})
except BaseException as exc:
 errors.stage(stage)
 errors.capture(exc, None if child is None else child.poll())
 if child is not None:stop_tree(child)
 if child_streams is not None:errors.collect_child(child,child_streams)
 if restore:restore.cleanup()
 diagnostics=pathlib.Path(os.environ['KPI_RECOVERY_DIAGNOSTIC_DIR']);details=[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(diagnostics.glob('process-*.jsonl'))]
 atomic(ROOT/run/'boundary-error.json',{'at':time.time(),'stage':stage,'exception_type':type(exc).__name__,'child_exit_code':None if child is None else child.poll(),'diagnostic_directory':str(diagnostics),'child_error_evidence':details})
 result=failure(cfg,stage,'timeout' if isinstance(exc,(TimeoutError,subprocess.TimeoutExpired)) else 'interrupted' if isinstance(exc,RuntimeError) else 'guard_or_recovery_rejected')
 try:send(result)
 except Exception:atomic(ROOT/run/'C-delivery-failed.json',{'at':time.time(),'failure_recorded_on_B':True,'reason':'C-report-channel-unavailable'})
idle()
