"""C-local exact-terminal integration. B receives no generic RPC/key/endpoint.

Only separately frozen finite-live-native terminal authority can dispatch. Node
observations are trusted full-node assertions, not a light client/finality proof.
"""
import fcntl,hashlib,json,os,pathlib,socket,stat,subprocess,tempfile,time,zlib
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import a1_check as c
import a1_recovery as r
import terminal_payout as payout
from terminal_sdk_gate import validate_receipt,validate_evidence,encode,sha,bindings
from terminal_body_check import check_body
from a1_fee_check import fee_requirements
from boundary_controller_v2 import events,verify_chain
from result_gate import validate as validate_result
from rpc_local import RPC

OPS={'terminal-submit','terminal-observe','terminal-status'}

def load(path,maximum=262144):
 path=pathlib.Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  st=os.fstat(f.fileno());payout.require(stat.S_ISREG(st.st_mode) and st.st_size<=maximum,'bounded regular metadata')
  raw=f.read(maximum+1)
 payout.require(len(raw)<=maximum,'metadata budget');return payout.strict_json(raw) if maximum<=65536 else json.loads(raw)

def header_for_comparison(header):
 # Native CompressedParents cumulative-end RLE, pinned 01b532e8... header.rs.
 # Normalize only representation; compare every header field and parent in order.
 payout.require(type(header) is dict and 'parentsByLevel' in header,'complete native header parents')
 parents=header['parentsByLevel'];payout.require(type(parents) is list,'header parent levels')
 expanded=[];total=0
 if parents and type(parents[0]) is list and len(parents[0])==2 and type(parents[0][0]) is int:
  previous=0;last=None
  for run in parents:
   payout.require(type(run) is list and len(run)==2,'compressed parent run')
   end=r.rpc_uint(run[0],8);values=run[1]
   payout.require(end>previous and type(values) is list and values!=last,'canonical compressed parent levels')
   payout.require(all(type(h) is str and len(r.unhex(h))==32 for h in values),'header parent hashes')
   total+=(end-previous)*len(values);payout.require(total<=255*2048,'native uncompressed parent bound')
   expanded.extend([list(values) for _ in range(end-previous)]);previous=end;last=values
 else:
  payout.require(len(parents)<=255,'native header level bound')
  for values in parents:
   payout.require(type(values) is list and all(type(h) is str and len(r.unhex(h))==32 for h in values),'expanded header parent hashes')
   total+=len(values);payout.require(total<=255*2048,'native uncompressed parent bound');expanded.append(list(values))
 return dict(header,parentsByLevel=expanded)

def immutable(path,value):
 raw=encode(value);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)

def policy(config,source_directory=None):
 p=config['terminal_policy'];payout.require(config['mode']=='finite-live-native' and config.get('execution_authorized') is True and config.get('terminal_execution_authorized') is True,'separate finite terminal execution authority')
 payout.require(p['schema']=='kpi-frozen-terminal-policy/v1' and p['run_id']==config['run_id'] and p['base_instance_id']==config['base_instance_id'] and p['network']=='testnet-10' and p['branch']=='s1_terminal' and p['max_attempts']==1 and p['execution_checklist_sha256']==config['execution_checklist_sha256'],'frozen terminal policy binding')
 # Trusted CONFIG is immutable source/service-bound before funding/A loss, never B data.
 payout.require(p['manifest_sha256']==config['manifest_sha256'] and p['inventory_sha256']==config['inventory_sha256'],'policy public bundle')
 for name,pin in p['sources_sha256'].items():
  base=pathlib.Path(source_directory) if source_directory is not None else pathlib.Path(__file__).parent
  path=base/name;payout.require(path.parent==base and sha(path.read_bytes())==pin,'terminal source changed')
 for name in ['terminal_runtime.py','terminal_payout.py','terminal_body_check.py','a1_recovery.py','a1_check.py','a1_fee_check.py','terminal_sdk_gate.py','result_gate.py','rpc_local.py','terminal_fee_quotes.mjs']:
  payout.require(name in p['sources_sha256'],'missing required source pin')
 payout.require(p['sdk_files_sha256']==__import__('terminal_sdk_gate').SDK_PINS,'fee SDK pins')
 for name in ['native','reference','context','quote_node']:
  t=p['tools'][name];payout.require(sha(pathlib.Path(t['path']).read_bytes())==t['sha256'],'native/context/reference tool pin')
 return p

