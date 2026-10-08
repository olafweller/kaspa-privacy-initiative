"""Original terminal_sdk.check_body copied verbatim; no prover/network."""
import a1_check as c
import a1_recovery as r
from terminal_sdk_gate import outputs

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

