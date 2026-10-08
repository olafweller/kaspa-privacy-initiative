"""Terminal SDK qualification after fresh construction. No secret or network input."""
import pathlib,json,hashlib,subprocess,os
import a1_check as c
import a1_recovery as r
from a1_recovery_rehearsal import verify_inventory
from terminal_sdk_gate import encode,sha,SDK_PINS,NODE_PIN,SCHEMA,outputs,bindings,validate_receipt,input_context
from capture_metadata import load_capture_metadata
import recovery_errors as errors
HERE=pathlib.Path(__file__).resolve().parent

def durable_new(path,value):
 path=pathlib.Path(path)
 with path.open('xb') as f:f.write(encode(value));f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)

def check_body(body,request,manifest,branch,full):
 c.require(branch=='s1_terminal','only authenticated recovered S1 terminal is qualified')
 c.keys(body,'version id inputs outputs lockTime subnetworkId gas payload storageMass','terminal body')
 c.require(body['version']==1 and body['lockTime']==manifest['envelope']['lock_time'] and body['gas']==manifest['envelope']['gas'] and body['payload']==manifest['envelope']['payload_hex'] and body['subnetworkId']==manifest['envelope']['subnetwork_hex'],'terminal envelope mismatch')
 c.require(len(body['inputs'])==1,'terminal input count');i=body['inputs'][0];c.keys(i,'previousOutpoint signatureScript sequence sigOpCount computeBudget','terminal input');c.require(i['previousOutpoint']=={'transactionId':request['txid'],'index':r.rpc_uint(request['index'],32)},'terminal input outpoint mismatch')
 entry=request['entry'];c.keys(entry,'amount scriptPublicKey blockDaaScore isCoinbase covenantId','authenticated input context')
 c.require(r.rpc_uint(entry['amount'])==r.rpc_uint(manifest['states']['s1']['R']) and entry['scriptPublicKey']==manifest['states']['s1']['spk_hex'] and entry['covenantId'] is None and entry['isCoinbase'] is False,'terminal amount/input SPK/covenant context mismatch');r.rpc_uint(entry['blockDaaScore'])
 c.require(i['sigOpCount']==0 and r.rpc_uint(i['sequence'])==(1<<64)-1 and type(i['computeBudget']) is int and i['computeBudget']==int(manifest['envelope']['compute_budgets'][branch]),'terminal sequence/budget mismatch')
 c.require(body['outputs']==outputs(manifest,branch) and len(body['outputs'])==1 and body['outputs'][0]['scriptPublicKey']==manifest['recipient']['spk_hex'],'terminal output amount/recipient/order/metadata mismatch')
 fee=r.rpc_uint(entry['amount'])-sum(r.rpc_uint(x['value']) for x in body['outputs']);c.require(fee==r.rpc_uint(manifest['branches'][branch]['fee']) and fee==r.rpc_uint(full['fee']),'terminal fee mismatch')
 c.require(body['id']==full['txid'] and r.full_hash(body)==full['full_hash'] and r.rpc_uint(body['storageMass'])==full['native_masses']['storage'],'terminal ID/full hash/storage mass mismatch')
 w=r.pushes(c.unhex(i['signatureScript']));c.require(len(w)==5 and [len(x) for x in w[:3]]==[32,32,128] and w[3]==c.unhex(manifest['branches'][branch]['selector_hex']),'terminal proof witness/branch mismatch')
 c.require(all(int.from_bytes(x,'little')<c.FR and x[16:]==bytes(16) for x in w[:2]),'terminal tag scalar ABI')
 c.require(c.sha(w[4])==manifest['states']['s1']['redeem']['sha256'] and c.p2sh(w[4]).hex()==entry['scriptPublicKey'],'terminal redeem/artifact mismatch')
 return w