def prepare(config,run):
 """Admin prepare only, before A loss; no node/proof/submit call."""
 p=policy(config);directory=pathlib.Path(run)/'terminal';directory.mkdir(mode=0o700)
 st=directory.stat();binding={'run_id':config['run_id'],'base_instance_id':config['base_instance_id'],
  'authorization_sha256':sha(encode(p)),'sources_sha256':sha(encode(p['sources_sha256'])),
  'device':st.st_dev,'inode':st.st_ino,'owner':st.st_uid}
 immutable(directory/'directory-authorization.json',binding)
 return {'prepared':True,'authorization_sha256':binding['authorization_sha256'],'broadcast':False}

def command(args,timeout=180):
 child=subprocess.run(args,capture_output=True,timeout=timeout)
 payout.require(child.returncode==0,'bounded native/reference command rejected')
 payout.require(len(child.stdout)<=262144,'native result budget');return json.loads(child.stdout)

def absence(config,run,guard,through=None):
 g=guard()
 if through is not None:
  deadline=time.monotonic()+5
  while g['at']<through:
   payout.require(time.monotonic()<deadline,'fresh post-observation absence probe unavailable')
   time.sleep(.1);g=guard()
 rows=events(pathlib.Path(run));verify_chain(rows)
 payout.require(len(rows)==6,'complete independent loss/recovery boundary')
 loss=rows[4];payout.require(loss['kind']=='A_LOSS_BOUNDARY','loss row')
 path=pathlib.Path(run)/'probes.jsonl';payout.require(path.stat().st_size<=8*1024*1024,'probe journal budget')
 previous='0'*64;seq=0;active=False;last=None;selected=[]
 for line in path.read_bytes().splitlines():
  probe=json.loads(line);check=dict(probe);value=check.pop('digest')
  payout.require(probe['seq']==seq and probe['previous']==previous and sha(encode(check))==value,'probe chain corruption')
  seq+=1;previous=value
  if value==loss['payload']['probe_chain_digest']:active=True
  if active:
   payout.require(probe['any_reachable'] is False and probe.get('uncertain',False) is False,'A return/uncertainty')
   # Journal sampling budget is operational; native/witness freshness stays strict.
   if last:payout.require(0<=probe['at']-last['at']<=30,'absence sample gap')
   last=probe;selected.append(probe['digest'])
 payout.require(active and last is not None and -2<=time.time()-last['at']<=5 and g['probe_digest']==last['digest'],'current complete absence interval')
 return {'loss_at':loss['at'],'at':last['at'],'sha256':sha(encode({'loss':loss['digest'],'probes':selected}))}

def dispatch_absence(run,q):
 # Post-submit checks cannot authorize another spend. Prove the original C loss
 # interval through qualification; do not assert that A is still absent now.
 run=pathlib.Path(run);rows=events(run);verify_chain(rows)
 payout.require(len(rows)==6 and rows[4]['kind']=='A_LOSS_BOUNDARY','original loss boundary')
 previous='0'*64;active=False;last=None;selected=[];matched=False
 for seq,line in enumerate((run/'probes.jsonl').read_bytes().splitlines()):
  probe=json.loads(line);check=dict(probe);digest=check.pop('digest')
  payout.require(probe['seq']==seq and probe['previous']==previous and sha(encode(check))==digest,'original probe hash chain')
  previous=digest
  if digest==rows[4]['payload']['probe_chain_digest']:active=True
  if active and probe['at']<=q['absence_at']:
   payout.require(probe['any_reachable'] is False and probe.get('uncertain',False) is False,'original dispatch A return/uncertainty')
   if last:payout.require(0<=probe['at']-last['at']<=30,'original dispatch sample gap')
   last=probe;selected.append(digest)
   if probe['at']==q['absence_at']:matched=True
 payout.require(active and matched and last is not None,'exact original dispatch interval')
 absent={'loss_at':rows[4]['at'],'at':last['at'],'sha256':sha(encode({'loss':rows[4]['digest'],'probes':selected}))}
 retained=load(run/'terminal/qualified-current.json',maximum=512*1024*1024)
 payout.require(absent==retained['absence'] and absent['sha256']==q['absence_sha256'] and absent['loss_at']==q['loss_at'] and -2<=q['qualified_at']-absent['at']<=5,'original independent qualified absence binding')
 return absent

def node_policy(p):
 pid=p['node_policy']['pid'];payout.require(type(pid) is int and pid>0,'qualified node process')
 proc=pathlib.Path('/proc')/str(pid);payout.require(sha((proc/'exe').read_bytes())==p['node_policy']['binary_sha256'],'node binary changed')
 args=(proc/'cmdline').read_bytes().split(b'\0');keys={x.split(b'=',1)[0] for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x}
 payout.require(not any(x in [b'-C',b'--configfile'] or x.startswith((b'--configfile=',b'--minrelay',b'--mempool',b'--maxstandard',b'--mass')) for x in args) and b'KASPAD_CONFIGFILE' not in keys and not any(b'FEE' in k or b'MASS' in k or b'MEMPOOL' in k for k in keys),'unqualified node relay overrides')
 return p['node_policy']

