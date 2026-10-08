"""Bounded boundary validation child. Original scanner/Full checks remain authoritative.
No submit, proof generation, or broadcast APIs. Cache lasts for one immutable job.
"""
import collections,hashlib,json,os,pathlib,signal,sqlite3,subprocess,sys,time,zlib
from capture import canonical
from boundary_watch import validate_boundary
import a1_recovery as recovery
import recovery_errors as errors

def cached_native(callback,entries,max_entries=50000,max_bytes=64*1024*1024):
 cache=collections.OrderedDict();size=0
 def validate(tx,context):
  nonlocal size
  entry=None if context is None else entries.get(context['outpoint'][0]+':'+str(context['outpoint'][1]))
  # Key includes every callback input; changed context or entry cannot reuse Full.
  key=hashlib.sha256(canonical({'tx':tx,'context':context,'entry':entry})).digest()
  if key in cache:
   value=cache.pop(key);cache[key]=value;return json.loads(value)
  result=callback(tx,context);encoded=canonical(result)
  if len(encoded)<=max_bytes:
   cache[key]=encoded;size+=len(key)+len(encoded)
   while len(cache)>max_entries or size>max_bytes:
    old,v=cache.popitem(last=False);size-=len(old)+len(v)
  return json.loads(encoded)
 return validate

class Job:
 def __init__(self,run,config,command=None,deadline_seconds=1800,clock=time.monotonic):
  self.finite_verification=config.get('mode')=='finite-live-native';self.publish_verification=None
  self.clock=clock;self.deadline=clock()+deadline_seconds;self.run=pathlib.Path(run);self.output=self.run/'validation-result.json';self.error=self.run/'validation-error.json'
  configpath=self.run/'validation-config.json'
  # Exclusive durable input prevents replay/overwrite and binds one job to this run.
  if command is None:
   with configpath.open('xb') as f:f.write(canonical(config));f.flush();os.fsync(f.fileno())
   command=[sys.executable,str(pathlib.Path(__file__).resolve()),str(configpath),str(self.run)]
  errors.initialize(self.run/'errors');errors.stage('C-boundary-validation',configpath)
  self.child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);self.streams=errors.attach_child(self.child)
  self.worker_identity={'pid':self.child.pid,'boot':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'start_ticks':int((pathlib.Path('/proc')/str(self.child.pid)/'stat').read_text().rsplit(')',1)[1].split()[19])} if self.finite_verification else None
 def stop(self):
  try:os.killpg(self.child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  self.child.wait(timeout=5)
  if self.streams is not None:errors.collect_child(self.child,self.streams);self.streams=None
 def poll(self):
  if self.clock()>=self.deadline:self.stop();raise TimeoutError('boundary validation deadline')
  code=self.child.poll()
  if code is None:return None
  self.stop() # also kill any surviving native descendants
  if code!=0:raise ValueError('boundary worker rejected; sanitized durable error retained')
  if self.finite_verification:
   from finite_runtime import read_verification
   witness,pin=read_verification(self.run/'PUBLISH-VERIFIED.json')
   if witness['worker']!=self.worker_identity:raise ValueError('publication verifier process identity changed')
   self.publish_verification={'worker':self.worker_identity,'witness_sha256':pin}
  return json.loads(self.output.read_text())

def worker(configpath,run):
 cfg=json.loads(pathlib.Path(configpath).read_text());run=pathlib.Path(run)
 rehearsal=cfg['mode']=='rehearsal' and cfg.get('rehearsal_workload')
 if rehearsal:
  from live_schema_rehearsal import require_rehearsal
  require_rehearsal(cfg)
 else:assert cfg['mode'] in ['live','finite-live-native'] and cfg.get('execution_authorized') is True
 binary=cfg['finite']['native']['path'] if cfg['mode']=='finite-live-native' else '/opt/kpi-g5-capture/kpi-poc-a1'
 reference=cfg['finite']['reference']['path'] if cfg['mode']=='finite-live-native' else '/opt/kpi-g5-capture/a1_reference'
 manifestpath=pathlib.Path(cfg['manifest']);assert hashlib.sha256(manifestpath.read_bytes()).hexdigest()==cfg['manifest_sha256']
 initial=json.loads((run/'initial.json').read_text());loc=initial['locator'];cp=initial['checkpoint'];intent=json.loads((run/'intent.json').read_text())
 database=run/'history.sqlite'
 if not rehearsal:
  if cfg['mode']=='finite-live-native':
   from finite_runtime import database as finite_database
   assert (run/'CAPTURE-STOP.json').exists() and not (run/'CAPTURE-FAULT.json').exists()
   source=sqlite3.connect('file:'+str(finite_database(cfg))+'?mode=ro',uri=True)
  else:source=sqlite3.connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True)
  target=sqlite3.connect(str(database));source.backup(target);target.close();source.close()
 from recovery_index import Archive
 maintained=Archive(database);maintained.db.close()
 db=sqlite3.connect(str(database));entries=json.loads((run/'historical-entries.json').read_bytes()) if rehearsal else {}
 try:
  from historical_context import Variants,native_callback_from_variants
  if rehearsal:
   for blob, in db.execute('SELECT response FROM utxo_observations WHERE page_seq>?',(cp['seq'],)):
    for item in json.loads(zlib.decompress(blob))['entries']:
     point=item['outpoint'];key=point['transactionId']+':'+str(point['index']);entry=item['utxoEntry']
     if key in entries and entries[key]!=entry:raise ValueError('conflicting native historical context')
     entries[key]=entry
  else:
   entries=Variants.from_database(db,cp['seq'])
  from history_chunks import Writer
  last=json.loads(db.execute("select value from metadata where key='last_commit'").fetchone()[0])
  writer=Writer(run/'history-evidence',cp,cfg['run_id'],last)
  for seq,start,cursor,horizon,check,blob,prev,digest in db.execute('select seq,start,cursor,horizon,response_sha,response,previous_digest,digest from pages where seq>? and seq<=? order by seq',(cp['seq'],last['seq'])):
   writer.add({'seq':seq,'startHash':start,'cursor':cursor,'queried_horizon':horizon,'response_sha256':check,'previous_digest':prev,'digest':digest,'response':json.loads(zlib.decompress(blob))})
  history_manifest,history_hash=writer.finish()
  from recovery_index import ensure_current,hint
  from indexed_discovery import from_chunks
  hint_value=hint(db,loc,cp,cfg['run_id']);durable(run/'lineage-hint.json',hint_value)
  scan,callbacks=from_chunks(run/'history-evidence',loc,json.loads(manifestpath.read_text()),cfg['inventory_sha256'],(recovery.native_callback(binary,reference,entries) if rehearsal else native_callback_from_variants(recovery.native_callback,binary,reference,entries)),hint_value,cp,{k:last[k] for k in ['seq','cursor','digest']},cfg['run_id'],history_hash)
  report=scan.report(last['cursor']);assert report['lineage_history_complete'] and report['state']=='s1' and len(report['transitions'])==1
  receipt={'schema':'kpi-g5-accepted-boundary/v1','accepted_continuation_native_Full':True,'range_complete':True,'C_commit_digest':last['digest'],'C_commit_seq':last['seq'],'S0_locator_sha256':hashlib.sha256(canonical(loc)).hexdigest(),'state_discovered':'s1','acceptance_trust':'validated C node observation, not cryptographic light-client proof'}
  durable(run/'indexed-boundary-statistics.json',{'native_callbacks':callbacks,'pages':history_manifest['page_count'],'history_bytes':history_manifest['semantic_pages_bytes']})
  if db.execute('SELECT 1 FROM bodies JOIN spends USING(full_hash) WHERE txid=? AND full_hash=? AND previous_txid=? AND previous_index=?',(intent['intended_txid'],intent['full_hash'],loc['s0_txid_hex'],int(loc['s0_index']))).fetchone() is None:raise ValueError('accepted continuation mismatches pre-submit intent')
  return {'intent_digest':hashlib.sha256(canonical(intent)).hexdigest(),'receipt':receipt}
 finally:db.close()

