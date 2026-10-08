"""Recovery-only orchestration: discover exact reserve, fresh proof, native Full.

No submit/broadcast capability. Fixture mode uses C-published unfunded data.
Future mode requires C's independently recorded A-loss boundary and a separately
pre-positioned approved inventory/locator/checkpoint/private backup.
"""
import argparse,json,pathlib,subprocess,time
from durable_result import atomic
from terminal_sdk import qualify, durable_new
from terminal_sdk_gate import input_context
import a1_check as c
import a1_recovery as r
from a1_recovery_rehearsal import verify_inventory
from access_check import query
from recovery_download import download
from history_chunks import iter_pages
from history_storage import Storage
from capture_metadata import load_capture_metadata
import recovery_errors as errors
BINARY='/software/kpi-poc-a1';REFERENCE='/software/a1_reference'
def command(args):
 return errors.command(args)
def recover(public,backup,locator,checkpoint,inventory,output,mode,run_id=None):
 errors.initialize(__import__('os').environ['KPI_RECOVERY_DIAGNOSTIC_DIR']);errors.register_backup(backup);errors.stage('immutable-artifact-check',public)
 start=time.monotonic();c.require(not output.exists(),'refuse reused recovery directory');verify_inventory(public,inventory)
 checked=command(['python3','/software/a1_check.py',str(public),'--intent',str(public/'owner-intent.json'),'--receipt',str(public/'setup-receipt.json'),'--reference-binary',REFERENCE]);c.require(checked['parameter_consistency'],'independent parameter checking failed')
 errors.stage('claim-and-recipient-verification',backup)
 command([BINARY,'check-backup',str(public),str(backup/'claim-secret.bin'),str(backup/'recipient-key.bin')])
 loc=c.load_json(locator);c.require(loc['artifact_index_sha256']==inventory,'untrusted locator inventory')
 output.mkdir(mode=0o700)
 if mode=='fixture':
  gate=query({'action':'control-gate','mode':'fixture'});c.require(gate['recovery_allowed'],'loss boundary absent');query({'action':'recovery-start','mode':'fixture'})
  archive=output/'archive';archive.mkdir(mode=0o700)
  for name in ['locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json']:
   data=query({'action':'fixture','name':name})['data'];(archive/name).write_bytes(c.canonical_json(data))
  c.require(c.load_json(archive/'locator.json')==loc,'fixture locator changed')
 else:
  errors.stage('pre-funding-checkpoint',checkpoint)
  c.require(checkpoint is not None,'pre-funding checkpoint required');cp=load_capture_metadata(checkpoint,'checkpoint');c.require(cp['cursor']==loc['scan_start_hash'],'locator/checkpoint mismatch')
  errors.stage('C-history-download',checkpoint)
  archive=output/'archive';download(cp,archive,'future',run_id=run_id)
 manifest=c.load_json(public/'manifest.json');source=load_capture_metadata(archive/'source.json','source') if mode!='fixture' else c.load_json(archive/'source.json');entries=c.load_json(archive/'entries.json')
 errors.stage('independent-lineage-scan',archive)
 if mode=='fixture':
  scan=r.Scanner(loc,manifest,r.native_callback(BINARY,REFERENCE,entries),inventory)
  for page in c.load_json(archive/'pages.json'):scan.page(page,source['horizon'])
 else:
  errors.stage('index-lookup',checkpoint);lookup_start=time.monotonic()
  hint=query({'action':'independent','op':'lineage-hint','run_id':run_id})
  (archive/'lineage-hint.json').write_bytes(c.canonical_json(hint));errors.emit('index-lookup-complete',{'seconds':time.monotonic()-lookup_start})
  errors.stage('underlying-evidence-verification',archive)
  from indexed_discovery import from_chunks
  from historical_context import Variants,native_callback_from_variants
  def emit(kind,data):
   errors.emit(kind,data)
   if kind=='S1-first-discovered':errors.stage(kind,archive)
  scan,callbacks=from_chunks(archive,loc,manifest,inventory,native_callback_from_variants(r.native_callback,BINARY,REFERENCE,Variants.load(entries)),hint,cp,source['history_commit'],run_id,source['history_manifest_sha256'],emit=emit)
  errors.emit('indexed-discovery-complete',{'native_callbacks':callbacks})
  from lifecycle_binding import load_config
  if load_config()['mode']=='finite-live-native':
   sealed=source['finite_seal']['continuation'];spender=hint['spender']
   c.require(sealed['txid']==spender['txid']==scan.current[0] and sealed['full_hash']==spender['full_hash'] and sealed['accepting_hash']==spender['accepting_hash'],'B independently verified continuation/seal mapping mismatch')
 c.require(scan.report(source['horizon'])['lineage_history_complete'],'funding/lineage coverage incomplete')
 c.require(scan.state in ('s0','s1'),'reserve has already exited')
 errors.stage('lineage-complete',archive)
 if mode=='fixture':
  current=c.load_json(archive/'current-utxos.json');current_entries=c.load_json(archive/'current-entries.json')
 else:
  # Address is only a bounded RPC lookup hint. Exact discovered outpoint and
  # native entry/accounting below are decisive; address equality never is.
  spk=manifest['states'][scan.state]['spk_hex'];address_script="const s=require('/software/sdk/kaspa.js');console.log(s.addressFromScriptPublicKey(new s.ScriptPublicKey(parseInt(process.argv[1].slice(0,4),16),process.argv[1].slice(4)),'testnet').toString());"
  response=subprocess.run(['/usr/bin/node','-e',address_script,spk],capture_output=True,text=True,timeout=30);c.require(response.returncode==0,'pinned SDK address derivation failed')
  observed=query({'action':'utxos','addresses':[response.stdout.strip()]})
  from lifecycle_binding import load_config
  config=load_config()
  if config['mode']=='finite-live-native':
   from finite_receipt import current as check_finite_current
   check_finite_current(config,observed,source,output,[response.stdout.strip()])
  c.require(observed['server']['networkId']=='testnet-10' and observed['server']['isSynced'],'current node not qualified')
  current=[];current_entries={}
  for item in observed['utxos']['entries']:
   op=item['outpoint'];entry=item['utxoEntry'];c.require('covenantId' in entry,'incomplete current native entry');key=op['transactionId']+':'+str(op['index']);current_entries[key]=entry
   current.append({'transaction_id':op['transactionId'],'index':str(op['index']),'value':str(entry['amount']),'spk_hex':r.rpc_spk(entry['scriptPublicKey']).hex(),'covenant':entry['covenantId']})
  (archive/'current-observation.json').write_text(json.dumps(observed))
 errors.stage('current-outpoint-and-accounting',archive)
 result=scan.reconcile_utxos(current,source['horizon']);point=result['current_outpoint'];key=point[0]+':'+str(point[1]);c.require(key in current_entries,'exact current reserve entry missing')
 entry=current_entries[key];entry=dict(entry);entry['scriptPublicKey']=r.rpc_spk(entry['scriptPublicKey']).hex()
 request=output/'terminal-request.json';request.write_bytes(c.canonical_json({'txid':point[0],'index':str(point[1]),'entry':entry}))
 errors.stage('fresh-terminal-proof',request)
 terminal=output/'fresh-terminal.json';receipt=command([BINARY,'fresh-terminal',str(public),scan.state+'_terminal',str(backup/'claim-secret.bin'),str(request),str(terminal)]);c.require(receipt.get('fresh_proof') and receipt.get('native_full'),'fresh terminal/native Full failed');witness=r.pushes(c.unhex(c.load_json(terminal)['inputs'][0]['signatureScript']));receipt.update(input_context_sha256=c.sha(c.canonical_json(input_context(entry))),input_request_sha256=c.sha(request.read_bytes()),proof_sha256=c.sha(witness[2]),witness_sha256=c.sha(c.unhex(c.load_json(terminal)['inputs'][0]['signatureScript'])),constructed_body_sha256=c.sha(c.canonical_json(c.load_json(terminal))));atomic(output/'terminal-proving-receipt.json',receipt)
 errors.stage('terminal-native-Full',terminal)
 native=output/'full-request.json';native.write_bytes(c.canonical_json({'transaction':c.load_json(terminal),'entry':entry}));full=command([BINARY,'validate-body',str(native)]);c.require(full.get('full_valid') is True,'independent final Full failed');durable_new(output/'terminal-pre-sdk-full-validation.json',full)
 full,sdk_receipt=qualify(public,inventory,request,terminal,full,receipt,result,output,run_id=run_id)
 durable_new(output/'terminal-full-validation.json',full)
 errors.stage('completed-SDK-decoded-Full',terminal)
 errors.emit('peak-B-RSS',{'kib':__import__('resource').getrusage(__import__('resource').RUSAGE_SELF).ru_maxrss})
 report={'scope':'unfunded independent B fixture' if mode=='fixture' else 'separately authorized recovery, no broadcast','mode':mode,'discovery':result,'fresh_terminal_proof':True,'separate_native_Full':True,'SDK_roundtrip_decoded_native_Full':True,'A_access_required':False,'broadcast':False,'elapsed_seconds':time.monotonic()-start,'current_observation_trust':'independent validated C node assertion, not light-client proof'}
 atomic(output/'report.json',report);print(json.dumps(report))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['fixture','future'],required=True)
 for name in ['public','backup','locator','checkpoint','output']:p.add_argument('--'+name,type=pathlib.Path,required=name!='checkpoint')
 p.add_argument('--run-id');p.add_argument('--inventory-sha256',required=True);a=p.parse_args()
 errors.initialize(__import__('os').environ['KPI_RECOVERY_DIAGNOSTIC_DIR'])
 errors.guarded(lambda:recover(a.public,a.backup,a.locator,a.checkpoint,a.inventory_sha256,a.output,a.mode,a.run_id))