def fee_policy(p,manifest,full,local_estimate,quotes):
 payout.require(quotes['network']=='testnet-10' and quotes['pins']['rusty_kaspa_commit']==manifest['pins']['rusty_kaspa_commit'],'fee quote provenance')
 rates=[Fraction(100)];now=time.time();expires=[]
 observations=quotes['observations'];payout.require(1<=len(observations)<=3,'external fee observation count')
 payout.require({o['endpoint'] for o in observations}==set(p['external_fee_endpoints']),'predeclared fee endpoints')
 for o in observations:
  payout.require(o['status']=='observed' and o['info']['isSynced'] is True and o['info']['serverVersion']==p['server_version'] and o['dag']['network']=='testnet-10','fresh synced external fee source')
  stamp=datetime.fromisoformat(o['observed_at_utc'].replace('Z','+00:00')).timestamp();payout.require(-2<=now-stamp<=300,'stale external fees');expires.append(stamp+300)
  add_rates(rates,o['fees'])
 add_rates(rates,local_estimate)
 rate=max(rates);mass,relay,floor,required=fee_requirements(full['native_masses'],rate)
 payout.require(required<=r.rpc_uint(full['fee'])==r.rpc_uint(p['fee_sompi']),'fixed fee/headroom insufficient')
 return {'passed':True,'rate':[str(rate.numerator),str(rate.denominator)],'required':str(required),'relay_floor':str(floor),'expiry_at':min(expires),'quotes_sha256':sha(encode(quotes)),'local_estimate_sha256':sha(encode(local_estimate))}

def add_rates(out,fees):
 e=fees['estimate'];buckets=[e['priorityBucket']]+e['normalBuckets']+e['lowBuckets'];payout.require(1<=len(buckets)<=32,'fee bucket bounds')
 for b in buckets:
  rate=Fraction(str(b['feerate']));payout.require(type(b['feerate']) is not bool and rate>0,'fee rational');out.append(rate)