def durable(path,data):
 path=pathlib.Path(path)
 with path.open('xb') as f:f.write(canonical(data));f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)

if __name__=='__main__':
 run=pathlib.Path(sys.argv[2]);errors.initialize(run/'errors');errors.stage('C-boundary-lineage',sys.argv[1])
 try:
  result=worker(sys.argv[1],run);durable(run/'validation-result.json',result)
  cfg=json.loads(pathlib.Path(sys.argv[1]).read_bytes())
  if cfg.get('mode')=='finite-live-native':
   errors.stage('C-boundary-publication-check',sys.argv[1])
   from finite_runtime import verify_publish
   from seal_witness import process_identity,durable_new
   seal=verify_publish(cfg,run,result)
   durable_new(run/'PUBLISH-VERIFIED.json',{'schema':'kpi-C-child-publish-verification/v1','run_id':cfg['run_id'],'worker':process_identity(),'config_sha256':hashlib.sha256((run/'validation-config.json').read_bytes()).hexdigest(),'result_sha256':hashlib.sha256((run/'validation-result.json').read_bytes()).hexdigest(),'manifest_sha256':cfg['manifest_sha256'],'capture_stop_sha256':hashlib.sha256((run/'CAPTURE-STOP.json').read_bytes()).hexdigest(),'seal':seal})
 except BaseException as exc:
  errors.capture(exc);durable(run/'validation-error.json',{'at':time.time(),'exception_type':type(exc).__name__,'message':errors.sanitize(exc),'stack_trace':errors.sanitize(''.join(__import__('traceback').format_exception(exc))),'config_sha256':hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(),'status':'rejected'});raise SystemExit(1)