def qualify(public,inventory,request_path,terminal_path,full,proving,discovery,output,run_id=None,config=None,binary='/software/kpi-poc-a1',reference='/software/a1_reference',node='/usr/bin/node',sdk='/software/sdk'):
 errors.stage('SDK-roundtrip-and-bindings',terminal_path)
 output=pathlib.Path(output);c.require(not any(output.glob('terminal-sdk-*')),'duplicate/mixed SDK qualification refused')
 cfg=config if config is not None else load_capture_metadata('/software/independent-config.json','config',os.environ.get('KPI_LIFECYCLE_CONFIG_SHA256'));c.require(run_id is None or cfg['run_id']==run_id,'SDK run mismatch')
 public=pathlib.Path(public);verify_inventory(public,inventory);manifest=c.load_json(public/'manifest.json');c.require(c.sha((public/'manifest.json').read_bytes())==cfg['manifest_sha256'] and inventory==cfg['inventory_sha256'],'SDK frozen bundle mismatch')
 sources={n:sha((HERE/n).read_bytes()) for n in ['terminal_sdk.py','terminal_sdk.mjs','terminal_sdk_gate.py','recover_exit.py','capture_metadata.py','recovery_errors.py']};sources.update({'kpi-poc-a1':sha(pathlib.Path(binary).read_bytes()),'a1_reference':sha(pathlib.Path(reference).read_bytes())});c.require(sources==cfg['terminal_sdk_sources_sha256'],'SDK source pins mismatch')
 actualnode={'version':subprocess.check_output([node,'--version'],text=True).strip(),'sha256':sha(pathlib.Path(node).read_bytes())};c.require(actualnode==NODE_PIN,'SDK Node runtime pin mismatch')
 for name,h in SDK_PINS.items():c.require(sha((pathlib.Path(sdk)/name).read_bytes())==h,'SDK file pin mismatch')
 branch='s1_terminal';request=c.load_json(request_path);c.require([request['txid'],r.rpc_uint(request['index'],32)]==list(discovery['current_outpoint']) and discovery['state']=='s1' and discovery['lineage_history_complete'] is True and discovery['current_utxo_reconciled'] is True,'SDK input differs from independently authenticated recovery result');raw=c.load_json(terminal_path);w=check_body(raw,request,manifest,branch,full);c.require(sha(pathlib.Path(request_path).read_bytes())==proving['input_request_sha256'] and sha(encode(input_context(request['entry'])))==proving['input_context_sha256'],'SDK request/current input context changed after independent construction')
 for name in ['pk','vk','r1cs']:c.artifact(public,manifest['branches'][branch][name],name=='r1cs')
 vk=c.artifact(public,manifest['branches'][branch]['vk']);c.require(c.script_push(vk) in w[4],'terminal VK not embedded in frozen redeem')
 c.require(sha(c.unhex(manifest['branches'][branch]['context_hex']))==manifest['branches'][branch]['context_sha256'],'terminal context binding')
 errors.stage('SDK-serialize-decode',terminal_path)
 sdkresult=errors.command([node,str(HERE/'terminal_sdk.mjs'),sdk,str(terminal_path),str(request_path),str(output)],timeout=60)
 decoded=c.load_json(output/'terminal-sdk-decoded.json');c.require(decoded==raw,'decoded body changed');check_body(decoded,request,manifest,branch,full)
 def command(args):
  return errors.command(args,timeout=120)
 hashes=command([reference,'--body',str(output/'terminal-sdk-decoded.json')]);c.require(hashes['txid']==full['txid'] and hashes['full_hash']==full['full_hash'],'decoded independent txid/full hash mismatch')
 errors.stage('SDK-decoded-native-Full',output/'terminal-sdk-decoded-request.json')
 final=command([binary,'validate-body',str(output/'terminal-sdk-decoded-request.json')]);c.require(final==full and final['full_valid'] is True,'decoded native Full/fee/compute/storage/transient mismatch')
 durable_new(output/'terminal-sdk-native-full.json',final)
 canonical_context={'amount':str(r.rpc_uint(request['entry']['amount'])),'scriptPublicKey':request['entry']['scriptPublicKey'],'blockDaaScore':str(r.rpc_uint(request['entry']['blockDaaScore'])),'isCoinbase':request['entry']['isCoinbase'],'covenantId':request['entry']['covenantId']}
 receipt={'schema':SCHEMA,'run_id':cfg['run_id'],'branch':branch,'instance_sha256':sha(c.unhex(manifest['instance_hex'])),'manifest_sha256':cfg['manifest_sha256'],'inventory_sha256':inventory,'sdk':sdkresult['sdk'],'runtime':sdkresult['runtime'],'sources':sources,'serialized_body_sha256':sha((output/'terminal-sdk-safe.json').read_bytes()),'serialized_numeric_sha256':sha((output/'terminal-sdk-numeric.json').read_bytes()),'constructed_file_sha256':sha(pathlib.Path(terminal_path).read_bytes()),'constructed_body_sha256':sha(encode(raw)),'decoded_body_sha256':sha((output/'terminal-sdk-decoded.json').read_bytes()),'decoded_request_sha256':sha((output/'terminal-sdk-decoded-request.json').read_bytes()),'txid':final['txid'],'full_hash':final['full_hash'],'input_outpoint':list(discovery['current_outpoint']),'input_amount':canonical_context['amount'],'input_context_sha256':sha(encode(canonical_context)),'input_request_sha256':sha(pathlib.Path(request_path).read_bytes()),'payout':decoded['outputs'][0]['value'],'recipient_spk_sha256':sha(c.unhex(decoded['outputs'][0]['scriptPublicKey'])),'output_count':len(decoded['outputs']),'ordered_outputs_sha256':sha(encode(decoded['outputs'])),'fee':final['fee'],'compute_budget':decoded['inputs'][0]['computeBudget'],'native_masses':final['native_masses'],'proof_sha256':sha(w[2]),'proof_bytes':len(w[2]),'witness_sha256':sha(c.unhex(decoded['inputs'][0]['signatureScript'])),'artifact_bindings':bindings(manifest,branch),'native_full_sha256':sha(encode(final)),'roundtrip_valid':sdkresult['roundtrip_valid'],'decoded_native_full_valid':final['full_valid']}
 validate_receipt(receipt,cfg,manifest,final,proving,discovery);durable_new(output/'terminal-sdk-receipt.json',receipt)
 return final,receipt