class Adapter:
 def __init__(self,config,run,guard,*,current=None,rpc_factory=RPC,native_command=command,read_only=False,observation_directory=None):
  self.config,self.run,self.guard=config,pathlib.Path(run),guard;self.read_only=read_only
  original=self.run/'terminal';self.directory=pathlib.Path(observation_directory) if observation_directory is not None else original
  payout.require(not read_only or (observation_directory is not None and self.directory!=original),'separate read-only observation attempt')
  historical=pathlib.Path(config['finite']['role_sources']['terminal_runtime.py']['path']).parent if read_only else None
  self.p=policy(config,historical)
  self.observation_sources={p.name:sha(p.read_bytes()) for p in pathlib.Path(__file__).parent.iterdir() if p.suffix in {'.py','.mjs'} and not p.name.startswith('test_')}
  if current is None:
   if read_only:
    from finite_runtime import readonly_current
    current=readonly_current(config,self.run,self.directory/'current-observer')
   else:
    from finite_runtime import current
  self.current=current;self.rpc_factory=rpc_factory;self.command=native_command
  self.binding=load(original/'directory-authorization.json');self.result=load(self.run/'B-result.json');self.manifest=load(config['manifest'])
  payout.require(sha(pathlib.Path(config['manifest']).read_bytes())==config['manifest_sha256'],'manifest changed')
  payout.require(self.binding['authorization_sha256']==sha(encode(self.p)) and self.binding['sources_sha256']==sha(encode(self.p['sources_sha256'])),'preloss directory authority mismatch')
  rows=events(self.run);verify_chain(rows)
  receipt=load(self.run/'B-result-receipt.json')
  payout.require(receipt['result_sha256']==sha(encode(self.result)) and receipt['status']=='success' and receipt['run_id']==config['run_id'] and receipt['terminal_sdk_receipt_sha256']==self.result['terminal_sdk_receipt_sha256'],'original C durable G5 receipt binding')
  validate_result(self.result,config,rows,validation_at=receipt['at'])
  payout.require(self.result['status']=='success' and self.result['broadcast'] is False,'per-run recovery absent')
  payout.require(r.rpc_uint(self.p['exact_payout'])==r.rpc_uint(self.result['terminal_sdk_receipt']['payout']) and self.p['recipient_spk_hex']==self.manifest['recipient']['spk_hex'] and r.rpc_uint(self.p['fee_sompi'])==r.rpc_uint(self.manifest['branches']['s1_terminal']['fee']),'predeclared terminal payout/fee')
 def qualify(self,candidate,binding):
  payout.require(not self.read_only,'read-only postcheck cannot qualify a spend')
  payout.require(binding==self.binding,'registered directory identity')
  result=self.result;sdk=result['terminal_sdk_receipt'];full=result['native_Full'];proving=result['fresh_proving'];discovery=result['recovery_report']['discovery']
  payout.require(candidate['sdk_receipt_sha256']==sha(encode(sdk))==result['terminal_sdk_receipt_sha256'] and candidate['g5_result_sha256']==sha(encode(result)),'B/C durable SDK/G5 binding')
  validate_receipt(sdk,self.config,self.manifest,full,proving,discovery);validate_evidence(sdk,result['terminal_sdk_receipt_sha256'],result['artifact_evidence'])
  payout.require(sha(encode(candidate['decoded']))==sdk['decoded_body_sha256'] and sha(encode(candidate['request']))==sdk['decoded_request_sha256'],'SDK decoded bytes changed')
  # Fee collection may take 25 seconds: finish it BEFORE starting the exact
  # current native witness. Native work afterwards still has the core age bound.
  node_policy(self.p);rpc=self.rpc_factory();rpc.METHODS=set(rpc.METHODS)|{'getFeeEstimate'}
  try:fees=rpc.call('getFeeEstimate',{})
  finally:rpc.close()
  with tempfile.TemporaryDirectory(dir=self.directory) as scratch:
   path=pathlib.Path(scratch)/'fee-policy.json';path.write_bytes(encode(self.p))
   quotes=self.command([self.p['tools']['quote_node']['path'],'--experimental-websocket',str(pathlib.Path(__file__).with_name('terminal_fee_quotes.mjs')),self.p['sdk_directory'],str(path)],timeout=25)
  fee=fee_policy(self.p,self.manifest,full,fees,quotes)
  self.sample=self.current(self.config,self.run);points={(x['outpoint']['transactionId'],x['outpoint']['index']):x['utxoEntry'] for x in self.sample['utxos']['entries']};point=tuple(discovery['current_outpoint'])
  payout.require(point in points,'exact S1 no longer unspent');entry=points[point]
  payout.require(entry==candidate['request']['entry'],'fresh exact native context changed')
  tx=candidate['decoded'];request={'txid':point[0],'index':str(point[1]),'entry':entry};w=check_body(tx,request,self.manifest,'s1_terminal',full)
  payout.require(sha(w[2])==sdk['proof_sha256']==proving['proof_sha256'] and sdk['artifact_bindings']==bindings(self.manifest,'s1_terminal'),'fresh proof/artifact binding')
  for name in ['pk','vk','r1cs']:c.artifact(pathlib.Path(self.config['manifest']).parent,self.manifest['branches']['s1_terminal'][name],name=='r1cs')
  vk=c.artifact(pathlib.Path(self.config['manifest']).parent,self.manifest['branches']['s1_terminal']['vk']);payout.require(c.script_push(vk) in w[4],'exact terminal VK embedded')
  with tempfile.TemporaryDirectory(dir=self.directory) as scratch:
   scratch=pathlib.Path(scratch);q=scratch/'request.json';b=scratch/'body.json';current=scratch/'current.json'
   q.write_bytes(encode(candidate['request']));b.write_bytes(encode(tx));current.write_bytes(encode({'entry':entry,'exact_input':tx['inputs'][0]['previousOutpoint'],'S1_unspent':True,'dag':self.sample['dag']}));current_digest=sha(current.read_bytes())
   checked=self.command([self.p['tools']['native']['path'],'validate-body',str(q)]);ids=self.command([self.p['tools']['reference']['path'],'--body',str(b)]);context=self.command([self.p['tools']['context']['path'],str(q),str(pathlib.Path(self.config['manifest']).parent),str(current)])
  payout.require(checked==full and checked['full_valid'] is True and ids['txid']==full['txid'] and ids['full_hash']==full['full_hash']==r.full_hash(tx),'actual native/reference Full mismatch')
  payout.require(context['native_Full'] is True and context['txid']==full['txid'] and context['full_hash']==full['full_hash'] and r.rpc_uint(context['fee_sompi'])==r.rpc_uint(full['fee']) and context['VK_sha256']==sdk['artifact_bindings']['vk_sha256'] and context['relay_policy']['passed'] is True,'current native context failed')
  payout.require(context['current_C_state_sha256']==current_digest and context['validation_DAA_score']==str(self.sample['dag']['virtualDaaScore']) and context['validation_past_median_time']==str(self.sample['dag']['pastMedianTime']),'actual current context binding')
  meter=context['meter'];payout.require({k:meter[k+'_mass'] for k in ['compute','storage','transient']}==full['native_masses'],'current native masses')
  payout.require(tx['inputs'][0]['computeBudget']==(11*meter['script_units']+99999)//100000 and meter['matching_vk_verifiers']==1 and meter['peak_combined_stack']<=244 and all(x<=1000000 for x in meter['native_counted_ops_per_script_signature_spk_redeem']),'unchanged script/budget/VK resource qualification')
  payout.require(context['signature_bytes']<=250000 and len(w[4])<=2000 and all(x<=10000 for x in context['output_script_bytes']) and full['native_masses']['compute']<=500000 and full['native_masses']['storage']<=500000 and full['native_masses']['transient']<=1000000,'unchanged terminal relay/resource maxima')
  absent=absence(self.config,self.run,self.guard);now=time.time()
  self.current_evidence={'sample':self.sample,'fee':fee,'context':context,'absence':absent};immutable(self.directory/'qualified-current.json',self.current_evidence)
  immutable(self.directory/'phase-clock.json',{'observer':__import__('seal_witness').process_identity(),'started_monotonic':time.monotonic(),'started_at':now})
  return {'schema':'kpi-C-terminal-qualification/v1','directory_binding_sha256':sha(encode(binding)),'witness_contract':'finite-prefix-current-witness/v1','run_id':self.config['run_id'],'base_instance_id':self.config['base_instance_id'],'network':'testnet-10','mode':'finite-live-native','phase':'G6-terminal','authorized':True,'g5_pass':True,'txid':full['txid'],'full_hash':full['full_hash'],'decoded_sha256':sha(encode(tx)),'params_sha256':sha(encode(candidate['params'])),'sdk_receipt_sha256':candidate['sdk_receipt_sha256'],'g5_result_sha256':candidate['g5_result_sha256'],'exact_input':tx['inputs'][0]['previousOutpoint'],'exact_entry':entry,'exact_payout':tx['outputs'][0],'fee_sompi':full['fee'],'authorization_sha256':self.binding['authorization_sha256'],'sources_sha256':self.binding['sources_sha256'],'witness_sha256':sha(encode(self.sample)),'native_current_sha256':sha(encode(context)),'fee_policy_sha256':sha(encode(fee)),'absence_sha256':absent['sha256'],'qualified_at':now,'expires_at':min(now+15,fee['expiry_at']),'witness_at':self.sample['observation_at'],'absence_at':absent['at'],'loss_at':absent['loss_at'],'lineage_active':True,'current_input_unspent':True,'native_full_valid':True,'current_native_full_valid':True,'fee_policy_passed':True,'continuous_A_absence':True}
 def submit_rpc(self):
  payout.require(not self.read_only,'read-only postcheck cannot submit')
  rpc=self.rpc_factory();rpc.METHODS=set(rpc.METHODS)|{'submitTransaction'};return rpc
 def observe(self,intent,phase):
  payout.require(self.observation_sources=={p.name:sha(p.read_bytes()) for p in pathlib.Path(__file__).parent.iterdir() if p.suffix in {'.py','.mjs'} and not p.name.startswith('test_')},'observation source changed')
  initial_path=self.directory/'initial-observation.json';later_path=self.directory/'later-observation.json'
  if phase=='later' and later_path.exists():return load(later_path,maximum=512*1024*1024)
  if phase=='initial' and initial_path.exists():return load(initial_path,maximum=512*1024*1024)
  q=payout.strict_json(intent.qualification_bytes);candidate=payout.strict_json(intent.candidate_bytes)
  phase_path=self.directory/'phase-clock.json'
  identity=__import__('seal_witness').process_identity()
  if not phase_path.exists():immutable(phase_path,{'observer':identity,'started_monotonic':time.monotonic(),'started_at':time.time()})
  phase_clock=load(phase_path)
  payout.require(phase_clock['observer']==identity and 0<=time.monotonic()-phase_clock['started_monotonic']<=2700,'terminal phase deadline/restart')
  if phase=='later':
   payout.require(initial_path.exists(),'later before initial observation');old=load(initial_path,maximum=512*1024*1024)
   if time.time()-old['evidence']['at']<120:return {'accepted':False,'phase':phase,'status':'waiting-required-recheck','broadcast':False}
  rpc=self.rpc_factory();rpc.METHODS=set(rpc.METHODS)|{'getVirtualChainFromBlock'}
  old=load(initial_path,maximum=512*1024*1024) if phase=='later' else None
  located_path=self.directory/'located-terminal.json';located=load(located_path,maximum=512*1024*1024) if located_path.exists() else None
  page=None;accepted=[];started=time.monotonic()
  try:
   if old or located:
    header=(old or located)['accepting_header'];body=(old or located)['accepted_native_body']
    payout.require(r.canonical_body(body)==r.canonical_body(candidate['decoded']) and r.full_hash(body)==q['full_hash'],'retained located body changed')
    request={'startHash':header['hash'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0}
    from seal_witness import survival
    survival(rpc.call('getVirtualChainFromBlock',request),header['hash'])
   else:
    cursor_path=self.directory/'discovery-progress.json'
    if cursor_path.exists():progress=load(cursor_path)
    else:
     # Start from C's already retained prefunding prefix, not the unstable
     # near-tip qualification sink. Require current selected-chain survival;
     # all page/body/reorg checks below remain strict.
     checkpoint=load(self.run/'initial.json')['checkpoint'];cursor=checkpoint['cursor']
     from seal_witness import survival
     survival(rpc.call('getVirtualChainFromBlock',{'startHash':cursor,'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),cursor)
     anchor=rpc.call('getBlock',{'hash':cursor,'includeTransactions':False})['block']
     payout.require(anchor['verboseData']['isChainBlock'] is True and anchor['header']['hash']==cursor and r.rpc_uint(anchor['header']['blueScore'])==r.rpc_uint(checkpoint['blue_score']),'retained prefunding discovery anchor changed')
     progress={'cursor':cursor,'pages':0,'bytes':0}
    for _ in range(4):
     payout.require(progress['pages']<32 and progress['bytes']<512*1024*1024 and time.monotonic()-started<600,'bounded terminal discovery exhausted')
     rpc.s.settimeout(180) if hasattr(rpc,'s') else None
     page=rpc.call('getVirtualChainFromBlockV2',{'startHash':progress['cursor'],'dataVerbosityLevel':'Full','minConfirmationCount':20})
     from capture import validate_page
     validate_page(progress['cursor'],page,[progress['cursor']],reference_binary=self.p['tools']['reference']['path'])  # unchanged strict Full group/order/body validator
     payout.require(not page['removedChainBlockHashes'],'terminal observation reorg')
     for group in page['chainBlockAcceptedTransactions']:
      for candidate_body in group['acceptedTransactions']:
       tid=candidate_body.get('verboseData',{}).get('transactionId')
       spends=any(i['previousOutpoint']==q['exact_input'] for i in candidate_body['inputs'])
       if spends:payout.require(tid==q['txid'] and r.full_hash(candidate_body)==q['full_hash'],'competing accepted terminal spend')
       if tid==q['txid']:
        payout.require(r.canonical_body(candidate_body)==r.canonical_body(candidate['decoded']) and r.full_hash(candidate_body)==q['full_hash'],'accepted body differs')
        accepted.append((group['chainBlockHeader'],candidate_body))
     progress['pages']+=1;progress['bytes']+=len(encode(page))
     payout.require(progress['pages']<=32 and progress['bytes']<=512*1024*1024,'terminal discovery page/byte budget')
     if accepted:
      payout.require(len(accepted)==1,'ambiguous terminal acceptance');found_header,found_body=accepted[0]
      page_name='located-native-page.json';immutable(self.directory/page_name,page)
      located={'accepting_header':found_header,'accepted_native_body':found_body,'node_page_sha256':sha(encode(page)),'node_page_file':page_name,'query_start':progress['cursor']}
      immutable(located_path,located) # before cursor advancement or UTXO readiness
     if page['addedChainBlockHashes']:progress['cursor']=page['addedChainBlockHashes'][-1]
     tmp=cursor_path.with_suffix('.pending');tmp.write_bytes(encode(progress));fd=os.open(tmp,os.O_RDONLY);os.fsync(fd);os.close(fd);os.replace(tmp,cursor_path);fd=os.open(self.directory,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
     if accepted or not page['addedChainBlockHashes']:break
    if not accepted:return {'accepted':False,'phase':phase,'status':'bounded-discovery-pending','broadcast':False}
    payout.require(len(accepted)==1,'ambiguous terminal acceptance');header,body=accepted[0]
   # Fresh UTXO/witness bracket AFTER potentially slow Full discovery, retaining
   # actual start time. Never relabel an earlier UTXO response as fresh.
   sample=self.current(self.config,self.run)
   points={(x['outpoint']['transactionId'],x['outpoint']['index']):x['utxoEntry'] for x in sample['utxos']['entries']}
   point=(q['exact_input']['transactionId'],q['exact_input']['index']);payout_point=(q['txid'],0)
   if point in points or payout_point not in points:return {'accepted':False,'phase':phase,'status':'awaiting-exact-acceptance-and-payout','broadcast':False}
   accepting=rpc.call('getBlock',{'hash':header['hash'],'includeTransactions':False})['block']
   payout.require(accepting['verboseData']['isChainBlock'] is True and header_for_comparison(accepting['header'])==header_for_comparison(header),'terminal accepting context changed')
   block=rpc.call('getBlock',{'hash':sample['dag']['sink'],'includeTransactions':False})['block']
   from seal_witness import survival
   survival(rpc.call('getVirtualChainFromBlock',{'startHash':header['hash'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),header['hash'])
  finally:rpc.close()
  now=sample['observation_at'];mono=sample['receipt']['started_monotonic'];absent=dispatch_absence(self.run,q)
  evidence={'schema':'kpi-C-terminal-observation/v1','observer_epoch':sha(encode(sample['receipt']['observer'])),'observed_monotonic':mono,'run_id':self.config['run_id'],'network':'testnet-10','authorization_sha256':self.binding['authorization_sha256'],'sources_sha256':self.binding['sources_sha256'],'witness_sha256':sha(encode(sample)),'absence_sha256':absent['sha256'],'at':now,'loss_at':absent['loss_at'],'absence_through':absent['at'],'absence_scope':'dispatch-qualification','continuous_A_absence':True,'phase_authorized':True,'synced':True,'lineage_active':True,'conflicting_spend':False,'reorg':False,'observed_txid':q['txid'],'observed_full_hash':q['full_hash'],'accepted_body':candidate['decoded'],'accepting_block_hash':header['hash'],'accepting_blue_score':r.rpc_uint(header['blueScore']),'current_blue_score':r.rpc_uint(block['header']['blueScore']),'exact_input':q['exact_input'],'input_unspent':False,'payout_outpoint':{'transactionId':q['txid'],'index':0},'payout_entry':points[payout_point]}
  # Every B-observe request reconstructs independent node evidence here; never
  # returns a caller-authored observation. Trusted closure only captures that evidence.
  initial=None
  if phase=='later':
   old=load(initial_path,maximum=512*1024*1024);initial=payout.VerifiedObservation(intent.digest,encode(old['evidence']),payout._TOKEN)
  verified=payout.observe(intent,{},lambda _:evidence,r.canonical_body,initial=initial)
  result={'schema':'kpi-C-exact-terminal-payout-observed/v1','run_id':self.config['run_id'],'phase':phase,'accepted':True,'txid':q['txid'],'full_hash':q['full_hash'],'intent_sha256':intent.digest,'accepting_block_hash':header['hash'],'at':now,'payout_sompi':str(points[payout_point]['amount']),'evidence':payout.strict_json(verified.evidence_bytes),'node_page_sha256':sha(encode(page)) if page else (old or located)['node_page_sha256'],'accepting_header':header,'accepted_native_body':body,'current_witness_sha256':sha(encode(sample)),'observation_sources_sha256':sha(encode(self.observation_sources)),'read_only_reconciliation':self.read_only,'no_global_G5_G6_closure':True,'broadcast':False}
  immutable(initial_path if phase=='initial' else later_path,result)
  # Preserve exact independent accepted native page/UTXOs only C locally.
  immutable(self.directory/(phase+'-node-observation.json'),{'page':page,'current':sample,'absence':absent})
  return {k:v for k,v in result.items() if k not in {'evidence','accepted_native_body','accepting_header'}}

def claimed_intent(directory):
 value=load(directory/'intent.json');claim=load(directory/'submission-claimed.json')
 payout.require(claim['intent_sha256']==sha(encode(value)),'durable terminal intent/claim mismatch')
 q=value['qualification'];payout.require(q['witness_contract']=='finite-prefix-current-witness/v1' and q['mode']=='finite-live-native','claim scope')
 return payout.ValidatedIntent(encode(value['candidate']),encode(q),encode(value),q['qualified_at'],0,payout._TOKEN)

def dispatch(q,config,run,guard):
 payout.require(q.get('run_id')==config['run_id'] and q.get('authenticated_role')=='B' and q.get('op') in OPS,'B-only exact terminal operation')
 # Controller supplies this callback after normal B role/loss guard. No B gates.
 guard();adapter=Adapter(config,run,guard);op=q['op'];directory=adapter.directory
 expected={'run_id','op','authenticated_role'}|({'candidate'} if op=='terminal-submit' else {'phase'} if op=='terminal-observe' else set())
 payout.require(set(q)==expected,'terminal operation fields')
 if op=='terminal-submit':
  payout.require(len(encode(q))<=16384,'unchanged terminal gateway envelope')
  return payout.submit_once(directory,q['candidate'],adapter.qualify,r.canonical_body,adapter.submit_rpc)
 if op=='terminal-status':
  if (directory/'later-observation.json').exists():return {k:v for k,v in load(directory/'later-observation.json',maximum=512*1024*1024).items() if k not in {'evidence','accepted_native_body','accepting_header'}}
  if (directory/'submission-result.json').exists():return load(directory/'submission-result.json')|{'claimed':True,'faulted':False}
  return {'claimed':(directory/'submission-claimed.json').exists(),'status':'reconcile-only' if (directory/'submission-claimed.json').exists() else 'no-terminal-attempt','faulted':False}
 payout.require(q['phase'] in {'initial','later'} and (directory/'submission-claimed.json').exists(),'terminal observation phase/claim')
 fd=os.open(directory/'observation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  st=os.fstat(fd);payout.require(st.st_uid==os.getuid() and stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'observation lock binding')
  fcntl.flock(fd,fcntl.LOCK_EX)
  return adapter.observe(claimed_intent(directory),q['phase'])
 finally:os.close(fd)

class ReadOnlyRPC(RPC):
 """Method guard remains read-only even if a caller expands METHODS."""
 READ_METHODS=frozenset(RPC.METHODS)|{'getVirtualChainFromBlock'}
 def call(self,method,params):
  payout.require(method in self.READ_METHODS,'postcheck RPC is read-only')
  return super().call(method,params)

def postcheck_existing(config,run,directory,expected_txid):
 """C-local operator reconciliation. Never a B request or a submission retry.
 Uses exactly Adapter.observe/payout.observe used by terminal-observe in a trial.
 New receipt lifetime; immutable old send/claim/result/observer history retained.
 """
 run=pathlib.Path(run);original=run/'terminal';directory=pathlib.Path(directory)
 payout.require(not directory.exists(),'fresh observation directory required');directory.mkdir(mode=0o700)
 before={n:sha((original/n).read_bytes()) for n in ['intent.json','submission-claimed.json','submission-result.json','located-terminal.json','located-native-page.json']}
 intent=claimed_intent(original);q=payout.strict_json(intent.qualification_bytes);candidate=payout.strict_json(intent.candidate_bytes)
 response=load(original/'submission-result.json');claim=load(original/'submission-claimed.json')
 payout.require(q['txid']==expected_txid and claim['one_attempt_only'] is True and response['outcome']=='admission-only' and response['response']['transactionId']==expected_txid,'existing exact one-shot admitted transaction')
 located=load(original/'located-terminal.json',maximum=512*1024*1024)
 payout.require(located['node_page_sha256']==before['located-native-page.json'],'retained native page bytes changed')
 for name in ['intent.json','submission-claimed.json','located-terminal.json']:
  raw=(original/name).read_bytes();fd=os.open(directory/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 def no_submit_guard():raise ValueError('read-only reconciliation has no spending guard')
 adapter=Adapter(config,run,no_submit_guard,rpc_factory=ReadOnlyRPC,read_only=True,observation_directory=directory)
 payout.require(q['full_hash']==adapter.result['native_Full']['full_hash'] and q['txid']==adapter.result['native_Full']['txid'] and q['g5_result_sha256']==sha(encode(adapter.result)) and q['sdk_receipt_sha256']==adapter.result['terminal_sdk_receipt_sha256'],'original durable native/SDK intent binding')
 payout.require(q['exact_payout']==candidate['decoded']['outputs'][0] and r.rpc_uint(q['exact_payout']['value'])==r.rpc_uint(adapter.p['exact_payout']) and q['exact_payout']['scriptPublicKey']==adapter.p['recipient_spk_hex'] and r.rpc_uint(q['fee_sompi'])==r.rpc_uint(adapter.p['fee_sompi']),'exact original amount/receiver/fee')
 initial=adapter.observe(intent,'initial');payout.require(initial['accepted'] is True,'initial postcheck incomplete')
 immutable(directory/'postcheck-progress.json',{'status':'initial-complete','txid':expected_txid,'initial_at':initial['at'],'broadcast':False})
 deadline=time.monotonic()+2700
 while True:
  old=load(directory/'initial-observation.json',maximum=512*1024*1024)
  remaining=max(120-(time.time()-old['evidence']['at']),120-(time.monotonic()-old['evidence']['observed_monotonic']))
  if remaining<=0:break
  payout.require(time.monotonic()<deadline,'postcheck wait deadline');time.sleep(min(remaining+.1,30))
 later=adapter.observe(intent,'later');payout.require(later['accepted'] is True,'later postcheck incomplete')
 payout.require(before=={n:sha((original/n).read_bytes()) for n in before},'original terminal evidence changed')
 result={'schema':'kpi-C-complete-readonly-terminal-postcheck/v1','run_id':config['run_id'],'txid':expected_txid,'initial':initial,'later':later,'wall_interval':later['at']-initial['at'],'monotonic_interval':load(directory/'later-observation.json',maximum=512*1024*1024)['evidence']['observed_monotonic']-old['evidence']['observed_monotonic'],'receipts_directory':str(directory),'original_evidence_sha256':before,'broadcast_calls':0,'funding_calls':0,'status':'success'}
 immutable(directory/'postcheck-result.json',result);return result
